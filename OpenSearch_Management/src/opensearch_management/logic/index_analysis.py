from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from ..client import OpenSearchClient

console = Console()

def simulate_text_analysis(client: OpenSearchClient, index_name: str, text: str, field: str = None, analyzer: str = None):
    """
    Uses the OpenSearch _analyze API to show how text is tokenized.
    """
    url = f"{index_name}/_analyze"
    
    body = {"text": text}
    
    # Priority: Field > Analyzer > Default (Standard)
    if field:
        body["field"] = field
        title_context = f"Field: [bold cyan]{field}[/bold cyan]"
    elif analyzer:
        body["analyzer"] = analyzer
        title_context = f"Analyzer: [bold cyan]{analyzer}[/bold cyan]"
    else:
        title_context = "Analyzer: [bold cyan]standard (default)[/bold cyan]"

    try:
        response = client.post(url, body=body, tag="analyze_text_simulation")
    except Exception as e:
        console.print(f"[bold red]Error analyzing text:[/bold red] {e}")
        return

    if not response:
        if client.dry_run:
            console.print("[dim]Dry run: No response to parse.[/dim]")
        return

    tokens = response.get("tokens", [])
    
    if not tokens:
        console.print(f"[yellow]No tokens produced for input text using {title_context}[/yellow]")
        return

    table = Table(title=f"Token Analysis Simulation ({title_context})", box=None)
    table.add_column("Token", style="green bold")
    table.add_column("Position", justify="right")
    table.add_column("Type", style="magenta")
    table.add_column("Start Offset")
    table.add_column("End Offset")

    for t in tokens:
        table.add_row(
            t.get("token"),
            str(t.get("position")),
            t.get("type"),
            str(t.get("start_offset")),
            str(t.get("end_offset"))
        )

    console.print(Panel(table, expand=False))
    
    # Insight generation
    _display_analysis_insights(tokens, field)

def inspect_document_termvectors(client: OpenSearchClient, index_name: str, doc_id: str, fields: List[str] = None):
    """
    Uses the _termvectors API to inspect how a specific document was tokenized.
    """
    url = f"{index_name}/_termvectors/{doc_id}"
    
    # Request body to specify fields and ensure we get term info
    body = {
        "fields": fields if fields else ["*"],
        "positions": True,
        "offsets": True,
        "payloads": False,
        "term_statistics": True,
        "field_statistics": False
    }

    try:
        response = client.post(url, body=body, tag="inspect_termvectors")
    except Exception as e:
        console.print(f"[bold red]Error fetching term vectors:[/bold red] {e}")
        return

    if not response:
        if client.dry_run:
            console.print("[dim]Dry run: No response to parse.[/dim]")
        return

    if not response.get("found", False):
        console.print(f"[bold red]Document {doc_id} not found in index {index_name}[/bold red]")
        return

    term_vectors = response.get("term_vectors", {})
    
    if not term_vectors:
        console.print(f"[yellow]No term vectors found. Ensure the fields are indexed and store term vectors.[/yellow]")
        return

    for field_name, data in term_vectors.items():
        terms = data.get("terms", {})
        
        table = Table(title=f"Stored Tokens: [bold cyan]{field_name}[/bold cyan]", box=None)
        table.add_column("Token", style="green bold")
        table.add_column("Freq", justify="right")
        table.add_column("Doc Freq", justify="right", style="dim")
        table.add_column("Positions", style="blue")

        # Sort terms alphabetically
        for term, details in sorted(terms.items()):
            freq = str(details.get("term_freq", "-"))
            doc_freq = str(details.get("doc_freq", "-"))
            
            # Extract positions list
            tokens_info = details.get("tokens", [])
            positions = ", ".join([str(t.get("position")) for t in tokens_info])
            
            table.add_row(term, freq, doc_freq, positions)

        console.print(Panel(table, expand=False))


def _display_analysis_insights(tokens: List[Dict], field: str):
    """Provides tips based on the tokens generated."""
    token_texts = [t.get("token") for t in tokens]
    
    console.print("\n[bold underline]Query Insights:[/bold underline]")
    
    if len(tokens) == 1 and tokens[0]['token'] == tokens[0].get('token', '').lower():
        console.print(f"• This looks like a [cyan]Keyword[/cyan] or exact match. Use [green]term[/green] query: {{ \"{field or 'field'}\": \"{token_texts[0]}\" }}")
    
    if len(tokens) > 1:
        console.print(f"• Text was split into {len(tokens)} tokens.")
        console.print(f"• For exact phrase match, use [green]match_phrase[/green]: {{ \"{field or 'field'}\": \"...\" }}")
        console.print(f"• For loose match, use [green]match[/green] (OR logic).")
        
    # Check for punctuation removal
    has_punctuation = any(not c.isalnum() for c in "".join(token_texts))
    if not has_punctuation:
        console.print("• [yellow]Note:[/yellow] Punctuation seems to be removed. Searching for special chars might fail.")