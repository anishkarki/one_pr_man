from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.layout import Layout
import json
from ..client import OpenSearchClient

console = Console()


def get_index_details(client: OpenSearchClient, index_patterns: List[str]):
    """
    Fetches and displays details for the given index patterns.
    """
    # Join patterns with comma for the API call
    path = ",".join(index_patterns)

    try:
        response = client.get(path, tag="get_index_details")
        # Also fetch stats for these indices
        stats_response = client.get(f"{path}/_stats", tag="get_index_stats")
    except Exception as e:
        console.print(f"[bold red]Error fetching index details:[/bold red] {e}")
        return

    if not response:
        if client.dry_run:
            console.print("[dim]Dry run: No response to parse.[/dim]")
        else:
            console.print(
                f"[yellow]No indices found matching: {index_patterns}[/yellow]"
            )
        return

    # If dry run, stats_response might be empty or None
    stats_data = stats_response.get("indices", {}) if stats_response else {}

    for index_name, details in response.items():
        index_stats = stats_data.get(index_name, {})
        _display_single_index(index_name, details, index_stats)


def _display_single_index(index_name: str, details: Dict[str, Any], stats: Dict[str, Any]):
    mappings = details.get("mappings", {})
    settings = details.get("settings", {}).get("index", {})
    aliases = details.get("aliases", {})
    
    # --- 1. Overview & Stats ---
    _display_overview(index_name, settings, aliases, mappings, stats)

    # --- 2. Advanced Settings ---
    _display_advanced_settings(settings)

    # --- 3. Field Analysis ---
    _display_field_analysis(mappings)

    # --- 4. Analysis Components ---
    analysis = settings.get("analysis", {})
    if analysis:
        console.print(
            Panel(
                Syntax(json.dumps(analysis, indent=2), "json", theme="monokai"),
                title="Analysis Settings (Analyzers & Normalizers)",
                expand=False,
            )
        )

    console.print("\n" + "=" * 50 + "\n")


def _display_overview(index_name: str, settings: Dict, aliases: Dict, mappings: Dict, stats: Dict):
    # Extract Settings
    default_pipeline = settings.get("default_pipeline", "None")
    number_of_shards = settings.get("number_of_shards", "N/A")
    number_of_replicas = settings.get("number_of_replicas", "N/A")
    refresh_interval = settings.get("refresh_interval", "1s (default)")
    
    # Extract Stats
    primaries = stats.get("primaries", {})
    total = stats.get("total", {})
    
    docs_count = primaries.get("docs", {}).get("count", "N/A")
    docs_deleted = primaries.get("docs", {}).get("deleted", "N/A")
    store_size = primaries.get("store", {}).get("size_in_bytes", 0)
    segments_count = primaries.get("segments", {}).get("count", "N/A")
    
    # Format Size
    size_mb = f"{store_size / 1024 / 1024:.2f} MB" if isinstance(store_size, (int, float)) else "N/A"

    # Extract Models
    models = _extract_models_from_mapping(mappings)

    table = Table(title=f"Index: [bold cyan]{index_name}[/bold cyan]", box=None)
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")
    table.add_column("Stat", style="magenta")
    table.add_column("Value", style="green")

    table.add_row("Shards", str(number_of_shards), "Docs Count", str(docs_count))
    table.add_row("Replicas", str(number_of_replicas), "Docs Deleted", str(docs_deleted))
    table.add_row("Refresh Interval", refresh_interval, "Store Size", size_mb)
    table.add_row("Default Pipeline", default_pipeline, "Segments", str(segments_count))
    table.add_row("Aliases", ", ".join(aliases.keys()) if aliases else "None", "", "")
    table.add_row("Models", ", ".join(models) if models else "None", "", "")

    console.print(Panel(table, title="Overview & Health", expand=False))


