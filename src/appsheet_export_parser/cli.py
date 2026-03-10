"""CLI entry point — thin shell around the library.

Usage:
    appsheet-parse pdf myapp-docs.pdf -o myapp.json
    appsheet-parse pdf myapp-docs.pdf -o myapp.json --config configs/myapp.yaml -v
    appsheet-parse url <app-id> -o myapp.json -v
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console

app = typer.Typer(
    name="appsheet-parse",
    help="Parse AppSheet documentation exports into structured JSON.",
    no_args_is_help=True,
)
console = Console()


def _print_summary(export: dict) -> None:
    """Print a summary of the parsed export."""
    meta = export.get("metadata", {})
    summary = meta.get("summary", {})
    console.print()
    console.print("[bold green]Parsed successfully![/bold green]")
    console.print(f"  App: {meta.get('app_name', 'Unknown')}")
    console.print(f"  Tables: {summary.get('total_tables', 0)} "
                  f"({summary.get('core_tables', 0)} core, "
                  f"{summary.get('process_tables', 0)} process)")
    console.print(f"  Columns: {summary.get('total_columns', 0)}")
    console.print(f"  Relationships: {summary.get('total_relationships', 0)}")
    console.print(f"  Actions: {summary.get('total_actions', 0)}")
    views = export.get("views", [])
    format_rules = export.get("format_rules", [])
    if views:
        console.print(f"  Views: {len(views)}")
    if format_rules:
        console.print(f"  Format Rules: {len(format_rules)}")


@app.command()
def pdf(
    source: str = typer.Argument(
        ...,
        help="Path to AppSheet documentation PDF",
    ),
    output: Path = typer.Option(
        None, "-o", "--output",
        help="Output JSON file path",
    ),
    config: Optional[Path] = typer.Option(
        None, "--config",
        help="App config YAML for table classification",
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose",
        help="Print progress details",
    ),
) -> None:
    """Parse an AppSheet documentation PDF into structured JSON."""
    from .parser import parse_pdf as _parse_pdf

    source_path = Path(source)

    if not source_path.exists():
        console.print(f"[red]File not found: {source_path}[/red]")
        raise typer.Exit(1)

    # Default output path
    if output is None:
        output = source_path.with_suffix(".json")

    try:
        export = _parse_pdf(
            pdf_path=source_path,
            output_path=output,
            app_config_path=config,
            verbose=verbose,
        )
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    _print_summary(export)
    console.print(f"  Output: {output}")


@app.command()
def url(
    app_id: str = typer.Argument(
        ...,
        help="AppSheet app ID (from your app's URL)",
    ),
    output: Path = typer.Option(
        None, "-o", "--output",
        help="Output JSON file path",
    ),
    config: Optional[Path] = typer.Option(
        None, "--config",
        help="App config YAML for table classification",
    ),
    chrome_profile: str = typer.Option(
        "/tmp/chrome-appsheet", "--chrome-profile",
        help="Chrome user-data-dir with auth cookies",
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose",
        help="Print progress details",
    ),
) -> None:
    """Parse an AppSheet app directly from its live documentation URL."""
    from .parser import parse_url as _parse_url

    if output is None:
        output = Path(f"{app_id}.json")

    try:
        export = _parse_url(
            app_id=app_id,
            output_path=output,
            app_config_path=config,
            chrome_profile=chrome_profile,
            verbose=verbose,
        )
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    _print_summary(export)
    console.print(f"  Output: {output}")


@app.command(name="parse")
def parse_legacy(
    source: str = typer.Argument(
        ...,
        help="Path to AppSheet documentation PDF (legacy — use 'pdf' subcommand)",
    ),
    output: Path = typer.Option(
        None, "-o", "--output",
        help="Output JSON file path",
    ),
    config: Optional[Path] = typer.Option(
        None, "--config",
        help="App config YAML for table classification",
    ),
    verbose: bool = typer.Option(
        False, "-v", "--verbose",
        help="Print progress details",
    ),
) -> None:
    """[Legacy] Parse an AppSheet documentation export. Use 'pdf' or 'url' instead."""
    if source.startswith("http"):
        console.print("[red]Use 'appsheet-parse url <app-id>' for URL mode.[/red]")
        raise typer.Exit(1)

    # Forward to pdf command
    pdf(source=source, output=output, config=config, verbose=verbose)


if __name__ == "__main__":
    app()
