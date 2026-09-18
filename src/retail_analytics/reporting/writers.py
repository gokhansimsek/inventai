"""Writers turn a Report into files. Add a format by adding a writer."""

from collections.abc import Callable
from html import escape
from pathlib import Path
from typing import Protocol

import pandas as pd
from jinja2 import Environment, PackageLoader, select_autoescape

from retail_analytics.reporting import charts, cube
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
    """Stakeholder-facing report: a single self-contained HTML file that works offline."""

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
        html = self._env.get_template("report.html.j2").render(
            report=report,
            charts=_charts(report) if report.has_sales else {},
            plotly_script=charts.plotly_script() if report.has_sales else "",
            table=_table,
            money=_money,
            percent=_percent,
            findings=_findings(report.data_quality),
            turnover_period=_turnover_period(report.turnover_weeks),
            quality=_quality_summary(report),
            quiet_checks=int(
                (report.data_quality[["fixed", "rejected", "flagged"]].sum(axis=1) == 0).sum()
            ),
            facts_payload=cube.facts_json(
                report.facts, report.top_n, report.min_units_for_margin_pct
            )
            if report.has_sales
            else "",
            regions=sorted(report.facts["stores"]["region"].unique()),
            date_min=_bound(report, "min"),
            date_max=_bound(report, "max"),
        )
        path.write_text(html, encoding="utf-8")
        return [path]


def _charts(report: Report) -> dict[str, str]:
    """Build the report's charts from its KPI tables.

    Args:
        report (Report): Report whose KPI tables contain sales.

    Returns:
        dict[str, str]: Chart HTML fragments keyed by name.
    """
    kpis = report.kpis
    by_store = kpis["sales_by_store"]
    by_store_margin = by_store.sort_values("gross_margin_pct", ascending=False)
    by_category = kpis["sales_by_category"]
    by_category_margin = by_category.sort_values("gross_margin_pct", ascending=False)
    by_day = kpis["sales_by_day"]
    turnover = kpis["inventory_turnover_by_store"]
    return {
        "revenue_by_store": charts.horizontal_bars(
            by_store["store_name"].tolist(), by_store["revenue"].tolist(), ",.0f", "Revenue (TRY)"
        ),
        "margin_by_store": charts.horizontal_bars(
            by_store_margin["store_name"].tolist(),
            by_store_margin["gross_margin_pct"].tolist(),
            ".1%",
            "Gross margin",
        ),
        "revenue_by_category": charts.horizontal_bars(
            by_category["category"].tolist(),
            by_category["revenue"].tolist(),
            ",.0f",
            "Revenue (TRY)",
        ),
        "margin_by_category": charts.horizontal_bars(
            by_category_margin["category"].tolist(),
            by_category_margin["gross_margin_pct"].tolist(),
            ".1%",
            "Gross margin",
        ),
        "revenue_by_day": charts.line(
            by_day["day"].tolist(), by_day["revenue"].tolist(), ",.0f", "Revenue (TRY)"
        ),
        "turnover_by_store": charts.horizontal_bars(
            turnover["store_name"].tolist(), turnover["turnover"].tolist(), ".2f", "Turnover"
        )
        if not turnover.empty
        else "",
    }


def _turnover_period(weeks: list[pd.Timestamp]) -> str:
    """Describe the days covered by the inventory weeks used for turnover.

    Args:
        weeks (list[pd.Timestamp]): Start dates (Mondays) of the weeks used, in order.

    Returns:
        str: E.g. ``"2024-03-04 to 2024-03-31"``; empty if no week was used.
    """
    if not weeks:
        return ""
    last_day = weeks[-1] + pd.Timedelta(days=6)
    return f"{weeks[0]:%Y-%m-%d} to {last_day:%Y-%m-%d}"


def _bound(report: Report, edge: str) -> str:
    """Give the first or last day the filter controls may be set to.

    Args:
        report (Report): The report content, whose sales facts carry every selected day.
        edge (str): ``"min"`` for the first day, ``"max"`` for the last.

    Returns:
        str: The day as ``YYYY-MM-DD``; empty when the selection holds no sales.
    """
    days = report.facts["sales"]["day"]
    if days.empty:
        return ""
    day = days.min() if edge == "min" else days.max()
    return str(day.strftime("%Y-%m-%d"))


def _quality_summary(report: Report) -> dict[str, int]:
    """Total what validation did, for the data-quality tiles and the reconciliation line.

    Args:
        report (Report): The report content, with per-rule counts and per-table row counts.

    Returns:
        dict[str, int]: Totals keyed ``fixed``, ``rejected``, ``flagged``, ``raw`` and
            ``clean``, summed across every rule and every table.
    """
    counts = report.data_quality[["fixed", "rejected", "flagged"]].sum()
    return {
        "fixed": int(counts["fixed"]),
        "rejected": int(counts["rejected"]),
        "flagged": int(counts["flagged"]),
        "raw": int(report.row_counts["raw"].sum()),
        "clean": int(report.row_counts["clean"].sum()),
    }


SEVERITY_STATUS = {"fix": "good", "flag": "warning", "reject": "critical"}


