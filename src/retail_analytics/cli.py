"""Command-line entry point: ``retail-analytics run``."""

from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from retail_analytics.config import load_settings
from retail_analytics.errors import PipelineError
from retail_analytics.logging_setup import configure_logging
from retail_analytics.pipeline import run_pipeline

DEFAULT_CONFIG = Path("config/default.yaml")
DATE_FORMATS = ["%Y-%m-%d"]

app = typer.Typer(add_completion=False, help="Retail analytics pipeline.")


@app.callback()
def main() -> None:
    """Validate retail data, compute KPIs and write a report."""


@app.command()
def run(  # noqa: PLR0917 -- typer maps each CLI option to a parameter
    config: Annotated[
        Path | None,
        typer.Option(help=f"YAML settings file. Defaults to {DEFAULT_CONFIG} if present."),
    ] = None,
    data_dir: Annotated[Path | None, typer.Option(help="Folder containing the input CSVs.")] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option(help="Folder for this run's report. Defaults to output/<timestamp>."),
    ] = None,
    store: Annotated[
        list[str] | None, typer.Option(help="Store id to analyse. Repeat for several.")
    ] = None,
    region: Annotated[
        list[str] | None, typer.Option(help="Region to analyse. Repeat for several.")
    ] = None,
    date_from: Annotated[
        datetime | None,
        typer.Option("--from", formats=DATE_FORMATS, help="First date to analyse (YYYY-MM-DD)."),
    ] = None,
    date_to: Annotated[
        datetime | None,
        typer.Option("--to", formats=DATE_FORMATS, help="Last date to analyse (YYYY-MM-DD)."),
    ] = None,
) -> None:
    """Run the pipeline and write the report.

    Command-line flags override the values in the config file.

    Args:
        config (Path | None): YAML settings file; None uses the default file if present.
        data_dir (Path | None): Folder containing the input CSVs.
        output_dir (Path | None): Folder for this run's output; None uses
            ``output/<timestamp>`` unless the config file sets it.
        store (list[str] | None): Store ids to analyse; None keeps the config's selection.
        region (list[str] | None): Regions to analyse; None keeps the config's selection.
        date_from (datetime | None): First date to analyse, inclusive.
        date_to (datetime | None): Last date to analyse, inclusive.

    Raises:
        typer.Exit: With code 1 when the configuration is invalid or the run stops on a
            PipelineError.
    """
    if config is None and DEFAULT_CONFIG.is_file():
        config = DEFAULT_CONFIG
    try:
        settings = load_settings(
            config,
            {
                "data_dir": data_dir,
                "output_dir": output_dir,
                "stores": tuple(store or ()),
                "regions": tuple(region or ()),
                "date_from": date_from.date() if date_from else None,
                "date_to": date_to.date() if date_to else None,
            },
        )
        if "output_dir" not in settings.model_fields_set:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            settings = settings.model_copy(update={"output_dir": Path("output") / timestamp})
        configure_logging(settings.output_dir / "run.log.jsonl")
        result = run_pipeline(settings)
    except PipelineError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from None
    typer.echo(f"Report written to {result.output_dir / 'report.html'}")
