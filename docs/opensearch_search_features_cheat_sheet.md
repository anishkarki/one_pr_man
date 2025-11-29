# OpenSearch Search Features Cheat Sheet

A quick reference for advanced search capabilities in OpenSearch.

## 1. Search Options

| Feature | Parameter | Description | Example |
| :--- | :--- | :--- | :--- |
| **Pagination** | `from`, `size` | Controls result window. | `"from": 0, "size": 20` |
| **Sorting** | `sort` | Sort by field or score. | `"sort": [{"price": "desc"}]` |
| **Highlighting** | `highlight` | Highlights matching terms. | `"highlight": {"fields": {"content": {}}}` |
| **Source Filtering** | `_source` | Select specific fields to return. | `"_source": ["title", "id"]` |
| **Explain** | `explain` | Returns score calculation details. | `"explain": true` |

## 2. Keyword Search (BM25)

Default similarity algorithm. Tunable via index settings.

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `k1` | `1.2` | **Term Saturation**. Controls how quickly the score levels off as term frequency increases. Higher = more distinct. |
| `b` | `0.75` | **Length Normalization**. Controls how much document length penalizes the score. `0` = no penalty, `1` = full penalty. |

**Configuration:**
```json
"settings": {
  "index.similarity.my_bm25": {
    "type": "BM25",
    "k1": 1.5,
    "b": 0.6
  }
}
```

## 3. Search Pipelines

Intercept and modify search requests and responses.

| Processor Type | Examples | Use Case |
| :--- | :--- | :--- |
| **Request** | `filter_query`, `script_request` | Enforce security filters, modify queries dynamically. |
| **Response** | `rename_field`, `truncate_description` | Clean up data before sending to client. |

**Usage:**
`GET /_search?search_pipeline=my_pipeline`

## 4. Asynchronous Search

Run long-running queries in the background.

| Action | Method | Endpoint |
| :--- | :--- | :--- |
| **Submit** | `POST` | `_plugins/_asynchronous_search` |
| **Poll/Get** | `GET` | `_plugins/_asynchronous_search/<ID>` |
| **Delete** | `DELETE` | `_plugins/_asynchronous_search/<ID>` |
| **Stats** | `GET` | `_plugins/_asynchronous_search/stats` |

## 5. SQL & PPL

Alternative query languages for OpenSearch.

| Language | Endpoint | Syntax Example |
| :--- | :--- | :--- |
| **SQL** | `_plugins/_sql` | `SELECT * FROM my_index WHERE age > 30` |
| **PPL** | `_plugins/_ppl` | `source=my_index | where age > 30 | fields name` |

**Key PPL Commands:**
*   `source`: Define index.
*   `where`: Filter results.
*   `fields`: Select columns.
*   `stats`: Aggregations (e.g., `stats count() by category`).
*   `head`: Limit results.

## 6. Cross-Cluster Search (CCS)

Search across multiple clusters.

**1. Configure Remote Cluster (on local cluster):**
```json
PUT _cluster/settings
{
  "persistent": {
    "cluster.remote.remote_cluster_name.seeds": ["host:9300"]
  }
}
```

**2. Search:**
`GET /remote_cluster_name:index_name/_search`

## 7. Advanced Relevance (Concepts)

| Feature | Description |
| :--- | :--- |
| **User Behavior Insights (UBI)** | Framework for collecting user interactions (clicks, queries) to build datasets for tuning relevance. |
| **Learning to Rank (LTR)** | Plugin that uses Machine Learning models (XGBoost, RankLib) to re-rank search results based on features. |

## 8. Search Relevance Workbench

A tool for comparing search results and tuning relevance.

**Enable Backend:**
```json
PUT _cluster/settings
{ "persistent": { "plugins.search_relevance.workbench_enabled": true } }
```

**Key APIs:**
| Resource | Method | Endpoint |
| :--- | :--- | :--- |
| **Query Set** | `PUT` | `_plugins/_search_relevance/query_sets` |
| **Search Config** | `PUT` | `_plugins/_search_relevance/search_configurations` |
| **Experiment** | `PUT` | `_plugins/_search_relevance/experiments` |
| **Get Results** | `GET` | `_plugins/_search_relevance/experiments/<id>` |
