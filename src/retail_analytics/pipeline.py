"""The run, end to end: load -> validate -> compute KPIs -> write report."""

import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from retail_analytics.config import Settings
from retail_analytics.filters import filter_sales
from retail_analytics.io.manifest import write_manifest
from retail_analytics.io.readers import load_raw_tables
from retail_analytics.kpis.revenue import revenue_by
from retail_analytics.reporting.report import Report
from retail_analytics.reporting.writers import CsvWriter, HtmlWriter, Writer
from retail_analytics.validation.engine import RowCounts, RuleOutcome, ValidationOutcome, validate
from retail_analytics.validation.registry import default_rules

log = logging.getLogger(__name__)


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
    report = Report(
        generated_at=datetime.now(),
        kpis={"revenue_by_store": revenue_by(sales, ["store_id"])},
        data_quality=pd.DataFrame([asdict(r) for r in outcome.rule_outcomes]),
        row_counts=_row_counts_table(outcome),
        quarantine=outcome.rejected,
        issues=outcome.flagged,
    )

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


def _row_counts_table(outcome: ValidationOutcome) -> pd.DataFrame:
    """Flatten per-table row counts into one table for the report.

    Args:
        outcome (ValidationOutcome): The result of validating every table.

    Returns:
        pd.DataFrame: One row per table with ``raw``, ``clean`` and ``rejected`` counts.
    """
    return pd.DataFrame([{"table": t, **asdict(c)} for t, c in outcome.row_counts.items()])
