# OpenSearch Query DSL Cheat Sheet

## ⚡ The Golden Rules of Efficiency
1.  **Filter vs. Query**:
    *   Use **Filter** (`filter`, `must_not`) for exact matches, ranges, and binary yes/no. It is **cached** and **faster**.
    *   Use **Query** (`must`, `should`) only when you need a **Relevance Score** (how well does it match?).
2.  **Avoid Leading Wildcards**: `*error` is slow. `error*` is okay.
3.  **Keyword vs. Text**:
    *   `term` queries on `text` fields usually fail (because of analysis). Use `match` for `text`.
    *   Use `term` for `keyword` fields.

## 🍃 Leaf Queries (Single Field)

| Type | Query | Description | Example |
| :--- | :--- | :--- | :--- |
| **Full Text** | `match` | Standard search. Analyzed. | `{"match": {"msg": "error failed"}}` |
| **Full Text** | `match_phrase` | Exact phrase match. | `{"match_phrase": {"msg": "fatal error"}}` |
| **Full Text** | `multi_match` | Search across multiple fields. | `{"multi_match": {"query": "error", "fields": ["title", "body"]}}` |
| **Term** | `term` | Exact value. Not analyzed. | `{"term": {"status": 404}}` |
| **Term** | `terms` | Any of the values (OR). | `{"terms": {"status": [404, 500]}}` |
| **Term** | `range` | Range of values. | `{"range": {"age": {"gte": 10, "lte": 20}}}` |
| **Term** | `exists` | Field is not null. | `{"exists": {"field": "user_id"}}` |
| **Expensive** | `wildcard` | Shell-style glob. | `{"wildcard": {"user": "adm*"}}` |
| **Expensive** | `regexp` | Regular expression. | `{"regexp": {"user": "s.*y"}}` |

## 🔗 Compound Queries (Boolean Logic)

The `bool` query is the container for combining multiple leaf queries.

```json
{
  "bool": {
    "must": [ ... ],     // AND (Contributes to Score)
    "filter": [ ... ],   // AND (No Score, CACHED) -> USE THIS MOST!
    "should": [ ... ],   // OR  (Boosts Score)
    "must_not": [ ... ]  // NOT (No Score, CACHED)
  }
}
```

### Example: The "Standard" Efficient Query
```json
{
  "query": {
    "bool": {
      "must": [
        { "match": { "message": "search text" } }  // Calculate score for this
      ],
      "filter": [
        { "term": { "status": "active" } },        // Filter this fast
        { "range": { "@timestamp": { "gte": "now-1d" } } }
      ]
    }
  }
}
```

### Advanced Compound Queries

| Query | Description | Use Case |
| :--- | :--- | :--- |
| **`boosting`** | Demote documents without excluding them. | "Show me apples, but rank 'rotten' ones lower." |
| **`constant_score`** | Wraps a filter and gives every document a score of 1.0. | Speed up queries when you don't care about ranking. |
| **`dis_max`** | Uses the score of the *best* matching field (not sum). | Searching same text in `title` vs `body`. |
| **`function_score`** | Modify scores with math, decay functions, or scripts. | "Boost newer documents", "Boost popular items". |

## 🤝 Joining Queries (Nested & Parent-Child)

**⚠️ Warning:** Expensive! OpenSearch is distributed; joins require extra overhead.
**🚨 Critical:** If `search.allow_expensive_queries` is `false`, these queries will **fail**.

| Query | Description | Requirement |
| :--- | :--- | :--- |
| **`nested`** | Search inside arrays of objects. | Field must be mapped as `type: "nested"`. |
| **`has_child`** | Find parent documents that have matching children. | Field must be mapped as `type: "join"`. |
| **`has_parent`** | Find child documents that have matching parents. | Field must be mapped as `type: "join"`. |
| **`parent_id`** | Find all children of a specific parent ID. | Field must be mapped as `type: "join"`. |

## 📏 Span Queries (Positional Search)

Low-level control over term order and proximity.

