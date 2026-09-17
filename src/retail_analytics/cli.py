"""Command-line entry point: ``retail-analytics run``."""

import logging
from pathlib import Path
from typing import Annotated

import typer

from retail_analytics.config import Settings
from retail_analytics.errors import PipelineError
from retail_analytics.pipeline import run_pipeline

app = typer.Typer(add_completion=False, help="Retail analytics pipeline.")


@app.callback()
def main() -> None:
    """Validate retail data, compute KPIs and write a report."""


@app.command()
def run(
    data_dir: Annotated[Path, typer.Option(help="Folder containing the input CSVs.")] = Path(
        "data"
    ),
    output_dir: Annotated[Path, typer.Option(help="Folder the report is written to.")] = Path(
        "output"
    ),
    store: Annotated[
        list[str] | None, typer.Option(help="Store id to analyse. Repeat for several.")
    ] = None,
) -> None:
    """Run the pipeline and write the report.

    Args:
        data_dir (Path): Folder containing the input CSVs.
        output_dir (Path): Folder the report is written to.
        store (list[str] | None): Store ids to analyse; None analyses every store.

    Raises:
        typer.Exit: With code 1 when the run stops on a PipelineError.
    """
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings(data_dir=data_dir, output_dir=output_dir, stores=tuple(store or ()))
    try:
        result = run_pipeline(settings)
    except PipelineError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from None
    typer.echo(f"Report written to {result.output_dir / 'report.html'}")
