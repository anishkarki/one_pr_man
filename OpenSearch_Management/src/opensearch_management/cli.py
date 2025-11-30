import typer
from typing import List
from rich.console import Console
from .config import get_settings, load_settings
from .log_setup import configure_logging
from .client import OpenSearchClient
from .logic.index_operations import get_index_details
from .logic.index_analysis import simulate_text_analysis, inspect_document_termvectors

app = typer.Typer(help="OpenSearch Management Tool")
index_app = typer.Typer(help="Manage OpenSearch Indices")
app.add_typer(index_app, name="index")

# --- Index Analysis Sub-commands ---
analyze_app = typer.Typer(help="Analyze text tokenization and stored term vectors")
index_app.add_typer(analyze_app, name="analyze")


console = Console()


@app.callback()
def main(
    ctx: typer.Context,
    config: str = typer.Option(
        "user-config.yaml", "--config", "-c", help="Path to configuration file."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate the operation."),
    query_history: bool = typer.Option(
        False, "-qh", "--query-history", help="Save query DSL to history."
    ),
):
    configure_logging()
    # Load settings from the specified config file
    load_settings(config)
    settings = get_settings()
    
    # Initialize the client once and pass it to sub-commands via ctx.obj
    client = OpenSearchClient(
        settings=settings,
        dry_run=dry_run,
        query_history=query_history,
    )
    
    ctx.obj = {
        "dry_run": dry_run, 
        "query_history": query_history,
        "client": client
    }


@app.command()
def hello(name: str = "world"):
    """Simple hello command."""
    settings = get_settings()
    console.print(f"Hello, {name}! Env: {settings.settings.app_env}")


@index_app.command("info")
def index_info(
    ctx: typer.Context,
    indices: List[str] = typer.Argument(..., help="List of index names or patterns."),
):
    """
    Get detailed information about one or more indices.
    """
    # Retrieve the client from the context
    client = ctx.obj["client"]
    get_index_details(client, indices)

@analyze_app.command("simulate")
def analyze_simulate(
    ctx: typer.Context,
    index: str = typer.Argument(..., help="The index name"),
    text: str = typer.Argument(..., help="The raw text to analyze"),
    field: str = typer.Option(None, "--field", "-f", help="Use the analyzer configured for this specific field"),
    analyzer: str = typer.Option(None, "--analyzer", "-a", help="Force a specific analyzer (e.g., standard, simple, whitespace)")
):
    """
    Simulate how text is tokenized by an index (using _analyze API).
    """
    client = ctx.obj["client"]
    simulate_text_analysis(client, index, text, field, analyzer)

@analyze_app.command("doc")
def analyze_doc(
    ctx: typer.Context,
    index: str = typer.Argument(..., help="The index name"),
    doc_id: str = typer.Argument(..., help="The document ID to inspect"),
    fields: str = typer.Option(None, "--fields", "-f", help="Comma-separated list of fields to inspect (default: all)")
):
    """
    Inspect how an existing document was tokenized (using _termvectors API).
    """
    client = ctx.obj["client"]
    field_list = fields.split(",") if fields else None
    inspect_document_termvectors(client, index, doc_id, field_list)

if __name__ == "__main__":
    app()

