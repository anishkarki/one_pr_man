# Development Flow & Fixes Log

This document tracks the setup process, fixes applied to the baseline template, and the standard development workflow for the `OpenSearch_Management` tool.

## 1. Baseline Fixes (Initial Setup)

The initial template generation resulted in a broken state due to naming conventions and library version mismatches. The following fixes were applied to establish a working baseline:

### A. Package Structure
-   **Issue**: The source directory was named `OpenSearch-Management` (kebab-case), which is not a valid Python package name for imports.
-   **Fix**: Renamed `src/OpenSearch-Management` to `src/opensearch_management` (snake_case).

### B. Dependency Management (`pyproject.toml`)
-   **Issue**: Missing essential libraries and incorrect package name references.
-   **Fix**:
    -   Updated project name to `opensearch-management`.
    -   Added `pydantic-settings` (required for Pydantic V2 environment management).
    -   Added `opensearch-py` and `requests` for core functionality.
    -   Updated CLI entry point to point to the new package structure: `opensearch-manager = "opensearch_management.cli:app"`.

### C. Code Modernization (Pydantic V2)
-   **Issue**: `config.py` used Pydantic V1 syntax (`BaseSettings` directly from `pydantic`), which caused import errors.
-   **Fix**:
    -   Imported `BaseSettings` and `SettingsConfigDict` from `pydantic_settings`.
    -   Updated `Config` class to `model_config = SettingsConfigDict(...)`.
    -   Updated field definitions to use `validation_alias` instead of `env`.

### D. Test Configuration
-   **Issue**: Tests were importing from `your_pkg` instead of the actual package.
-   **Fix**: Updated `tests/test_cli.py` to import from `opensearch_management.cli`.

---

## 2. Development Workflow

### Prerequisites
-   Python 3.11+
-   `pip`

### Setup Environment
1.  **Clean Install**:
    ```bash
    cd OpenSearch_Management
    rm -rf .venv
    python3 -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -e ".[dev]"
    ```
    *Note: The quotes around `.[dev]` are often necessary in zsh to prevent globbing errors.*

### Running Tests
Execute the test suite using `pytest`. This runs unit tests and checks code coverage.
```bash
pytest
```

### Code Quality
We use `ruff` for both linting and formatting, and `mypy` for static type checking.

1.  **Format Code**:
    ```bash
    ruff format .
    ```

2.  **Lint Code**:
    ```bash
    ruff check .
    ```

3.  **Type Check**:
    ```bash
    mypy .
    ```

### CLI Usage
The tool is installed as an editable package, exposing the `opensearch-manager` command.

```bash
opensearch-manager --help
opensearch-manager hello --name "Developer"
```

---

## 3. Project Structure
```
OpenSearch_Management/
├── src/
│   └── opensearch_management/  # Main package
│       ├── core/               # Business logic
│       ├── cli.py              # Typer CLI entry point
│       ├── config.py           # Pydantic settings
│       └── logging.py          # Structlog configuration
├── tests/                      # Pytest suite
├── docs/                       # Documentation
├── pyproject.toml              # Dependencies & Build config
├── Makefile                    # Shortcut commands
└── README.md                   # General info
```

---

## 4. Feature 1: Index Information & Core Infrastructure

### A. Core Infrastructure Implementation
-   **Goal**: Establish a robust foundation for making requests with support for "Dry Run" and "Query History".
-   **Implementation**:
    -   Created `src/opensearch_management/client.py`:
        -   Implemented `OpenSearchClient` class wrapping `requests`.
        -   **Dry Run**: Intercepts requests if `dry_run=True`, printing the curl-equivalent details to console using `rich` and skipping the network call.
        -   **Query History**: If `query_history=True`, saves the request DSL (method, url, body) to a JSON file in `history_dsl/` before execution.
    -   **Configuration Migration**:
        -   Moved from Environment Variables (`.env`) to a structured YAML file (`user-config.yaml`) for complex config (nested auth, connection details).
        -   Updated `config.py` to use `PyYAML` and nested Pydantic models (`ConnectionConfig`, `AuthConfig`, `AppSettings`).

### B. Feature: Index Information (`index info`)
-   **Goal**: Retrieve and display detailed information about indices (mappings, settings, aliases, models).
-   **Implementation**:
    -   Created `src/opensearch_management/logic/index_operations.py`.
    -   Implemented `get_index_details` which calls `GET /<index_pattern>`.
        -   **Optimization**: When multiple indices are provided as arguments, they are joined by commas (e.g., `index1,index2`). This leverages the OpenSearch REST API's ability to handle multiple indices in a single request, reducing network overhead compared to sequential calls.
    -   Added logic to extract "Associated Models" by recursively searching mappings for `model_id` (crucial for Neural Search).
    -   Formatted output using `rich` Tables and Panels for readability.

### C. Feature: Enhanced Index Analytics (`index info`)
-   **Goal**: Provide a deep-dive report on index health, structure, and query optimization tips.
-   **Implementation**:
    -   **Stats Integration**: Fetches `_stats` to display Docs Count, Deleted Docs, Store Size, and Segment Count.
    -   **Field Analysis**: Recursively parses mappings to display a table of fields with:
        -   **Type**: (keyword, text, date, knn_vector, etc.)
        -   **Analyzed Status**: Yes/No.
        -   **Best Query**: Suggests `term` for keywords, `match` for text, `range` for dates.
        -   **Warnings**: Flags potential issues like "No Aggs" on text fields without fielddata.
    -   **Advanced Settings**: Scans for critical performance settings (`refresh_interval`, `translog`, `sort.field`) and displays their impact.

### D. CLI Integration
-   **Command**: `opensearch-manager index info <indices...>`
-   **Global Flags**: Added `--dry-run` and `-qh` / `--query-history` to the main callback, passing state via `ctx.obj`.
-   **Config Flag**: Added `--config` to specify custom YAML configuration.

### E. Verification & Testing
-   **Live Test**: Verified against a running OpenSearch instance with `patronidata` indices.
-   **Unit Tests**:
    -   `tests/test_client.py`: Mocked `requests` to verify Dry Run logic (no calls) and History logic (file creation).
    -   `tests/test_config.py`: Verified YAML loading and default fallbacks.
-   **Code Quality**: Ran `ruff check . --fix` and `ruff format .` to ensure compliance.
