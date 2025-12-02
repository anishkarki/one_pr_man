import requests
import json
import time
import sys

# Configuration
HOST = 'localhost'
PORT = 19200
AUTH = ('admin', 'admin')
BASE_URL = f"http://{HOST}:{PORT}"
HEADERS = {"Content-Type": "application/json"}
VERIFY_SSL = False
EMAIL_CHANNEL_ID = "yZI4WJoBHocox8i_xA-r"
INDEX_NAME = "patronidata"

def check_connection():
    """Check connection to OpenSearch."""
    try:
        response = requests.get(BASE_URL, auth=AUTH, headers=HEADERS, verify=VERIFY_SSL)
        if response.status_code == 200:
            print(f"Connected to OpenSearch at {BASE_URL}")
            return True
        else:
            print(f"Failed to connect: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Connection error: {e}")
        return False

def insert_doc(hostname, message, timestamp=None):
    """Insert a single document."""
    url = f"{BASE_URL}/{INDEX_NAME}/_doc"
    if timestamp is None:
        timestamp = int(time.time() * 1000)
    
    doc = {
        "hostname": hostname,
        "_raw": message,
        "@timestamp": timestamp
    }
    
    response = requests.post(url, auth=AUTH, headers=HEADERS, json=doc, verify=VERIFY_SSL)
    if response.status_code == 201:
        print(f"Inserted doc for {hostname}")
    else:
        print(f"Failed to insert doc for {hostname}: {response.text}")

def insert_dummy_data():
    """Insert dummy data to trigger alerts."""
    current_time = int(time.time() * 1000)
    old_time = current_time - (10 * 60 * 1000) # 10 mins ago

    print("\n--- Inserting Dummy Data ---")
    insert_doc("host-A", "complete error happened. All down", current_time)
    insert_doc("host-B", "Another error occurred here", current_time)
    insert_doc("host-C", "Operation completed successfully", current_time)
    insert_doc("host-OLD", "This is an old error", old_time)

def get_monitor_by_name(name):
    """Search for a monitor by name."""
    url = f"{BASE_URL}/_plugins/_alerting/monitors/_search"
    query = {
        "query": {
            "match": {
                "monitor.name": name
            }
        }
    }
    response = requests.get(url, auth=AUTH, headers=HEADERS, json=query, verify=VERIFY_SSL)
    if response.status_code == 200:
        hits = response.json()['hits']['hits']
        for hit in hits:
            if hit['_source']['name'] == name:
                return hit['_id']
    return None

def delete_monitor_by_name(name):
    """Delete a monitor by name to ensure fresh state."""
    mid = get_monitor_by_name(name)
    if mid:
        requests.delete(f"{BASE_URL}/_plugins/_alerting/monitors/{mid}", auth=AUTH, headers=HEADERS, verify=VERIFY_SSL)
        print(f"Deleted existing monitor {mid}")