def _severity_badge(severity: str) -> str:
    """Render a severity as a status dot beside its name.

    The dot carries the status color and the word carries the meaning, so severity is
    never encoded by color alone.

    Args:
        severity (str): Rule severity, one of ``fix``, ``flag`` or ``reject``.

    Returns:
        str: HTML markup for the badge, with the severity text escaped.
    """
    status = SEVERITY_STATUS.get(severity, "warning")
    return f'<span class="badge {status}"><span class="dot"></span>{escape(severity)}</span>'


def _findings(data_quality: pd.DataFrame) -> pd.DataFrame:
    """Keep the rules that changed, removed or flagged at least one row.

    Args:
        data_quality (pd.DataFrame): One row per rule with fixed, rejected and flagged
            counts.

    Returns:
        pd.DataFrame: Rules with a non-zero count, in execution order.
    """
    counts = data_quality[["fixed", "rejected", "flagged"]]
    return data_quality[counts.sum(axis=1) > 0]


COLUMN_LABELS = {
    "store_id": "Store",
    "store_name": "Store name",
    "article_id": "Article",
    "article_name": "Article name",
    "gross_margin": "Gross margin (TRY)",
    "gross_margin_pct": "Gross margin %",
    "revenue": "Revenue (TRY)",
    "cost": "Cost (TRY)",
    "cogs": "COGS (TRY)",
    "avg_inventory_value": "Avg inventory (TRY)",
    "value": "Value (TRY)",
    "inventory_sold_qty": "Sold per inventory",
    "transaction_units": "Units per transactions",
    "rule_id": "Rule",
}
MONEY_COLUMNS = {"revenue", "cost", "gross_margin", "cogs", "avg_inventory_value", "value"}


def _table(frame: pd.DataFrame, columns: list[str] | None = None) -> str:
    """Render a table for people: readable headers, TRY without decimals, percentages.

    Text columns are left-aligned and numbers right-aligned.

    Args:
        frame (pd.DataFrame): The table to render.
        columns (list[str] | None): Columns to show, in order; None shows all.

    Returns:
        str: HTML ``<table>`` markup with every value escaped.
    """
    shown = frame[columns] if columns else frame
    classes = [_cell_class(column) for column in shown.columns]
    header = "".join(
        f'<th class="{css}">{escape(COLUMN_LABELS.get(c, c.replace("_", " ").capitalize()))}</th>'
        for c, css in zip(shown.columns, classes, strict=True)
    )
    formatters = [_formatter(shown[column]) for column in shown.columns]
    names = list(shown.columns)
    body = "".join(
        "<tr>"
        + "".join(
            f'<td class="{css}">{_cell_html(name, value, fmt)}</td>'
            for name, value, fmt, css in zip(names, row, formatters, classes, strict=True)
        )
        + "</tr>"
        for row in shown.itertuples(index=False)
    )
    return f'<table class="data"><thead><tr>{header}</tr></thead><tbody>{body}</tbody></table>'


def _cell_html(column: str, value: object, formatter: Callable[[object], str]) -> str:
    """Render one cell, as a status badge for severity and as escaped text otherwise.

    Args:
        column (str): Column name, used to pick the badge treatment.
        value (object): The cell's value.
        formatter (Callable[[object], str]): Formatter for this column's values.

    Returns:
        str: HTML for the cell's contents, with any text escaped.
    """
    if column == "severity":
        return _severity_badge(str(value))
    return escape(formatter(value))


TEXT_COLUMNS = {
    "store_id",
    "store_name",
    "region",
    "article_id",
    "article_name",
    "category",
    "table",
    "severity",
    "rule_id",
    "month",
}
LONG_TEXT_COLUMNS = {"description"}


def _cell_class(column: str) -> str:
    """Choose the alignment class for a column.

    Args:
        column (str): Column name.

    Returns:
        str: ``"text-long"`` for prose, ``"text"`` for short text, ``"num"`` otherwise.
    """
    if column in LONG_TEXT_COLUMNS:
        return "text-long"
    return "text" if column in TEXT_COLUMNS else "num"


def _formatter(values: pd.Series) -> Callable[[object], str]:
    """Choose how to display one column's values.

    Args:
        values (pd.Series): The column, named after the KPI field it holds.

    Returns:
        Callable[[object], str]: Function turning one value into display text.
    """
    column = str(values.name)
    if column in MONEY_COLUMNS:
        return lambda v: _money(float(v))  # type: ignore[arg-type]
    if column.endswith("_pct"):
        return lambda v: _percent(float(v))  # type: ignore[arg-type]
    if column == "turnover":
        return lambda v: f"{float(v):.2f}"  # type: ignore[arg-type]
    if pd.api.types.is_datetime64_any_dtype(values):
        return lambda v: f"{v:%Y-%m-%d}"
    if pd.api.types.is_integer_dtype(values):
        return lambda v: f"{v:,}"
    return str


def _money(value: float) -> str:
    """Format an amount in TRY with thousands separators and no decimals.

    Args:
        value (float): Amount in TRY.

    Returns:
        str: E.g. ``"57,423,657"``.
    """
    return f"{value:,.0f}"


def _percent(value: float) -> str:
    """Format a fraction as a percentage with one decimal.

    Args:
        value (float): A fraction, e.g. 0.1794.

    Returns:
        str: E.g. ``"17.9%"``.
    """
    return f"{value:.1%}"
