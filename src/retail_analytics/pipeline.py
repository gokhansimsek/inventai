"""The run, end to end: load -> validate -> filter -> compute KPIs -> write report."""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from retail_analytics.config import Settings
from retail_analytics.filters import filter_by_store, filter_sales
from retail_analytics.io.manifest import write_manifest
from retail_analytics.io.readers import load_raw_tables
from retail_analytics.kpis.articles import rank_articles
from retail_analytics.kpis.inventory import (
    TurnoverResult,
    compare_sales_with_inventory,
    inventory_turnover,
)
from retail_analytics.kpis.returns import summarise_possible_returns
from retail_analytics.kpis.sales import enrich_sales, summarise_sales
from retail_analytics.reporting.cube import build_facts
from retail_analytics.reporting.report import Report
from retail_analytics.reporting.writers import CsvWriter, HtmlWriter, Writer
from retail_analytics.validation.engine import (
    RowCounts,
    RuleOutcome,
    ValidationOutcome,
    validate,
)
from retail_analytics.validation.registry import default_rules

log = logging.getLogger(__name__)

STORE_COLUMNS = ["store_id", "store_name", "region"]


@dataclass(frozen=True)
class RunResult:
    output_dir: Path
    row_counts: dict[str, RowCounts]
    rule_outcomes: list[RuleOutcome]
    files_written: list[Path]


def run_pipeline(settings: Settings, writers: list[Writer] | None = None) -> RunResult:
    """Run the whole pipeline: load, validate, filter, compute KPIs, write the report.

    Args:
        settings (Settings): Input and output locations and the analysis filters.
        writers (list[Writer] | None): Output writers; None uses the CSV and HTML writers.

    Returns:
        RunResult: Output folder, per-table row counts, what each rule did, and every
            file written.

    Raises:
        InputDataError: If an input file is missing or structurally broken.
        ConfigError: If a filter names an unknown store or region.
    """
    started_at = datetime.now()
    raw = load_raw_tables(settings.data_dir)
    for table, frame in raw.items():
        log.info(
            "Loaded %s: %d rows",
            table,
            len(frame),
            extra={"stage": "load", "table": table, "rows": len(frame)},
        )

    rules = default_rules(pd.Timestamp(settings.as_of), settings.price_tolerance)
    outcome = validate(raw, rules)
    for rule in outcome.rule_outcomes:
        log.info(
            "Rule %s: fixed=%d rejected=%d flagged=%d",
            rule.rule_id,
            rule.fixed,
            rule.rejected,
            rule.flagged,
            extra={"stage": "validate", **asdict(rule)},
        )

    clean_sales = outcome.clean["transactions"]
    sales = filter_sales(clean_sales, outcome.clean["stores"], settings)
    log.info(
        "Selected %d of %d clean sales",
        len(sales),
        len(clean_sales),
        extra={"stage": "filter", "rows_in": len(clean_sales), "rows_out": len(sales)},
    )

    stores, articles = outcome.clean["stores"], outcome.clean["articles"]
    inventory = filter_by_store(outcome.clean["inventory"], stores, settings)
    turnover = inventory_turnover(inventory, articles, settings.date_from, settings.date_to)
    enriched = enrich_sales(sales, articles, stores)
    quarantined = _selected(outcome.rejected["transactions"], stores, settings)
    kpis = _compute_kpis(
        enriched, inventory, turnover, quarantined=quarantined, stores=stores, settings=settings
    )
    report = Report(
        generated_at=started_at,
        selection=_describe_selection(settings),
        has_sales=not sales.empty,
        kpis=kpis,
        turnover_weeks=turnover.weeks,
        top_n=settings.top_n,
        min_units_for_margin_pct=settings.min_units_for_margin_pct,
        data_quality=pd.DataFrame([asdict(r) for r in outcome.rule_outcomes]),
        row_counts=_row_counts_table(outcome),
        quarantine=outcome.rejected,
        issues=outcome.flagged,
        facts=build_facts(
            enriched,
            inventory,
            articles,
            stores,
            sales_vs_inventory=kpis["sales_vs_inventory"],
            quarantined_sales=quarantined,
        ),
    )
    log.info("Computed %d KPI tables", len(report.kpis), extra={"stage": "kpis"})

    files = [write_manifest(settings, outcome.row_counts, started_at)]
    for writer in writers or [CsvWriter(), HtmlWriter()]:
        files.extend(writer.write(report, settings.output_dir))
    log.info(
        "Wrote %d files to %s",
        len(files),
        settings.output_dir,
        extra={"stage": "write", "files": [str(f) for f in files]},
    )

    return RunResult(settings.output_dir, outcome.row_counts, outcome.rule_outcomes, files)


