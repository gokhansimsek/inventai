"""Run validation rules over the raw tables and collect everything they found."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from retail_analytics.validation.base import Rule, Severity


@dataclass(frozen=True)
class RowCounts:
    raw: int
    clean: int
    rejected: int


@dataclass(frozen=True)
class RuleOutcome:
    rule_id: str
    table: str
    severity: Severity
    description: str
    fixed: int
    rejected: int
    flagged: int


@dataclass(frozen=True)
class ValidationOutcome:
    clean: dict[str, pd.DataFrame]
    rejected: dict[str, pd.DataFrame]
    flagged: dict[str, pd.DataFrame]
    rule_outcomes: list[RuleOutcome]
    row_counts: dict[str, RowCounts]


def validate(raw: Mapping[str, pd.DataFrame], rules: Sequence[Rule]) -> ValidationOutcome:
    """Apply rules in order and collect what they found for every table.

    Each rule receives its table as left by the previous rule for that table, plus
    every table in its current state. Rules for master data (stores, articles) must
    run before the rules that check references to them, so rows pointing at a
    rejected master row are rejected too.

    Args:
        raw (Mapping[str, pd.DataFrame]): Raw tables keyed by table name.
        rules (Sequence[Rule]): Rules to apply, in execution order.

    Returns:
        ValidationOutcome: Clean, rejected and flagged rows per table, what each rule
            did, and raw/clean/rejected row counts.
    """
    clean = dict(raw)
    rejected: dict[str, list[pd.DataFrame]] = {table: [] for table in raw}
    flagged: dict[str, list[pd.DataFrame]] = {table: [] for table in raw}
    outcomes = []

    for rule in rules:
        result = rule.apply(clean[rule.table], clean)
        clean[rule.table] = result.data
        rejected[rule.table].append(result.rejected.assign(rule_id=rule.rule_id))
        flagged[rule.table].append(result.flagged.assign(rule_id=rule.rule_id))
        outcomes.append(
            RuleOutcome(
                rule_id=rule.rule_id,
                table=rule.table,
                severity=rule.severity,
                description=rule.description,
                fixed=result.fixed_count,
                rejected=len(result.rejected),
                flagged=len(result.flagged),
            )
        )

    rejected_tables = {t: _concat(frames) for t, frames in rejected.items()}
    return ValidationOutcome(
        clean=clean,
        rejected=rejected_tables,
        flagged={t: _concat(frames) for t, frames in flagged.items()},
        rule_outcomes=outcomes,
        row_counts={t: RowCounts(len(raw[t]), len(clean[t]), len(rejected_tables[t])) for t in raw},
    )


def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    """Stack a table's result frames from several rules.

    Args:
        frames (list[pd.DataFrame]): Frames produced by the rules; empty ones are skipped.

    Returns:
        pd.DataFrame: The non-empty frames stacked with a fresh index, or an empty
            DataFrame if all were empty.
    """
    non_empty = [f for f in frames if len(f)]
    return pd.concat(non_empty, ignore_index=True) if non_empty else pd.DataFrame()
