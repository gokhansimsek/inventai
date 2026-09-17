"""Writers turn a Report into files. Add a format by adding a writer."""

from pathlib import Path
from typing import Protocol

import pandas as pd
from jinja2 import Environment, PackageLoader, select_autoescape

from retail_analytics.reporting.report import Report


class Writer(Protocol):
    def write(self, report: Report, out_dir: Path) -> list[Path]:
        """Write a report in this writer's format.

        Args:
            report (Report): The report content to write.
            out_dir (Path): Folder to write into; created if missing.

        Returns:
            list[Path]: Every file written.
        """
        ...


class CsvWriter:
    """Machine-readable output: one CSV per KPI, quarantine table and issues table."""

    def write(self, report: Report, out_dir: Path) -> list[Path]:
        """Write the report tables as CSV files.

        Writes ``data_quality.csv`` and ``row_counts.csv``, then every non-empty table
        into ``kpis/``, ``quarantine/`` and ``issues/``.

        Args:
            report (Report): The report content to write.
            out_dir (Path): Folder to write into; created if missing.

        Returns:
            list[Path]: Every CSV file written.
        """
        groups = {
            "kpis": report.kpis,
            "quarantine": report.quarantine,
            "issues": report.issues,
        }
        written = [self._write(report.data_quality, out_dir / "data_quality.csv")]
        written.append(self._write(report.row_counts, out_dir / "row_counts.csv"))
        for folder, tables in groups.items():
            for name, frame in tables.items():
                if len(frame):
                    written.append(self._write(frame, out_dir / folder / f"{name}.csv"))
        return written

    @staticmethod
    def _write(frame: pd.DataFrame, path: Path) -> Path:
        """Write one table to a CSV file, creating parent folders.

        Args:
            frame (pd.DataFrame): The table to write.
            path (Path): Destination file.

        Returns:
            Path: The path written, for the caller's list of outputs.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path, index=False)
        return path


class HtmlWriter:
    """Stakeholder-facing report: a single self-contained HTML file."""

    def __init__(self) -> None:
        """Load report templates from the package with HTML autoescaping."""
        self._env = Environment(
            loader=PackageLoader("retail_analytics.reporting"),
            autoescape=select_autoescape(),
        )

    def write(self, report: Report, out_dir: Path) -> list[Path]:
        """Render the report as a single self-contained HTML file.

        Args:
            report (Report): The report content to render.
            out_dir (Path): Folder to write ``report.html`` into; created if missing.

        Returns:
            list[Path]: The path of ``report.html``.
        """
        path = out_dir / "report.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        html = self._env.get_template("report.html.j2").render(report=report, table=_table)
        path.write_text(html, encoding="utf-8")
        return [path]


def _table(frame: pd.DataFrame) -> str:
    """Render a DataFrame as an HTML table for the report.

    Args:
        frame (pd.DataFrame): The table to render.

    Returns:
        str: HTML ``<table>`` markup with thousands separators and 2 decimal places.
    """
    return frame.to_html(index=False, classes="data", border=0, float_format="{:,.2f}".format)
