import json
import os
import datetime
from typing import Any, Dict, Optional, Union
import requests
from rich.console import Console
from rich.syntax import Syntax
import structlog
from .config import Settings

logger = structlog.get_logger()
console = Console()


class OpenSearchClient:
    def __init__(
        self, settings: Settings, dry_run: bool = False, query_history: bool = False
    ):
        self.settings = settings
        self.dry_run = dry_run
        self.query_history = query_history

        # Use the first host for now, or handle multiple hosts logic later
        host = (
            settings.connection.hosts[0] if settings.connection.hosts else "localhost"
        )
        port = settings.connection.port
        protocol = "https" if settings.connection.use_ssl else "http"

        self.base_url = f"{protocol}://{host}:{port}"

        if settings.auth.type == "basic":
            self.auth = (settings.auth.username, settings.auth.password)
        else:
            # TODO: Implement token auth
            self.auth = None

        self.verify_certs = settings.connection.verify_certs

        # Ensure history directory exists if needed
        if self.query_history:
            history_dir = settings.settings.history_dir
            os.makedirs(history_dir, exist_ok=True)

    def _save_history(
        self,
        method: str,
        url: str,
        body: Optional[Dict[str, Any]] = None,
        tag: str = "query",
    ):
        timestamp = datetime.datetime.now().isoformat()
        history_dir = self.settings.settings.history_dir
        filename = f"{history_dir}/{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{tag}.json"

        history_entry = {
            "timestamp": timestamp,
            "tag": tag,
            "method": method,
            "url": url,
            "body": body,
        }

        with open(filename, "w") as f:
            json.dump(history_entry, f, indent=2)

        logger.info("Query saved to history", filename=filename)

    def request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        tag: str = "query",
    ) -> Union[Dict[str, Any], requests.Response]:
        url = f"{self.base_url}/{path.lstrip('/')}"

        # Prepare headers
        headers = {"Content-Type": "application/json"}

        # Handle Dry Run
        if self.dry_run:
            console.print(f"[bold yellow]DRY RUN: {method} {url}[/bold yellow]")
            if params:
                console.print(f"Params: {params}")
            if body:
                syntax = Syntax(
                    json.dumps(body, indent=2),
                    "json",
                    theme="monokai",
                    line_numbers=True,
                )
                console.print(syntax)
            return {}  # Return empty dict for dry run

        # Handle Query History
        if self.query_history:
            self._save_history(method, url, body, tag)

        # Execute Request
        try:
            response = requests.request(
                method=method,
                url=url,
                auth=self.auth,
                json=body,
                params=params,
                headers=headers,
                verify=self.verify_certs,
                timeout=30,
            )
            response.raise_for_status()

            # Try to parse JSON, otherwise return response object or text
            try:
                return response.json()
            except json.JSONDecodeError:
                return response

        except requests.exceptions.RequestException as e:
            logger.error("Request failed", method=method, url=url, error=str(e))
            if hasattr(e, "response") and e.response is not None:
                logger.error("Response content", content=e.response.text)
            raise

    def get(
        self, path: str, params: Optional[Dict[str, Any]] = None, tag: str = "get"
    ) -> Any:
        return self.request("GET", path, params=params, tag=tag)

    def post(
        self,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        tag: str = "post",
    ) -> Any:
        return self.request("POST", path, body=body, params=params, tag=tag)

    def put(
        self,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        tag: str = "put",
    ) -> Any:
        return self.request("PUT", path, body=body, params=params, tag=tag)

    def delete(
        self, path: str, params: Optional[Dict[str, Any]] = None, tag: str = "delete"
    ) -> Any:
        return self.request("DELETE", path, params=params, tag=tag)