| Query | Description | Example |
| :--- | :--- | :--- |
| **`span_term`** | The basic unit. Matches a term. | `{"span_term": {"user": "kimchy"}}` |
| **`span_near`** | Matches spans near each other (ordered/unordered). | `{"span_near": {"clauses": [...], "slop": 5}}` |
| **`span_first`** | Matches near the beginning of the field. | `{"span_first": {"match": {...}, "end": 3}}` |
| **`span_not`** | Excludes matches that overlap with another span. | `{"span_not": {"include": {...}, "exclude": {...}}}` |

## 🛠️ Utility Queries

| Query | Description | Parameters |
| :--- | :--- | :--- |
| **`match_all`** | Matches all documents. Default query. | `boost` (float), `_name` (string) |
| **`match_none`** | Matches no documents. | `boost` (float), `_name` (string) |

## 🧪 Specialized Queries

| Query | Description | Limitation |
| :--- | :--- | :--- |
| **`more_like_this`** | Finds documents similar to input text. | Can be slow; requires tuning `min_term_freq`. |
| **`script`** | Filters documents using a custom script. | **Performance Killer**. Compiled per doc. |
| **`script_score`** | Customizes scoring using a script. | Slower than standard scoring. |
| **`distance_feature`** | Boosts score based on date/geo proximity. | Only for `date`, `date_nanos`, `geo_point`. |
| **`percolate`** | Matches a document against stored queries. | Requires `percolator` field type. |
| **`knn`** | Vector search (k-Nearest Neighbors). | Requires `knn` plugin & HNSW index. |
| **`rank_feature`** | Optimized numeric feature boosting. | Field must be `rank_feature` type. |

## 🎯 Minimum Should Match (Precision)

Controls how many optional clauses must match.

| Value | Description | Example |
| :--- | :--- | :--- |
| **Integer** | Match at least N clauses. | `2` |
| **Negative Int** | Match (Total - N) clauses. | `-1` |
| **Percentage** | Match N% of clauses (rounded down). | `75%` |
| **Negative %** | Allowed to miss N% of clauses. | `-25%` |
| **Combination** | Conditional logic. | `2<75%` (If >2 clauses, match 75%) |

## 🔄 Rewrite Parameter (Performance vs. Accuracy)

Controls how multi-term queries (like `wildcard`, `prefix`, `fuzzy`) are rewritten into low-level Lucene queries.

| Rewrite Method | Description | Performance | Scoring |
| :--- | :--- | :--- | :--- |
| **`constant_score`** | Rewrites to a filter. Matches get score of 1.0. | 🚀 Fastest | ❌ No |
| **`scoring_boolean`** | Rewrites to a boolean query. Calculates relevance. | 🐢 Slowest | ✅ Yes |
| **`top_terms_N`** | Keeps only the top N matching terms. | ⚡ Fast | ✅ Yes (Approx) |
| **`constant_score_boolean`** | Like `constant_score` but uses boolean logic internally. | 🚀 Fast | ❌ No |

**💡 Pro Tip:** Use `constant_score` for `wildcard` or `prefix` queries if you don't care about relevance ranking. It's significantly faster.

## 🥈 Rescore (The Second Pass)

Run a cheap query on all docs, then run an expensive query on just the top N results.

| Parameter | Description | Default |
| :--- | :--- | :--- |
| **`window_size`** | Number of top docs to rescore. | `10` |
| **`query_weight`** | Weight of the original query score. | `1.0` |
| **`rescore_query_weight`** | Weight of the rescore query score. | `1.0` |
| **`score_mode`** | How to combine scores (`total`, `multiply`, `avg`, `max`, `min`). | `total` |

**Use Case:** Use `match` (cheap) to find candidates, then `match_phrase` (expensive) or `script_score` (very expensive) on the top 50 to fix the ranking.

## 🧩 Regex Syntax (Lucene Engine)

**⚠️ Warning:** Regex queries are term-level and can be slow. No `^` or `$` anchors supported (matches entire token by default).

