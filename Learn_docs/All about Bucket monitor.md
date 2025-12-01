# All About Bucket-Level Monitors in OpenSearch

Bucket-level monitors in OpenSearch Alerting allow you to categorize your data into groups (buckets) and monitor each group independently. This is particularly useful when you want to monitor the health or status of multiple entities (like servers, hosts, or services) using a single monitor configuration, rather than creating a separate monitor for each entity.

## Key Concepts

### 1. Buckets
Buckets are created using the `terms` aggregation in your Elasticsearch/OpenSearch query. For example, if you aggregate by `hostname`, each unique hostname found in the logs becomes a bucket.

### 2. Evaluation
The monitor evaluates the trigger condition for *each bucket* separately. If the condition is met for a specific bucket (e.g., `host-a`), an alert is generated specifically for that bucket.

### 3. Inputs
Bucket-level monitors typically use an extraction query that includes a `composite` aggregation or a `terms` aggregation to group the data.

## Configuration Steps

### Step 1: Define the Monitor
*   **Name**: A descriptive name.
*   **Type**: `bucket_level_monitor`.
*   **Schedule**: How often the monitor runs (e.g., every 1 minute).

### Step 2: Define the Query (Input)
The query must return the buckets you want to monitor.
Example Query Structure:
```json
{
  "size": 0,
  "query": {
    "bool": {
      "filter": [
        {
          "range": {
            "@timestamp": {
              "from": "{{period_end}}||-1m",
              "to": "{{period_end}}",
              "include_lower": true,
              "include_upper": true,
              "format": "epoch_millis"
            }
          }
        }
      ]
    }
  },
  "aggs": {
    "by_hostname": {
      "terms": {
        "field": "hostname.keyword",
        "size": 10
      },
      "aggs": {
        "error_count": {
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
```

### Step 3: Define the Trigger
The trigger condition is a Painless script that evaluates the results for each bucket.
*   **Condition**: Checks if the metric in the bucket exceeds a threshold.
    *   Example: `params._bucket.error_count.doc_count > 0`

### Step 4: Define the Action
*   **Destination**: Where to send the alert (e.g., Email, Slack, Chime, Custom Webhook).
*   **Message**: The content of the alert. You can use variables like `{{ctx.results.0.aggregations.by_hostname.buckets}}` to include details about the triggering buckets.

## API Endpoint
To create a monitor programmatically, you use the `_plugins/_alerting/monitors` endpoint.

**Method**: `POST`
**URL**: `/_plugins/_alerting/monitors`

## Example Use Case: Host Error Monitoring
**Goal**: Alert if any host logs the word "error" in the `_raw` field within the last minute.
**Aggregation**: `hostname`.
**Trigger**: Count of "error" documents > 0.

This approach ensures that if `host-A` has errors and `host-B` is fine, you only get an alert for `host-A`.
