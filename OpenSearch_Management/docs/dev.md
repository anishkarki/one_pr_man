# Developer Notes: Boundaries, Limitations & Features

This document defines the architectural boundaries, known limitations, and core feature requirements for the `OpenSearch_Management` project.

## 1. Core Philosophy: Dual-Layer Implementation

To ensure maximum flexibility and transparency, the tool must support two distinct modes of operation for interacting with OpenSearch.

### A. Request-Based (Layer 1 - Primary)
*   **Implementation**: Uses the standard `requests` library.
*   **Purpose**: To provide raw, unadulterated access to the OpenSearch REST API. This ensures that we are never limited by the SDK's abstraction and can debug exact JSON payloads.
*   **Priority**: All features must be implemented using `requests` **first**.

### B. SDK-Based (Layer 2 - Secondary)
*   **Implementation**: Uses `opensearch-py`.
*   **Purpose**: To provide a Pythonic, type-safe, and convenient wrapper for common operations once the raw logic is proven.
*   **Priority**: Implemented after the raw request version is verified.

---

## 2. Key Features

### A. Query History (`-qh`)
Every command that interacts with the cluster must support a query history flag.

*   **Flag**: `-qh` / `--query-history`
*   **Behavior**:
    *   Intercepts the request (GET, POST, PUT, DELETE, PATCH).
    *   Saves the full DSL (JSON body), endpoint, and method to a local storage location (e.g., `history_dsl/`).
    *   **Metadata**: Each entry must include:
        *   Timestamp (ISO 8601)
        *   Tag (User-provided or auto-generated from command name)
        *   HTTP Method & Endpoint
*   **Goal**: Build a library of executed queries for audit, replay, or documentation.

### B. Dry Run (`--dry-run`)
Safety mechanism to preview operations without side effects.

*   **Flag**: `--dry-run`
*   **Behavior**:
    *   Constructs the full request (URL, Headers, Body).
    *   **Prints** the request to the console (using `rich` for syntax highlighting).
    *   **Aborts** the network call.
*   **Validation**: Allows the user to verify the generated DSL against their expectations before execution.

---

## 3. Boundaries & Limitations

### Boundaries
*   **Scope**: This tool is strictly for **Management** (Index creation, Mapping updates, Pipeline registration, Model deployment). It is *not* a high-throughput ingestion client or a data visualization tool.
*   **State**: The tool should be stateless where possible, relying on the cluster's state. Local state is limited to configuration (`.env`) and logs/history (`history_dsl/`).

### Limitations
*   **Error Handling**: The `requests` implementation requires robust manual error handling (status codes, timeouts, connection errors) which `opensearch-py` usually handles. We must implement a unified error handler for the raw layer.
*   **Complexity**: Maintaining two implementations for every feature increases code volume. We must use shared interfaces/protocols to keep the CLI logic clean and agnostic of the underlying driver where possible.

---

## 4. Implementation Roadmap

1.  **Infrastructure**: Setup `Context` object to hold `dry_run` and `save_history` states.
2.  **Client Wrapper**: Create a wrapper class that can switch between `requests` and `opensearch-py` (or just wraps `requests` with the history/dry-run logic first).
3.  **Feature: Indices**: Implement `create`, `delete`, `get` using the wrapper.
4.  **Feature: Pipelines**: Implement `put`, `get`, `simulate`.
5.  **Feature: Neural**: Implement Model Group creation and Model registration.
