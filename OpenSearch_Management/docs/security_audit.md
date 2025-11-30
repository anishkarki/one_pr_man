# Security Audit Report

**Date:** November 30, 2025
**Target:** OpenSearch Management Tool

## Executive Summary
A security review of the codebase identified several potential vulnerabilities, primarily related to configuration management, data persistence, and default settings. The most critical issues involve the potential for credential leakage via version control and insecure default SSL settings.

## Findings

### 1. Insecure Default SSL Configuration (High)
-   **Location:** `src/opensearch_management/config.py`
-   **Issue:** The `verify_certs` setting defaults to `False`.
-   **Risk:** This disables SSL certificate verification, making the application vulnerable to Man-in-the-Middle (MitM) attacks. An attacker could intercept and modify traffic between the tool and the OpenSearch cluster.
-   **Recommendation:** Change the default to `True`. Users working with self-signed certificates should explicitly opt-in to insecure mode.

### 2. Credential Leakage Risk (High)
-   **Location:** `user-config.yaml` (Root Directory)
-   **Issue:** The configuration file containing credentials (`username`, `password`) was not excluded from version control (`.gitignore`).
-   **Risk:** Committing this file would expose sensitive credentials to anyone with access to the repository.
-   **Remediation:** Added `user-config.yaml` to `.gitignore`.

### 3. Sensitive Data Persistence in History (Medium)
-   **Location:** `src/opensearch_management/client.py` (`_save_history` method)
-   **Issue:** The tool saves the full body of every request to the `history_dsl/` directory when `--query-history` is enabled.
-   **Risk:** If a request contains sensitive information (e.g., indexing PII, creating users with passwords), it is stored in plain text on the disk.
-   **Remediation:**
    -   Added `history_dsl/` to `.gitignore`.
    -   Consider implementing a redaction mechanism for sensitive fields (e.g., `password`, `token`) before saving.

### 4. Lack of Environment Variable Support (Medium)
-   **Location:** `src/opensearch_management/config.py`
-   **Issue:** The configuration loader relies primarily on the YAML file. It does not explicitly support overriding secrets via environment variables (e.g., `OPENSEARCH_PASSWORD`).
-   **Risk:** Forces users to write credentials to disk, increasing the attack surface.
-   **Recommendation:** Update `Settings` to use `pydantic-settings`'s `BaseSettings` to automatically read from environment variables.

### 5. Potential Logging of Sensitive Data (Low)
-   **Location:** `src/opensearch_management/client.py`
-   **Issue:** `logger.error("Response content", content=e.response.text)` logs the full error response.
-   **Risk:** If an error response from OpenSearch contains sensitive data (unlikely but possible), it will be logged.
-   **Recommendation:** Ensure logs are stored securely and consider truncating or sanitizing error responses.

## Actions Taken
-   [x] Updated `.gitignore` to exclude `user-config.yaml` and `history_dsl/`.
-   [ ] Update `config.py` to default `verify_certs` to `True`.
-   [ ] Refactor `config.py` to support Environment Variables.