def _display_advanced_settings(settings: Dict):
    # Critical Settings to look for
    critical_keys = [
        "max_result_window",
        "translog.durability",
        "translog.sync_interval",
        "sort.field",
        "sort.order",
        "query.default_field",
        "lifecycle.name"
    ]
    
    table = Table(title="Advanced Settings", show_header=True, header_style="bold magenta", box=None)
    table.add_column("Setting")
    table.add_column("Value")
    table.add_column("Impact")

    found_any = False
    
    # Flatten settings for easier search
    flat_settings = _flatten_dict(settings)
    
    for key, value in flat_settings.items():
        # Check if this key matches any critical key pattern
        for crit in critical_keys:
            if crit in key:
                impact = _get_setting_impact(crit)
                table.add_row(key, str(value), impact)
                found_any = True
                break
    
    if found_any:
        console.print(Panel(table, title="Critical Index Settings", expand=False))


def _get_setting_impact(key: str) -> str:
    impacts = {
        "refresh_interval": "Indexing latency vs Search visibility",
        "max_result_window": "Deep pagination limit (default 10k)",
        "translog": "Crash recovery & Write performance",
        "sort.field": "Faster range/sort queries (Sorted Index)",
        "lifecycle": "ISM Policy attached"
    }
    for k, v in impacts.items():
        if k in key:
            return v
    return "Query/Indexing behavior"


def _display_field_analysis(mappings: Dict):
    properties = mappings.get("properties", {})
    if not properties:
        return

    table = Table(title="Field Analysis & Query Tips", show_header=True, header_style="bold yellow", box=None)
    table.add_column("Field", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Analyzed?", style="magenta")
    table.add_column("Ignore Above", style="blue")
    table.add_column("Best Query", style="white")
    table.add_column("Notes/Warnings", style="red")

    # Recursively get fields
    flat_fields = _flatten_fields(properties)

    for field, details in flat_fields.items():
        ftype = details.get("type", "object")
        analyzed = "Yes" if ftype == "text" else "No"
        ignore_above = str(details.get("ignore_above", "-"))
        
        # Determine Best Query & Notes
        best_query, notes = _analyze_field_usage(ftype, details)
        
        table.add_row(field, ftype, analyzed, ignore_above, best_query, notes)

    console.print(Panel(table, title="Field Analysis", expand=False))


def _analyze_field_usage(ftype: str, details: Dict) -> tuple[str, str]:
    """Returns (Best Query, Notes) based on field type and details."""
    notes = []
    best_query = ""

    if ftype == "keyword":
        best_query = "term, terms, prefix"
        notes.append("Fast filtering")
        if details.get("doc_values") is False:
            notes.append("No Aggs (doc_values=false)")
            
    elif ftype == "text":
        best_query = "match, match_phrase"
        notes.append("Analyzed")
        if details.get("fielddata"):
            notes.append("High Memory (fielddata=true)")
        else:
            notes.append("No Aggs (fielddata=false)")
            
    elif ftype == "date":
        best_query = "range"
        notes.append("Fast range queries")
        
    elif ftype == "nested":
        best_query = "nested"
        notes.append("Slow if many nested docs")
        
    elif ftype == "geo_point":
        best_query = "geo_distance"
        notes.append("Special index structure")
        
    elif ftype == "knn_vector":
        best_query = "knn"
        notes.append("Neural Search / Vector DB")

    return best_query, ", ".join(notes)


def _flatten_fields(properties: Dict, prefix: str = "") -> Dict[str, Dict]:
    """Recursively flattens mapping properties."""
    fields = {}
    for name, details in properties.items():
        full_name = f"{prefix}.{name}" if prefix else name
        
        # Handle 'fields' (multi-fields like .keyword)
        if "fields" in details:
            for sub_name, sub_details in details["fields"].items():
                sub_full_name = f"{full_name}.{sub_name}"
                fields[sub_full_name] = sub_details
        
        if "properties" in details:
            # Nested object or object type
            fields.update(_flatten_fields(details["properties"], full_name))
        else:
            fields[full_name] = details
            
    return fields


def _flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _extract_models_from_mapping(mappings: Dict[str, Any]) -> List[str]:
    """
    Recursively search for 'model_id' in mappings.
    """
    models = []

    def _search(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "model_id":
                    models.append(v)
                else:
                    _search(v)
        elif isinstance(obj, list):
            for item in obj:
                _search(item)

    _search(mappings)
    return list(set(models))
