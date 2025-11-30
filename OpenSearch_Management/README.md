# OpenSearch Management Tool

A Python tool for managing OpenSearch resources (indices, pipelines, models) with enterprise-grade practices.

## Development Setup

1.  **Create Virtual Environment**:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -e .[dev]
    ```

3.  **Run Checks**:
    ```bash
    # Format and Lint
    ruff format .
    ruff check .

    # Type Check
    mypy .

    # Run Tests
    pytest --cov=opensearch_management --cov-report=term-missing
    ```

## Usage

```bash
opensearch-manager --help
```
