"""CLI entry point — thin shell around the library.

Usage:
    appsheet-parse parse myapp-docs.pdf -o myapp.json
    appsheet-parse parse myapp-docs.pdf -o myapp.json --config configs/myapp.yaml -v
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


@app.command()
def parse(
    source: str = typer.Argument(
        ...,
        help="Path to AppSheet documentation PDF (or URL in future versions)",
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
    """Parse an AppSheet documentation export into structured JSON."""
    from .parser import parse_pdf

    source_path = Path(source)

    if source.startswith("http"):
        console.print("[red]URL mode not yet supported. Use a PDF file path.[/red]")
        raise typer.Exit(1)

    if not source_path.exists():
        console.print(f"[red]File not found: {source_path}[/red]")
        raise typer.Exit(1)

    # Default output path
    if output is None:
        output = source_path.with_suffix(".json")

    try:
        export = parse_pdf(
            pdf_path=source_path,
            output_path=output,
            app_config_path=config,
            verbose=verbose,
        )
    except RuntimeError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)

    # Summary
    meta = export.get("metadata", {})
    summary = meta.get("summary", {})
    console.print()
    console.print(f"[bold green]Parsed successfully![/bold green]")
    console.print(f"  App: {meta.get('app_name', 'Unknown')}")
    console.print(f"  Tables: {summary.get('total_tables', 0)} "
                  f"({summary.get('core_tables', 0)} core, "
                  f"{summary.get('process_tables', 0)} process)")
    console.print(f"  Columns: {summary.get('total_columns', 0)}")
    console.print(f"  Relationships: {summary.get('total_relationships', 0)}")
    console.print(f"  Actions: {summary.get('total_actions', 0)}")
    console.print(f"  Output: {output}")


if __name__ == "__main__":
    app()
