# Future Logs Neural Search (Single Host)

This document outlines the implementation for a real-time neural search index that filters logs for a specific host (`patroni1`) and vectorizes them as they are ingested.

## Implementation Steps (Dev Tools DSL)

The following commands can be run directly in the OpenSearch Dashboards Dev Tools console.

### 1. Environment Variables
These values are used throughout the commands. Replace them with your actual values.
- `MODEL_ID`: `RLmMzpoBDLC7DRstN6vK`
- `TARGET_HOST`: `patroni1`

### 2. Model Verification
First, we verify that the embedding model is deployed and ready to accept inference requests.

```json
GET /_plugins/_ml/models/RLmMzpoBDLC7DRstN6vK
```

### 3. Filtering Pipeline Creation
We create an ingest pipeline named `future-host-pipeline`. This pipeline performs two key actions:
1.  **Drop Processor**: Checks if the `host.name` field matches our target (`patroni1`). If it does not match, the document is dropped and not indexed.
2.  **Text Embedding Processor**: If the document is kept, this processor takes the text from `_raw` and generates a vector embedding in the `message_embedding` field using the specified model.

```json
PUT /_ingest/pipeline/future-host-pipeline
{
  "description": "Filter logs for patroni1 and vectorize",
  "processors": [
    {
      "drop": {
        "if": "ctx.host?.name != 'patroni1'"
      }
    },
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
We create the `patroni-future-host` index.
- **Settings**: We enable k-NN search (`index.knn: true`) and set the `default_pipeline` to the one created above. This ensures all new documents go through our filter/vectorize logic automatically.
- **Mappings**: We define `message_embedding` as a `knn_vector` with the correct dimension (384 for all-MiniLM-L6-v2) and HNSW method for efficient search.

```json
PUT /patroni-future-host
{
  "settings": {
    "index.knn": true,
    "default_pipeline": "future-host-pipeline"
  },
  "mappings": {
    "properties": {
      "timestamp": { "type": "date" },
      "host": { 
        "properties": {
          "name": { "type": "keyword" }
        }
      },
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

### 5. Real-time Ingestion (Simulation)
We simulate the ingestion of logs.

**Log 1: Target Host (Should be Indexed)**
This log comes from `patroni1`. The pipeline will allow it and generate an embedding.

```json
POST /patroni-future-host/_doc
{
  "timestamp": "2025-11-30T10:00:01",
  "host": { "name": "patroni1" },
  "_raw": "FATAL: database system is shutting down due to lack of disk space"
}
```

**Log 2: Other Host (Should be Dropped)**
This log comes from `patroni2`. The pipeline's drop processor will discard it.

```json
POST /patroni-future-host/_doc
{
  "timestamp": "2025-11-30T10:00:02",
  "host": { "name": "patroni2" },
  "_raw": "INFO: following new leader"
}
```

**Refresh Index**
Make the data searchable immediately.

```json
POST /patroni-future-host/_refresh
```

### 6. Verification & Search

**Verify Filtering**
Check the document count. It should be 1 (only the patroni1 log).

```json
GET /patroni-future-host/_count
```

**Execute Neural Search**
Perform a semantic search using the `neural` query type. This converts the query text "disk space issue" into a vector and finds the nearest neighbors in the `message_embedding` field.

```json
GET /patroni-future-host/_search
{
  "query": {
    "neural": {
      "message_embedding": {
        "query_text": "disk space issue",
        "model_id": "RLmMzpoBDLC7DRstN6vK",
        "k": 3
      }
    }
  },
  "_source": ["_raw", "host.name"]
}
```