def ensure_bucket_monitor():
    """Create or Update the Bucket-Level Monitor."""
    url = f"{BASE_URL}/_plugins/_alerting/monitors"
    monitor_name = "Hostname Error Monitor (Python Script)"
    
    # Delete first to ensure fresh state (no old throttling history)
    delete_monitor_by_name(monitor_name)
    
    monitor_payload = {
        "type": "bucket_level_monitor",
        "monitor_type": "bucket_level_monitor", 
        "name": monitor_name,
        "enabled": True,
        "schedule": {
            "period": {
                "interval": 1,
                "unit": "MINUTES"
            }
        },
        "inputs": [
            {
                "search": {
                    "indices": [INDEX_NAME],
                    "query": {
                        "size": 0,
                        "query": {
                            "range": {
                                "@timestamp": {
                                    "gte": "now-5m"
                                }
                            }
                        },
                        "aggs": {
                            "by_hostname": {
                                "terms": {
                                    "field": "hostname",
                                    "size": 10
                                },
                                "aggs": {
                                    "error_check": {
                                        "filter": {
                                            "match": {
                                                "_raw": "error"
                                            }
                                        },
                                        "aggs": {
                                            "latest_log": {
                                                "top_hits": {
                                                    "size": 1,
                                                    "sort": [
                                                        {
                                                            "@timestamp": {
                                                                "order": "desc"
                                                            }
                                                        }
                                                    ],
                                                    "_source": {
                                                        "includes": [
                                                            "_raw",
                                                            "hostname"
                                                        ]
                                                    }
                                                }
                                            },
                                            "max_error_time": {
                                                "max": {
                                                    "field": "@timestamp"
                                                }
                                            }
                                        }
                                    },
                                    "only_errors": {
                                        "bucket_selector": {
                                            "buckets_path": {
                                                "count": "error_check._count"
                                            },
                                            "script": "params.count > 0"
                                        }
                                    },
                                    "sort_by_time": {
                                        "bucket_sort": {
                                            "sort": [
                                                {
                                                    "error_check>max_error_time": {
                                                        "order": "desc"
                                                    }
                                                },
                                                {
                                                    "_count": {
                                                        "order": "asc"
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        ],
        "triggers": [
            {
                "bucket_level_trigger": {
                    "name": "Error Trigger",
                    "severity": "1",
                    "condition": {
                        "buckets_path": {
                            "_count": "_count",
                            "error_count": "error_check._count"
                        },
                        "parent_bucket_path": "by_hostname",
                        "script": {
                            "source": "params.error_count > 0",
                            "lang": "painless"
                        }
                    },
                    "actions": [
                        {
                            "name": "Send Email Notification",
                            "destination_id": EMAIL_CHANNEL_ID,
                            "action_execution_policy": {
                                "action_execution_scope": {
                                    "per_alert": {
                                        "actionable_alerts": [
                                            "DEDUPED",
                                            "NEW"
                                        ]
                                    }
                                }
                            },
                                                        "subject_template": {
                                                            "source": "Alert: Error detected on host {{ctx.results.0.aggregations.by_hostname.buckets.0.key}}"
                                                        },
                                                        "message_template": {
                                                            "source": "Hello,\n\nAlert details for host {{ctx.results.0.aggregations.by_hostname.buckets.0.key}}:\n\n{{#ctx.results.0.aggregations.by_hostname.buckets.0.error_check.latest_log.hits.hits}}- Host: {{_source.hostname}}\n  Log: {{_source._raw}}\n{{/ctx.results.0.aggregations.by_hostname.buckets.0.error_check.latest_log.hits.hits}}{{^ctx.results.0.aggregations.by_hostname.buckets.0.error_check.latest_log.hits.hits}}No recent error log captured.{{/ctx.results.0.aggregations.by_hostname.buckets.0.error_check.latest_log.hits.hits}}\n\nPlease investigate."
                                                        },
                            "throttle_enabled": True,
                            "throttle": {
                                "value": 5,
                                "unit": "MINUTES"
                            }
                        }
                    ]
                }
            }
        ]
    }

    print("\n--- Ensuring Bucket Monitor ---")
    
    print("Creating new monitor...")
    response = requests.post(url, auth=AUTH, headers=HEADERS, json=monitor_payload, verify=VERIFY_SSL)
    
    if response.status_code in [200, 201]:
        monitor_id = response.json()['_id']
        print(f"Monitor created successfully: {monitor_id}")
        return monitor_id
    else:
        print(f"Failed to create Monitor: {response.status_code} - {response.text}")
        return None

def execute_monitor(monitor_id):
    """Manually execute the monitor to verify alerts."""
    if not monitor_id:
        return {}

    print(f"\n--- Executing Monitor {monitor_id} ---")
    # dryrun=false ensures that alerts are actually created/updated, allowing throttling to work
    exec_url = f"{BASE_URL}/_plugins/_alerting/monitors/{monitor_id}/_execute?dryrun=false"
    exec_resp = requests.post(exec_url, auth=AUTH, headers=HEADERS, verify=VERIFY_SSL)
    
    if exec_resp.status_code == 200:
        print("Monitor executed successfully.")
        exec_data = exec_resp.json()
        
        triggered_hosts = {} # host -> is_throttled

        # Check trigger results
        if 'trigger_results' in exec_data:
            print("\nTrigger Results:")
            for trigger_id, result in exec_data['trigger_results'].items():
                print(f"  Trigger {trigger_id} payload:\n{json.dumps(result, indent=2)}")
                # Check action results
                if 'action_results' in result:
                    for bucket_key, action_res in result['action_results'].items():
                        for action_name, res in action_res.items():
                             error = res.get('error')
                             status = res.get('status')
                             is_throttled = res.get('throttled', False)
                             triggered_hosts[bucket_key] = is_throttled
                             
                             print(f"  Bucket: {bucket_key} - Action: {action_name}")
                             print(f"    Throttled: {is_throttled}")
                             if error:
                                 print(f"    Error: {error}")
                             else:
                                 print(f"    Success! Status: {status}")
                                 # print(f"    Full Result: {res}") # Debug

        else:
            print("No trigger_results found. Raw execute payload:")
            print(json.dumps(exec_data, indent=2))

        return triggered_hosts

    else:
        print(f"Execution failed: {exec_resp.status_code} - {exec_resp.text}")
        return {}

def check_mailhog():
    """Check MailHog for the latest email and verify content."""
    print("\n--- Checking MailHog ---")
    try:
        # Wait a moment for email to arrive
        time.sleep(2)
        response = requests.get("http://localhost:8025/api/v2/messages")
        if response.status_code == 200:
            messages = response.json()['items']
            if not messages:
                print("No messages found in MailHog.")
                return

            print(f"Found {len(messages)} messages in MailHog.")
            
            # Check the last few messages (since we just ran the monitor)
            # We expect 2 messages (one for host-A, one for host-B) if it's per-bucket.
            
            count = 0
            for msg in messages[:2]: # Look at top 2
                count += 1
                subject = msg['Content']['Headers']['Subject'][0]
                body = msg['Content']['Body']
                print(f"\nEmail #{count}")
                print(f"Subject: {subject}")
                print(f"Body Full:\n{body}") 
                
            expected_log = "complete error happened. All down"
            # We want to see if we have multiple emails.
            
        else:
            print(f"Failed to query MailHog: {response.status_code}")
    except Exception as e:
        print(f"Error checking MailHog: {e}")

def clear_mailhog():
    """Delete all messages in MailHog."""
    try:
        requests.delete("http://localhost:8025/api/v1/messages")
        print("Cleared MailHog messages.")
    except Exception:
        pass

def clean_index():
    """Delete and recreate the index to ensure a clean state."""
    print("\n--- Cleaning Index ---")
    resp = requests.delete(f"{BASE_URL}/{INDEX_NAME}", auth=AUTH, headers=HEADERS, verify=VERIFY_SSL)
    print(f"Delete response: {resp.status_code} - {resp.text}")
    
    # Define mapping to ensure @timestamp is treated as a date
    mapping = {
        "mappings": {
            "properties": {
                "@timestamp": {"type": "date"},
                "hostname": {"type": "keyword"},
                "_raw": {"type": "text"}
            }
        }
    }
    
    requests.put(f"{BASE_URL}/{INDEX_NAME}", auth=AUTH, headers=HEADERS, json=mapping, verify=VERIFY_SSL)
    print(f"Recreated index {INDEX_NAME} with date mapping")

def debug_search():
    """Debug: Search for all docs."""
    url = f"{BASE_URL}/{INDEX_NAME}/_search"
    response = requests.get(url, auth=AUTH, headers=HEADERS, verify=VERIFY_SSL)
    print("\n--- Debug Search ---")
    if response.status_code == 200:
        hits = response.json()['hits']['total']['value']
        print(f"Total hits: {hits}")
        
        # Search specifically for host-A
        query = {
            "query": {
                "term": {
                    "hostname": "host-A"
                }
            }
        }
        resp = requests.get(f"{BASE_URL}/{INDEX_NAME}/_search", auth=AUTH, headers=HEADERS, json=query, verify=VERIFY_SSL)
        print(f"Search for host-A hits: {resp.json()['hits']['total']['value']}")
        if resp.json()['hits']['hits']:
             print(f"Sample host-A doc: {resp.json()['hits']['hits'][0]['_source']}")

        # Check mapping
        mapping_url = f"{BASE_URL}/{INDEX_NAME}/_mapping"
        map_resp = requests.get(mapping_url, auth=AUTH, headers=HEADERS, verify=VERIFY_SSL)
        print(f"Mapping: {map_resp.text}")
    else:
        print(f"Search failed: {response.text}")

if __name__ == "__main__":
    if check_connection():
        clean_index() # Clean up old data
        clear_mailhog()
        
        # Ensure monitor exists with throttling enabled
        monitor_id = ensure_bucket_monitor()
        if not monitor_id:
            sys.exit(1)

        # --- Step 1: Trigger Host A ---
        print("\n=== STEP 1: Trigger Host A ===")
        insert_doc("host-A", "Error on A", int(time.time() * 1000))
        print("Waiting 5 seconds for indexing...")
        time.sleep(5)
        
        debug_search() # Check if data is there
        
        triggered_1 = execute_monitor(monitor_id)
        if "host-A" in triggered_1 and not triggered_1["host-A"]:
            print(">>> Step 1 PASS: Host A triggered and NOT throttled.")
        else:
            print(f">>> Step 1 FAIL: Host A status: {triggered_1.get('host-A', 'Not Found')}")

        # --- Step 2: Sleep ---
        print("\n=== STEP 2: Sleeping for 2 seconds (simulating time passing) ===")
        time.sleep(2)

        # --- Step 3: Trigger Host A (again) and Host B ---
        print("\n=== STEP 3: Trigger Host A (again) and Host B ===")
        current_time = int(time.time() * 1000)
        insert_doc("host-A", "Error on A again", current_time)
        insert_doc("host-B", "Error on B", current_time)
        print("Waiting 5 seconds for indexing...")
        time.sleep(5)

        triggered_2 = execute_monitor(monitor_id)

        # --- Step 4: Verify Throttling ---
        print("\n=== STEP 4: Verify Throttling ===")
        
        # Host A should be throttled
        if "host-A" in triggered_2 and triggered_2["host-A"]:
            print(">>> Step 4 PASS: Host A was throttled (triggered but action suppressed).")
        else:
            print(f">>> Step 4 FAIL: Host A throttling status: {triggered_2.get('host-A', 'Not Found')}")

        # Host B SHOULD trigger (new alert) and NOT be throttled
        if "host-B" in triggered_2 and not triggered_2["host-B"]:
            print(">>> Step 4 PASS: Host B triggered (new alert).")
        else:
            print(f">>> Step 4 FAIL: Host B status: {triggered_2.get('host-B', 'Not Found')}")

        check_mailhog()
