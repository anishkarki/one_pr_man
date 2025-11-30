# Usage Guide

This guide provides instructions on how to configure and use the `opensearch-manager` CLI tool.

## Configuration

The tool uses environment variables for configuration. You can set these in your shell or use a `.env` file in the project root.

| Variable | Default | Description |
| :--- | :--- | :--- |
| `APP_ENV` | `dev` | The application environment (e.g., `dev`, `prod`). |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `JSON_LOGS` | `False` | If `True`, logs will be output in JSON format. |

**Example `.env` file:**
```bash
APP_ENV=dev
LOG_LEVEL=DEBUG
JSON_LOGS=False
```

## CLI Commands

The tool is invoked using the `opensearch-manager` command.

### Basic Usage

Check if the tool is running and view the current environment settings:

```bash
opensearch-manager
```

**Output:**
```text
Hello! env=dev level=INFO
```

### Help

To see available commands and options:

```bash
opensearch-manager --help
```

### Hello Command

A simple command to verify the CLI is working.

```bash
opensearch-manager hello --name "OpenSearch User"
```

**Output:**
```text
Hello, OpenSearch User!
```

## Index Management

### Get Index Information

Retrieve detailed information about one or more indices, including health stats, mappings, and query optimization tips.

```bash
opensearch-manager index info <index_patterns...>
```

**Arguments:**
*   `index_patterns`: One or more index names or wildcard patterns (e.g., `logs-*`, `my-index`).

**Output Includes:**
1.  **Overview & Health**: Shard count, Replica count, Docs count, Deleted docs, Store size, Refresh interval.
2.  **Advanced Settings**: Critical settings like `translog` durability, `max_result_window`, and `sort.field`.
3.  **Field Analysis**: A table showing every field's type, whether it is analyzed, the best query types to use, and performance warnings (e.g., "High Memory" for fielddata).
4.  **Analysis Settings**: Custom analyzers and normalizers if defined.

**Example:**
```bash
opensearch-manager index info "patroni*"
```

## Future Commands

As the tool evolves, more commands will be added for managing OpenSearch resources:

-   `index`: Manage indices (create, delete, reindex).
-   `pipeline`: Manage ingest pipelines.
-   `model`: Manage ML models.