def _compute_kpis(
    enriched: pd.DataFrame,
    inventory: pd.DataFrame,
    turnover: TurnoverResult,
    *,
    quarantined: pd.DataFrame,
    stores: pd.DataFrame,
    settings: Settings,
) -> dict[str, pd.DataFrame]:
    """Compute every KPI table for the selected data.

    Args:
        enriched (pd.DataFrame): Clean sales inside the selection, with revenue, cost and
            the article and store attributes added.
        inventory (pd.DataFrame): Clean inventory for the selected stores.
        turnover (TurnoverResult): Inventory turnover for the selection.
        quarantined (pd.DataFrame): Quarantined transactions inside the selection.
        stores (pd.DataFrame): Validated store master data.
        settings (Settings): Run settings: selection, date range and ranking options.

    Returns:
        dict[str, pd.DataFrame]: KPI tables keyed by the file name they are written to.
    """
    return {
        "summary": summarise_sales(enriched, []),
        "sales_by_store": summarise_sales(enriched, STORE_COLUMNS),
        "sales_by_category": summarise_sales(enriched, ["category"]),
        "sales_by_month": summarise_sales(enriched, ["month"]).sort_values("month"),
        "sales_by_week": summarise_sales(enriched, ["week"]).sort_values("week"),
        "sales_by_day": summarise_sales(enriched, ["day"]).sort_values("day"),
        **rank_articles(enriched, settings.top_n, settings.min_units_for_margin_pct),
        "inventory_turnover_by_store": stores[STORE_COLUMNS]
        .merge(turnover.by_store, on="store_id")
        .sort_values("turnover", ascending=False),
        "sales_vs_inventory": compare_sales_with_inventory(enriched, inventory, turnover.weeks),
        "possible_returns": summarise_possible_returns(quarantined),
    }


def _selected(
    quarantined_sales: pd.DataFrame, stores: pd.DataFrame, settings: Settings
) -> pd.DataFrame:
    """Narrow quarantined sales to the selection, so possible returns match revenue.

    Args:
        quarantined_sales (pd.DataFrame): Every quarantined transaction; empty with no
            columns when nothing was quarantined.
        stores (pd.DataFrame): Validated store master data.
        settings (Settings): Run settings with the selection.

    Returns:
        pd.DataFrame: Quarantined rows with a valid date, for known, selected stores
            inside the date range.
    """
    if quarantined_sales.empty:
        return quarantined_sales
    dates = pd.to_datetime(quarantined_sales["date"], errors="coerce")
    dated = quarantined_sales[dates.notna()].assign(date=dates[dates.notna()])
    return filter_sales(dated, stores, settings)


def _describe_selection(settings: Settings) -> str:
    """Describe the store, region and date selection in words.

    Args:
        settings (Settings): Run settings.

    Returns:
        str: E.g. ``"Stores: all · Regions: Marmara · Dates: 2024-03-01 to 2024-03-15"``.
    """
    stores = ", ".join(settings.stores) or "all"
    regions = ", ".join(settings.regions) or "all"
    start = settings.date_from.isoformat() if settings.date_from else "start of data"
    end = settings.date_to.isoformat() if settings.date_to else "end of data"
    return f"Stores: {stores} · Regions: {regions} · Dates: {start} to {end}"


def _row_counts_table(outcome: ValidationOutcome) -> pd.DataFrame:
    """Flatten per-table row counts into one table for the report.

    Args:
        outcome (ValidationOutcome): The result of validating every table.

    Returns:
        pd.DataFrame: One row per table with ``raw``, ``clean`` and ``rejected`` counts.
    """
    return pd.DataFrame([{"table": t, **asdict(c)} for t, c in outcome.row_counts.items()])
