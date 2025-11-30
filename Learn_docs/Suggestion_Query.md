# The Ultimate Guide to Querying & Aggregating Log Data
**Target Audience:** Developers & DevOps debugging logs in OpenSearch.
**Context:** You have unstructured logs in `_raw` (Text) and `_raw.keyword` (Keyword).

---

## 1. The Golden Rules of Search

Before writing a query, ask: **"Do I want to match a specific *meaning* or the exact *bytes*?"**

| Field Type | Analyzer | Best For | Query Type |
| :--- | :--- | :--- | :--- |
| **Text** (`_raw`) | Standard (Splits words) | Searching words, phrases, error codes inside a line. | `match`, `match_phrase` |
| **Keyword** (`_raw.keyword`) | None (Exact string) | Sorting, Exact ID lookups, Aggregations. | `term`, `terms` |

---

## 2. Searching Scenarios

### Scenario A: Searching for "Codes" (e.g., `e=22012`)
Your log contains `... u=1234,e=22012,ERROR ...`.
The Standard Analyzer splits this into tokens: `["u", "1234", "e", "22012", "error"]`.

#### ❌ The Wrong Way
*   **Query:** `term: { "_raw": "e=22012" }`
*   **Result:** 0 Hits.
*   **Why:** The token `e=22012` does not exist. It was split.

#### ⚠️ The "Okay" Way (Fast but Loose)
*   **Query:** `match: { "_raw": "22012" }`
*   **Result:** Matches any log containing `22012`.
*   **Risk:** Might match a port number, a row count, or a user ID `22012`.

#### ✅ The Best Way (Precise)
*   **Query:** `match_phrase: { "_raw": "e=22012" }`
*   **Result:** Matches only when token `e` is immediately followed by `22012`.
*   **Why:** It respects the structure without requiring the field to be parsed.

### Scenario B: Searching for Phrases (e.g., "connecting to database")
Tokens: `["connecting", "to", "database"]`.

#### ✅ The Best Way
*   **Query:** `match_phrase: { "_raw": "connecting to database" }`
*   **Why:** Ensures the words appear in that exact order. A simple `match` (OR) would find logs like "database error connecting to user", which is not what you want.

---

## 3. Aggregations: "How do I bucket these errors?"

You want to see a chart: **"Top Error Codes"**.
You have a problem: The error code is buried inside the `_raw` string.

### ❌ Why you can't use standard Aggregations
1.  **On `_raw` (Text):** Fielddata is disabled by default. Aggregating on analyzed text consumes massive heap memory. **Do not enable fielddata.**
2.  **On `_raw.keyword` (Keyword):** Every log line has a timestamp, so every line is unique.
    *   Bucket 1: `2025-11-30 10:01 Error 22012` (Count: 1)
    *   Bucket 2: `2025-11-30 10:02 Error 22012` (Count: 1)
    *   **Result:** Useless. You want to group by `22012`, not the full line.

### ✅ Solution 1: Runtime Fields (The "On-the-fly" Extractor)
You can define a temporary field *during the query* to extract the error code and aggregate on it. This is slower than ingestion-time extraction but perfect for ad-hoc analysis.

**Query:**
```json
GET /patronidata/_search
{
  "runtime_mappings": {
    "extracted_error_code": {
      "type": "keyword",
      "script": {
        "source": "if (doc['_raw.keyword'].size() == 0) return; String raw = doc['_raw.keyword'].value; int start = raw.indexOf('e='); if (start != -1) { int end = raw.indexOf(',', start); if (end == -1) end = raw.length(); emit(raw.substring(start + 2, end)); }"
      }
    }
  },
  "size": 0,
  "aggs": {
    "top_errors": {
      "terms": {
        "field": "extracted_error_code",
        "size": 10
      }
    }
  }
}
```

### ✅ Solution 2: Significant Text (The "Lazy" Discovery)
If you don't know the pattern (e.g., `e=...`) but just want to see "what weird words are appearing in my logs?", use `significant_text`.

**Query:**
```json
GET /patronidata/_search
{
  "query": {
    "match": { "_raw": "error" }
  },
  "size": 0,
  "aggs": {
    "unusual_terms": {
      "significant_text": {
        "field": "_raw",
        "size": 10
      }
    }
  }
}
```
*   **Result:** Might return `22012`, `timeout`, `connection` because they appear frequently *with* "error" but not in the general dataset.

---

## 4. How to Verify Tokens (The "Why")

Don't guess how OpenSearch sees your data. **See it.**

Use the CLI tool to simulate the analysis:

**Command:**
```bash
opensearch-manager index analyze simulate patronidata "e=22012"
```

