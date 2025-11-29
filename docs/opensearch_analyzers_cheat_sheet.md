# OpenSearch Analyzers Cheat Sheet

## Core Concepts
*   **Text Analysis**: Converting unstructured text into structured terms for the inverted index.
*   **Analyzer**: A pipeline of: `Char Filters` -> `Tokenizer` -> `Token Filters`.

## Components

### 1. Character Filters (Pre-processing)
*   *Runs on raw text before tokenization.*
*   **html_strip**: Removes HTML elements (`<b>` -> ``).
*   **mapping**: Replaces characters based on a map (`:)` -> `_smile_`).
*   **pattern_replace**: Replaces characters using Regex.

### 2. Tokenizers (The Splitter)
*   *Splits text into a stream of tokens. Exactly one required.*
*   **standard**: Splits on word boundaries, removes punctuation. (Default)
*   **whitespace**: Splits on whitespace characters.
*   **keyword**: No split. Entire text is one token.
*   **pattern**: Splits based on a Regex separator.
*   **uax_url_email**: Like standard, but keeps URLs and Emails intact.

### 3. Token Filters (The Modifier)
*   *Modifies, adds, or removes tokens.*
*   **lowercase**: Converts to lowercase.
*   **stop**: Removes common words (stop words).
*   **unique**: Removes duplicate tokens.
*   **synonym**: Replaces or adds tokens based on a synonym list.
*   **stemmer**: Reduces words to root form (`running` -> `run`).
*   **asciifolding**: Converts non-ASCII characters (e.g., `à` -> `a`).

## Special Types

### Normalizers
*   **Use Case**: Keyword fields (exact matching).
*   **Structure**: `Char Filters` -> `Token Filters`. **No Tokenizer**.
*   **Limit**: Can only use character-level filters (e.g., lowercase), not token-level (e.g., synonyms).

### Token Graphs
*   **Use Case**: Multi-word synonyms (e.g., "ny" -> "new york").
*   **Mechanism**: `synonym_graph` filter creates a graph where multi-word synonyms occupy the same position length as the original term.

## Testing
*   **API**: `GET /_analyze`
*   **Usage**:
    ```json
    GET /_analyze
    {
      "analyzer": "standard",
      "text": "Text to test"
    }
    ```
