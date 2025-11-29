# Optimal Query Generation for Patroni Logs

## 1. Objective
To design and validate the most efficient OpenSearch query for detecting failover events in Patroni/Postgres/Etcd logs.

## 2. Data Analysis
*   **Index**: `patronidata`
*   **Key Fields**: 
    *   `hostname` (keyword)
    *   `component` (keyword)
    *   `message` (text, standard analyzer)
*   **Tokenization Insights**: 
    *   The standard analyzer lowercases text (e.g., `FATAL` -> `fatal`).
    *   Punctuation is removed (e.g., `FATAL:` -> `fatal`).
    *   Numbers are preserved.

## 3. Query Strategies Tested

### Option A: Broad Wildcard ("The Lazy Query")
Uses expensive wildcards and unstructured text search.
*   **Strategy**: `wildcard` on hostname + `query_string` for message.
*   **Pros**: Easy to write, covers everything.
*   **Cons**: High resource usage (wildcards are slow), potential for noise.

### Option B: Precise Bool ("The Optimized Query")
Uses filters for keywords and specific match clauses.
*   **Strategy**: `term`/`prefix` on hostname + `bool` logic for components & keywords.
*   **Pros**: Fast, structured, leverages filter caching.
*   **Cons**: Verbose, requires knowing exact keywords.

## 4. Experiment Results (Search Relevance Workbench)
We ran a `PAIRWISE_COMPARISON` experiment using the OpenSearch Search Relevance Workbench.

*   **Broad Wildcard**: Found to be less efficient and potentially noisier.
*   **Precise Bool**: Targeted specific components and messages effectively.

## 5. Performance Benchmark
We benchmarked both queries by running them 50 times against the dataset.

*   **Broad Wildcard Latency**: ~3.20 ms
*   **Precise Bool Latency**: ~2.33 ms
*   **Result**: The Precise Bool query is approximately **1.4x faster**.

## 6. Final Optimal Query
The **Precise Bool** strategy is the winner due to better performance and precision.

```json
{
  "query": {
    "bool": {
      "filter": [
        { "prefix": { "hostname": "db-prod" } },
        { "terms": { "component": ["patroni", "postgres", "etcd"] } }
      ],
      "should": [
        { "match": { "message": "promoted leader" } },
        { "match": { "message": "demoted replica" } },
        { "match": { "message": "terminating connection" } },
        { "match": { "message": "acquiring lock" } }
      ],
      "minimum_should_match": 1
    }
  }
}
```