| Operator | Description | Example |
| :--- | :--- | :--- |
| **`.`** | Any single character. | `ab.` matches `abc`, `abd` |
| **`?`** | 0 or 1 of preceding char. | `colou?r` matches `color`, `colour` |
| **`+`** | 1 or more of preceding char. | `go+` matches `go`, `goo` |
| **`*`** | 0 or more of preceding char. | `a*b` matches `b`, `ab`, `aab` |
| **`{n,m}`** | Repetitions. | `x{2,4}` matches `xx`, `xxx`, `xxxx` |
| **`|`** | OR operator. | `apple|pear` |
| **`[]`** | Character class. | `[abc]` matches `a`, `b`, or `c` |
| **`~`** | Complement (Requires `COMPLEMENT` flag). | `~abc` matches anything EXCEPT `abc` |
| **`&`** | Intersection (Requires `INTERSECTION` flag). | `...&...` matches both patterns |
| **`<min-max>`** | Numeric Range (Requires `INTERVAL` flag). | `<1-100>` matches numbers 1 to 100 |

## 📊 Aggregations (Analytics)

The "GROUP BY" and "SUM/AVG" of OpenSearch.

| Type | Aggregation | Description | Example |
| :--- | :--- | :--- | :--- |
| **Metric** | `stats` | Min, Max, Sum, Avg, Count. | `{"stats": {"field": "price"}}` |
| **Metric** | `cardinality` | Count distinct values (Approx). | `{"cardinality": {"field": "user_id"}}` |
| **Bucket** | `terms` | Group by field values (Top N). | `{"terms": {"field": "status", "size": 5}}` |
| **Bucket** | `date_histogram` | Group by time interval. | `{"date_histogram": {"field": "@timestamp", "fixed_interval": "1h"}}` |
| **Bucket** | `range` | Group by custom ranges. | `{"range": {"field": "price", "ranges": [{"to": 10}, {"from": 10}]}}` |
| **Pipeline** | `derivative` | Rate of change (requires histogram). | `{"derivative": {"buckets_path": "my_count"}}` |

**Structure:**
```json
"aggs": {
  "NAME": { "TYPE": { ... } }
}
```

## 📖 Full-Text Query Reference

| Query Type | Description |
| :--- | :--- |
| **`intervals`** | Allows fine-grained control of the matching terms’ proximity and order. |
| **`match`** | The default full-text query. Can be used for fuzzy matching and phrase or proximity searches. |
| **`match_bool_prefix`** | Creates a Boolean query that matches all terms in any position, treating the last term as a prefix. |
| **`match_phrase`** | Matches a whole phrase up to a configurable slop. |
| **`match_phrase_prefix`** | Matches terms as a whole phrase, treating the last term as a prefix. |
| **`multi_match`** | Similar to the match query but is used on multiple fields. |
| **`query_string`** | Uses a strict syntax to specify Boolean conditions (`AND`, `OR`) and multi-field search. |
| **`simple_query_string`** | A simpler, less strict version of `query_string`. Won't error on syntax mistakes. |

## 🏎️ Performance Benchmark (Live Results)

Results from running 50 iterations of each query type against the `patronidata` index.

| Query Type | Avg Time (ms) | Efficiency Rating | Notes |
| :--- | :--- | :--- | :--- |
| **Term (Keyword)** | 0.02 | 🚀 Instant | Direct inverted index lookup. Fastest possible query. |
| **Range (Date)** | 0.04 | 🚀 Instant | Numeric range optimization (BKD trees). |
| **Bool (Filter)** | 0.18 | 🚀 Instant | Combines fast queries. Cached bitsets make this scalable. |
| **Match (Text)** | 0.20 | ⚡ Fast | Standard analysis overhead. |
| **Multi Match** | 0.66 | ⚡ Fast | Checks multiple fields, slightly more overhead. |
| **Fuzzy** | 1.10 | 🐢 Slow | Edit distance calculation is expensive. |
| **Wildcard (*)** | 4.00 | 🐌 Terrible | Leading wildcard forces full term scan. Avoid! |
```
