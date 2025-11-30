# Design Patterns & Architecture

This document outlines the core design patterns and architectural decisions used in the **OpenSearch Management Tool**. The project follows a modular, CLI-first approach designed for maintainability, testability, and developer experience.

## 1. CLI Architecture (Typer & Click)

The application is built using [Typer](https://typer.tiangolo.com/), which leverages Python type hints to generate CLI interfaces.

### Command Groups & Nesting
We use a hierarchical command structure to organize functionality logically.
- **Main App**: The entry point (`opensearch-manager`).
- **Sub-Typers**: Functional groups like `index` are added as sub-apps.
- **Nested Commands**: Commands like `analyze` are further nested under `index`.

**Structure:**
```python
app = typer.Typer()
index_app = typer.Typer()
analyze_app = typer.Typer()

app.add_typer(index_app, name="index")
index_app.add_typer(analyze_app, name="analyze")
```

### Dependency Injection via Context Object (`ctx.obj`)
We use the **Context Object** pattern to manage state and dependencies across commands. This avoids global variables and allows for cleaner testing.

1.  **Initialization**: The `main` callback initializes the `OpenSearchClient` and global settings (like `dry_run`).
2.  **Injection**: These dependencies are stored in `ctx.obj`.
3.  **Consumption**: Sub-commands retrieve the client from `ctx.obj`.

**Example:**
```python
# In main callback
@app.callback()
def main(ctx: typer.Context, dry_run: bool, ...):
    client = OpenSearchClient(..., dry_run=dry_run)
    ctx.obj = {"client": client}

# In sub-command
@index_app.command("info")
def index_info(ctx: typer.Context, ...):
    client = ctx.obj["client"]  # Ready-to-use client
    get_index_details(client, ...)
```

## 2. Client Abstraction Layer

The `OpenSearchClient` class (`src/opensearch_management/client.py`) serves as a wrapper around the raw HTTP requests. It implements several key patterns:

### The Facade Pattern
The client provides a simplified interface (`get`, `post`, `put`, `delete`) for interacting with the OpenSearch cluster, hiding the complexity of:
-   URL construction.
-   Authentication handling.
-   Error handling and logging.
-   JSON parsing.

### Dry Run Mode (Simulation)
The client implements a "Dry Run" pattern internally. If `dry_run=True` is passed during initialization:
-   **Write operations are intercepted.**
-   The request (Method, URL, Body) is printed to the console using `rich`.
-   No actual network request is sent.
-   This allows users to safely preview destructive actions.

### Query History (Audit/Replay)
If enabled, the client automatically serializes every request body to a JSON file in the history directory. This implements a basic **Command Sourcing** or **Audit Log** pattern, allowing users to replay or inspect generated DSL.

## 3. Separation of Concerns (Service Layer)

The codebase is strictly divided into three layers:

1.  **Interface Layer (`cli.py`)**:
    -   Handles user input (arguments, options).
    -   Manages CLI output formatting.
    -   Orchestrates calls to the logic layer.
    -   *Should not contain business logic.*

2.  **Logic/Service Layer (`logic/`)**:
    -   Contains the actual implementation of features (e.g., `index_operations.py`, `index_analysis.py`).
    -   Accepts the `OpenSearchClient` and raw parameters.
    -   Performs data processing and API interaction.
    -   *Independent of the CLI framework (mostly).*

3.  **Infrastructure Layer (`client.py`, `config.py`, `log_setup.py`)**:
    -   Handles low-level details like HTTP, file I/O, and configuration loading.

## 4. Configuration Management

We use **Pydantic Settings** for configuration management.
-   **Type Safety**: Configuration is defined as Pydantic models (`Settings`, `ConnectionConfig`, `AuthConfig`).
-   **Validation**: Inputs from `user-config.yaml` are validated at startup.
-   **Environment Variables**: Can override file-based settings (standard Pydantic behavior).

## 5. UI/UX Patterns

### Rich Console
We use the `rich` library to enhance the terminal experience:
-   **Tables**: For structured data (e.g., Index Stats, Field Analysis).
-   **Panels**: To group related information visually.
-   **Syntax Highlighting**: For displaying JSON bodies during dry runs.

### Insight Generation
The `index analyze` logic implements a pattern of **"Data + Insight"**. Instead of just dumping raw API responses, the tool:
1.  Parses the response.
2.  Analyzes the data (e.g., "Is this token lowercased?", "Are there multiple tokens?").
3.  Generates actionable advice (e.g., "Use `match_phrase` for this field").

## 6. Logging Strategy

We use `structlog` for structured logging.
-   **Contextual Logging**: Logs include context (method, url) automatically.
-   **Separation**:
    -   `console.print`: For user-facing output (tables, results).
    -   `logger.info/error`: For internal application events and debugging.