**Output Interpretation:**
1.  **If you see `["e", "22012"]`**: The field is **Text** (Standard Analyzer). You must use `match_phrase` to find them together.
2.  **If you see `["e=22012"]`**: The field is **Keyword**. You must search for `e=22012` exactly.

To check `_raw.keyword` specifically, you can force the analyzer (if you know it) or just remember: **Keyword fields always produce ONE token equal to the input.**

---

## 5. Aggregation Deep Dive: `host.name` vs `_raw.keyword`

You asked: *"Can I aggregate with hostname? How is _raw.keyword working?"*

### The Rule of Cardinality (Uniqueness)
Aggregation works by grouping **identical** tokens into buckets.

#### Case A: `host.name` (Good for Aggregation ✅)
*   **Data:**
    *   Doc 1: `host.name = "server-A"`
    *   Doc 2: `host.name = "server-A"`
    *   Doc 3: `host.name = "server-B"`
*   **Analyzer:** Keyword (Keeps "server-A" as one token).
*   **Result:**
    *   Bucket "server-A": Count 2
    *   Bucket "server-B": Count 1
*   **Verdict:** Perfect. You get meaningful groups.

#### Case B: `_raw.keyword` (Bad for Aggregation ❌)
*   **Data:**
    *   Doc 1: `_raw = "2025-01-01 10:00:01 Error"`
    *   Doc 2: `_raw = "2025-01-01 10:00:02 Error"`
*   **Analyzer:** Keyword (Keeps the WHOLE line as one token).
*   **Result:**
    *   Bucket "2025-01-01 10:00:01 Error": Count 1
    *   Bucket "2025-01-01 10:00:02 Error": Count 1
*   **Verdict:** Useless. Because of the timestamp, every line is unique. You get 1 bucket per document.

### Summary
*   **Can you aggregate on `host.name`?** **YES.** It has low cardinality (few unique values).
*   **Can you aggregate on `_raw.keyword`?** **NO.** It has high cardinality (almost all values are unique).

---

## 6. Performance Explained (The "Why" behind the Speed)

| Operation | Field | Speed | Why is it this speed? |
| :--- | :--- | :--- | :--- |
| **Filter** | `keyword` | 🚀🚀🚀 | **Exact Lookup.** OpenSearch keeps a sorted list of all terms. It jumps straight to "server-A" (Binary Search). |
| **Filter** | `text` | 🚀🚀 | **Inverted Index.** It looks up "error" in the index. Fast, but might match many documents (scoring overhead). |
| **Phrase** | `text` | 🚀 | **Position Check.** It finds "connecting" AND "database", then checks their *position numbers* to ensure they are neighbors. Extra math. |
| **Regex** | `keyword` | 🐢 | **Term Scan.** If you search `*error*`, it must check *every single unique term* in the index to see if it matches the pattern. |
| **Script** | `runtime` | 🐢🐢 | **Code Execution.** It has to load the document value into memory and run a script *for every single document* that matches the query. |

## 7. Summary Recommendation

1.  **To Find `e=22012`**: Use `match_phrase` on `_raw`.
2.  **To Find "connecting to database"**: Use `match_phrase` on `_raw`.
3.  **To Count Error Codes**: Use a **Runtime Field** aggregation to extract the code dynamically, or (better) update your ingestion pipeline to extract `e` into a dedicated field `error_code`.

---

## 8. Real DSL Examples (Copy-Paste Ready)

Here are the exact JSON bodies you should use.

### A. The "Find Specific Error" Query
**Goal:** Find logs containing the exact sequence `e=22012`.
**Use Case:** Debugging a specific application error code.
**DSL:**
```json
GET /patronidata/_search
{
  "query": {
    "match_phrase": {
      "_raw": "e=22012"
    }
  }
}
```

### B. The "Filter by Host" Query
**Goal:** Find all logs from a specific host (e.g., `e20666c13238`).
**Use Case:** Isolating issues to one server.
**DSL:**
```json
GET /patronidata/_search
{
  "query": {
    "term": {
      "host.name": "e20666c13238"
    }
  }
}
```

### C. The "Top Hosts" Aggregation
**Goal:** Count how many logs generated by each host.
**Use Case:** Finding noisy neighbors or load balancing checks.
**DSL:**
```json
GET /patronidata/_search
{
  "size": 0, 
  "aggs": {
    "top_hosts": {
      "terms": {
        "field": "host.name",
        "size": 10
      }
    }
  }
}
```
*Note: `"size": 0` means "don't show me the log lines, just show me the counts".*

### D. The "Errors per Host" (Combo)
**Goal:** Find logs containing "error" and count them by host.
**Use Case:** "Which server is throwing the most errors?"
**DSL:**
```json
GET /patronidata/_search
{
  "size": 0,
  "query": {
    "match": {
      "_raw": "error"
    }
  },
  "aggs": {
    "hosts_with_errors": {
      "terms": {
        "field": "host.name",
        "size": 10
      }
    }
  }
}
```

