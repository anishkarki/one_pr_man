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

def insert_dummy_data():
    """Insert dummy data to trigger alerts."""
    url = f"{BASE_URL}/{INDEX_NAME}/_doc"
    current_time = int(time.time() * 1000)

    docs = [
        {
            "hostname": "host-A",
            "_raw": "This is a critical error in the system",
            "@timestamp": current_time
        },
        {
            "hostname": "host-B",
            "_raw": "Another error occurred here",
            "@timestamp": current_time
        },
        {
            "hostname": "host-C",
            "_raw": "Operation completed successfully",
            "@timestamp": current_time
        }
    ]

    print("\n--- Inserting Dummy Data ---")
    for doc in docs:
        response = requests.post(url, auth=AUTH, headers=HEADERS, json=doc, verify=VERIFY_SSL)
        if response.status_code == 201:
            print(f"Inserted doc for {doc['hostname']}")
        else:
            print(f"Failed to insert doc for {doc['hostname']}: {response.text}")

def create_bucket_monitor():
    """Create the Bucket-Level Monitor."""
    url = f"{BASE_URL}/_plugins/_alerting/monitors"
    
    monitor_payload = {
        "type": "bucket_level_monitor",
        "monitor_type": "bucket_level_monitor", 
        "name": "Hostname Error Monitor (Python Script)",
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
                        "aggs": {
                            "by_hostname": {
                                "terms": {
                                    "field": "hostname.keyword",
                                    "size": 10
                                },
                                "aggs": {
                                    "error_check": {
                                        "filter": {
                                            "match": {
                                                "_raw": "error"
                                            }
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
                            "subject_template": {
                                "source": "Alert: Error detected on host {{ctx.newAlerts.0.bucket_keys}}"
                            },
                            "message_template": {
                                "source": """
Hello,

An error was detected on host: {{ctx.newAlerts.0.bucket_keys}}
Time: {{ctx.periodEnd}}

Please investigate.

Regards,
OpenSearch Monitor
"""
                            },
                            "throttle_enabled": False
                        }
                    ]
                }
            }
        ]
    }

    print("\n--- Creating Bucket Monitor ---")
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
        return

    print(f"\n--- Executing Monitor {monitor_id} ---")
    exec_url = f"{BASE_URL}/_plugins/_alerting/monitors/{monitor_id}/_execute"
    exec_resp = requests.post(exec_url, auth=AUTH, headers=HEADERS, verify=VERIFY_SSL)
    
    if exec_resp.status_code == 200:
        print("Monitor executed successfully.")
        exec_data = exec_resp.json()
        
        # Check trigger results
        if 'trigger_results' in exec_data:
            print("\nTrigger Results:")
            for trigger_id, result in exec_data['trigger_results'].items():
                # Check action results
                if 'action_results' in result:
                    for bucket_key, action_res in result['action_results'].items():
                        for action_name, res in action_res.items():
                             error = res.get('error')
                             status = res.get('status')
                             print(f"  Bucket: {bucket_key} - Action: {action_name}")
                             if error:
                                 print(f"    Error: {error}")
                             else:
                                 print(f"    Success! Status: {status}")
    else:
        print(f"Execution failed: {exec_resp.status_code} - {exec_resp.text}")

if __name__ == "__main__":
    if check_connection():
        insert_dummy_data()
        # Give OpenSearch a moment to index the data
        time.sleep(2)
        
        monitor_id = create_bucket_monitor()
        if monitor_id:
            # Give the monitor a moment to be ready (though execute is immediate)
            time.sleep(1)
            execute_monitor(monitor_id)
