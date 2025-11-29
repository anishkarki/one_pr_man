# Patroni Neural Search Implementation

This document outlines the steps taken to implement Neural Search (Semantic Search) for Patroni logs using OpenSearch.

## Implementation Steps (Dev Tools DSL)

The following commands can be run directly in the OpenSearch Dashboards Dev Tools console.

### 1. Environment Variables
- `MODEL_ID`: `RLmMzpoBDLC7DRstN6vK`

### 2. Model Verification
```json
GET /_plugins/_ml/models/RLmMzpoBDLC7DRstN6vK
```

### 3. Ingest Pipeline Creation
We create a pipeline to vectorize the `_raw` log message.

```json
PUT /_ingest/pipeline/patroni-neural-pipeline
{
  "description": "Vectorize patroni log messages",
  "processors": [
    {
      "text_embedding": {
        "model_id": "RLmMzpoBDLC7DRstN6vK",
        "field_map": {
          "_raw": "message_embedding"
        }
      }
    }
  ]
}
```

### 4. Index Configuration
Create the `patronidata-neural` index with k-NN enabled.

```json
PUT /patronidata-neural
{
  "settings": {
    "index.knn": true,
    "default_pipeline": "patroni-neural-pipeline"
  },
  "mappings": {
    "properties": {
      "timestamp": { "type": "date" },
      "hostname": { "type": "keyword" },
      "component": { "type": "keyword" },
      "level": { "type": "keyword" },
      "_raw": { "type": "text" },
      "message_embedding": {
        "type": "knn_vector",
        "dimension": 384,
        "method": {
          "name": "hnsw",
          "engine": "lucene",
          "parameters": {
            "m": 16,
            "ef_construction": 128
          }
        }
      }
    }
  }
}
```

### 5. Data Reindexing
Populate the neural index from the existing `patronidata` index.

```json
POST /_reindex?wait_for_completion=false
{
  "source": {
    "index": "patronidata"
  },
  "dest": {
    "index": "patronidata-neural"
  }
}
```

**Check Task Status**
Replace `<task_id>` with the ID returned by the reindex command.
```json
GET /_tasks/<task_id>
```

**Refresh Index**
```json
POST /patronidata-neural/_refresh
```

### 6. Semantic Search Execution
```json
GET /patronidata-neural/_search
{
  "query": {
    "neural": {
      "message_embedding": {
        "query_text": "database went down",
        "model_id": "RLmMzpoBDLC7DRstN6vK",
        "k": 3
      }
    }
  },
  "_source": ["_raw", "component", "hostname"]
}
```