## 9. How to Run & "See" It

### 1. Where to Run
*   **Dev Tools:** In OpenSearch Dashboards, go to **Management > Dev Tools**. Paste the JSON on the left, click Play.
*   **Curl:** `curl -X GET "localhost:9200/patronidata/_search" -H 'Content-Type: application/json' -d '{ ... }'`

### 2. How to "See" Performance (Profiling)
If you want to know *exactly* why a query is slow, add `"profile": true`.

**DSL:**
```json
GET /patronidata/_search
{
  "profile": true,
  "query": {
    "match_phrase": {
      "_raw": "e=22012"
    }
  }
}
```
**Output:** It will return a detailed breakdown of timing (e.g., "TermQuery: 0.5ms", "NextDoc: 1.2ms"). This is how you prove that `regex` is slower than `term`.

## 10. Debugging with Raw API Logs (The "Black Box" Revealed)

When you use the CLI tool (or look at `--query-history`), you see raw API requests. Here is how to read them to make decisions, and the **exact DSL** to run them yourself in Dev Tools.

### 1. The Simulation Request (`_analyze`)
**Context:** You are testing a string to see how it breaks down.
**Log Entry:**
```json
{
  "timestamp": "2025-11-30T18:00:26.172958",
  "tag": "analyze_text_simulation",
  "method": "POST",
  "url": "http://localhost:19200/patronidata/_analyze",
  "body": {
    "text": "2025/11/30 6:58 u=1234,e=22012,ERROR: Error connecting to database"
  }
}
```
**Dev Tools DSL:**
```json
POST /patronidata/_analyze
{
  "text": "2025/11/30 6:58 u=1234,e=22012,ERROR: Error connecting to database"
}
```
**How to Conclude:**
*   **Action:** Look at the response `tokens`.
*   **Observation:** The text `e=22012` becomes two tokens: `["e", "22012"]`.
*   **Conclusion:** You **cannot** use `term: "e=22012"`. You **must** use `match_phrase: "e=22012"` to find these two tokens next to each other.

### 2. The Inspection Request (`_termvectors`)
**Context:** You are checking a specific document (`S7o7...`) to see what is *actually* stored on disk.
**Log Entry:**
```json
{
  "timestamp": "2025-11-30T18:00:26.491735",
  "tag": "inspect_termvectors",
  "method": "POST",
  "url": "http://localhost:19200/patronidata/_termvectors/S7o7z5oBDLC7DRstgBGH",
  "body": {
    "fields": ["*"],
    "positions": true,
    "offsets": true,
    "term_statistics": true
  }
}
```
**Dev Tools DSL:**
```json
POST /patronidata/_termvectors/S7o7z5oBDLC7DRstgBGH
{
  "fields": ["*"],
  "positions": true,
  "offsets": true,
  "term_statistics": true
}
```
**How to Conclude:**
*   **Action:** Look at the `term_vectors` in the response.
*   **Observation:**
    *   Field `_raw`: Has terms `connecting`, `to`, `database` with positions `[11, 12, 13]`.
    *   Field `_raw.keyword`: Has one giant term `2025...database`.
*   **Conclusion:**
    *   For `_raw`: Use `match_phrase` (relies on positions).
    *   For `_raw.keyword`: Use `term` (relies on exact string).

### 3. The Metadata Requests (`_stats` & `_mapping`)
**Context:** Checking index health and configuration.
**Log Entry:**
```json
{
  "tag": "get_index_details",
  "method": "GET",
  "url": "http://localhost:19200/patronidata"
}
```
**Dev Tools DSL:**
```json
GET /patronidata
```
**How to Conclude:**
*   **Action:** Look at `mappings.properties`.
*   **Observation:** `_raw` is `type: text`. `_raw.keyword` is `type: keyword`.
*   **Conclusion:**
    *   `text` = Analyzed = Use `match`/`match_phrase`.
    *   `keyword` = Not Analyzed = Use `term`/`terms`.

## 11. The Final Decision Matrix

Based on the outputs from the tools above, here is your cheat sheet:

| Observation from `_analyze` / `_termvectors` | Query to Use | Why? |
| :--- | :--- | :--- |
| **Single Token** (e.g., `user-id-123`) | `term` | Exact match is fastest. |
| **Multiple Tokens** (e.g., `error`, `connecting`) | `match` | Standard full-text search. |
| **Multiple Tokens + Sequential IDs** (e.g., `e`, `22012`) | `match_phrase` | You need to preserve the relationship/order. |
| **Single Giant Token** (e.g., full log line) | `term` (Only for full exact string) | It's a keyword field. Partial matches fail. |
