"""Rules that apply to any table, configured by table and column."""

from collections.abc import Mapping

import pandas as pd

from retail_analytics.validation.base import RuleResult, Severity


class RejectUnknownReference:
    """Quarantine rows whose key is missing from the table it refers to.

    Checks against the referenced table as validated so far, so rows pointing at a
    rejected master row are rejected too.
    """

    severity = Severity.REJECT

    def __init__(self, table: str, column: str, referenced_table: str) -> None:
        """Build the rule for one foreign-key column.

        Args:
            table (str): Table holding the reference, e.g. ``"transactions"``.
            column (str): Referencing column; the referenced table has a column of the
                same name.
            referenced_table (str): Table the column refers to, e.g. ``"stores"``.
        """
        self.table = table
        self.column = column
        self.referenced_table = referenced_table
        self.rule_id = f"{table.upper()}_{column.upper()}_UNKNOWN"
        self.description = f"Every {column} in {table} must exist in {referenced_table}."

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Quarantine rows whose reference is not found.

        Args:
            df (pd.DataFrame): The referencing table.
            tables (Mapping[str, pd.DataFrame]): Every table as validated so far; must
                contain the referenced table.

        Returns:
            RuleResult: Rows with a known reference, and rejected rows with a ``reason``.
        """
        known = tables[self.referenced_table][self.column]
        bad = ~df[self.column].isin(known)
        reason = (
            f"{self.column} '"
            + df.loc[bad, self.column].astype(str)
            + f"' not found in {self.referenced_table}"
        )
        return RuleResult(data=df[~bad], rejected=df[bad].assign(reason=reason))


class RejectExactCopies:
    """Quarantine rows that exactly repeat an earlier row, keeping the first.

    Runs on the raw text, before any other rule, so a copy is caught even when its
    values would fail later checks.
    """

    severity = Severity.REJECT

    def __init__(self, table: str) -> None:
        """Build the rule for one table.

        Args:
            table (str): Table to check.
        """
        self.table = table
        self.rule_id = f"{table.upper()}_EXACT_COPY"
        self.description = (
            f"A row in {table} identical in every column to an earlier row is a copy; "
            "the first is kept and the copies are quarantined."
        )

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Quarantine exact copies.

        Args:
            df (pd.DataFrame): The table to check.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

        Returns:
            RuleResult: First occurrences, and rejected copies with a ``reason``.
        """
        copy = df.duplicated(keep="first")
        return RuleResult(
            data=df[~copy], rejected=df[copy].assign(reason="exact copy of an earlier row")
        )


class RejectConflictingKeys:
    """Quarantine every row of a key that appears on rows with different values.

    Runs after the row-level checks: when only one version of a key is valid, the
    invalid versions have already been quarantined and the valid one is kept.
    When several valid versions remain, nothing says which is right, so all go.
    """

    severity = Severity.REJECT

    def __init__(self, table: str, key: list[str]) -> None:
        """Build the rule for one table's key.

        Args:
            table (str): Table to check.
            key (list[str]): Columns that identify a row, e.g. ``["transaction_id"]``.
        """
        self.table = table
        self.key = key
        self.rule_id = f"{table.upper()}_KEY_CONFLICT"
        self.description = (
            f"Each {'/'.join(key)} must identify one row in {table}. When several valid "
            "rows share it with different values, all of them are quarantined."
        )

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Quarantine rows whose key is shared by other rows.

        Args:
            df (pd.DataFrame): The table to check.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

        Returns:
            RuleResult: Rows with a unique key, and rejected rows with a ``reason``.
        """
        conflicting = df.duplicated(subset=self.key, keep=False)
        if not conflicting.any():
            return RuleResult(data=df)
        rows = df[conflicting]
        copies = rows.groupby(self.key)[self.key[0]].transform("size").astype(str)
        key_text = rows[self.key].astype(str).agg("/".join, axis=1)
        reason = (
            f"{'/'.join(self.key)} '"
            + key_text
            + "' appears on "
            + copies
            + " rows with different values"
        )
        return RuleResult(data=df[~conflicting], rejected=rows.assign(reason=reason))


MISSING_VALUE_SPELLINGS = frozenset({"", "N/A", "NA", "NULL", "NONE"})


class NormaliseMissingValues:
    """Turn the text spellings of "no value" into real nulls."""

    severity = Severity.FIX

    def __init__(self, table: str, column: str) -> None:
        """Build the rule for one column.

        Args:
            table (str): Table to fix.
            column (str): Column whose missing-value spellings become null.
        """
        self.table = table
        self.column = column
        self.rule_id = f"{table.upper()}_{column.upper()}_MISSING_SPELLINGS"
        self.description = (
            f"Blank, N/A, NA, NULL and NONE in {table}.{column} (any case) all mean "
            "'no value' and are stored as null."
        )

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Replace missing-value spellings with null.

        Args:
            df (pd.DataFrame): The table to fix.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

        Returns:
            RuleResult: All rows with nulls in place of the spellings; the fixed count is
                the number of values replaced.
        """
        is_missing = df[self.column].str.strip().str.upper().isin(MISSING_VALUE_SPELLINGS)
        out = df.copy()
        out[self.column] = out[self.column].mask(is_missing)
        return RuleResult(data=out, fixed_count=int(is_missing.sum()))


ISO_DATE = r"^\d{4}-\d{2}-\d{2}$"
DAY_FIRST_DATE = r"^\d{2}-\d{2}-\d{4}$"


class ParseDates:
    """Parse a text date column that mixes ISO and day-first formats.

    Day-first (DD-MM-YYYY) is assumed rather than month-first because, in the data,
    many such dates have a first part above 12 and none has a second part above 12.
    """

    severity = Severity.FIX

    def __init__(self, table: str, column: str) -> None:
        """Build the rule for one date column.

        Args:
            table (str): Table to fix.
            column (str): Text column holding dates.
        """
        self.table = table
        self.column = column
        self.rule_id = f"{table.upper()}_{column.upper()}_FORMAT"
        self.description = (
            f"{table}.{column} accepts YYYY-MM-DD and DD-MM-YYYY; day-first dates are "
            "converted. Other formats and impossible dates are quarantined."
        )

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Convert the column to timestamps, quarantining values that are not dates.

        Args:
            df (pd.DataFrame): The table with a text date column.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

        Returns:
            RuleResult: Rows with a parsed date, rejected rows with a ``reason``; the
                fixed count is the number of day-first dates converted.
        """
        text = df[self.column].astype(str)
        is_iso = text.str.match(ISO_DATE)
        is_day_first = text.str.match(DAY_FIRST_DATE)
        parsed = pd.to_datetime(text.where(is_iso), format="%Y-%m-%d", errors="coerce").fillna(
            pd.to_datetime(text.where(is_day_first), format="%d-%m-%Y", errors="coerce")
        )

        bad_format = ~(is_iso | is_day_first)
        bad_calendar = ~bad_format & parsed.isna()
        reason = pd.Series(pd.NA, index=df.index, dtype="string")
        reason[bad_format] = (
            f"{self.column} '" + text[bad_format] + "' is not YYYY-MM-DD or DD-MM-YYYY"
        )
        reason[bad_calendar] = (
            f"{self.column} '" + text[bad_calendar] + "' is not a real calendar date"
        )

        bad = bad_format | bad_calendar
        out = df[~bad].assign(**{self.column: parsed[~bad]})
        return RuleResult(
            data=out,
            rejected=df[bad].assign(reason=reason[bad]),
            fixed_count=int((is_day_first & ~bad).sum()),
        )


class RejectOutOfRange:
    """Quarantine rows whose numeric value falls outside a range."""

    severity = Severity.REJECT

    def __init__(
        self,
        table: str,
        column: str,
        minimum: float | None = None,
        maximum: float | None = None,
        include_minimum: bool = True,
    ) -> None:
        """Build the rule for one numeric column.

        Args:
            table (str): Table to check.
            column (str): Numeric column to check.
            minimum (float | None): Lowest allowed value; None for no lower bound.
            maximum (float | None): Highest allowed value (inclusive); None for no upper
                bound.
            include_minimum (bool): Whether ``minimum`` itself is allowed.
        """
        self.table = table
        self.column = column
        self.minimum = minimum
        self.maximum = maximum
        self.include_minimum = include_minimum
        self.rule_id = f"{table.upper()}_{column.upper()}_RANGE"
        self.description = f"{table}.{column} {self._requirement()}."

    def _requirement(self) -> str:
        """Describe the allowed range in words.

        Returns:
            str: E.g. ``"must be between 0 and 100"`` or ``"must be greater than 0"``.
        """
        if self.minimum is not None and self.maximum is not None:
            return f"must be between {self.minimum:g} and {self.maximum:g}"
        if self.minimum is not None:
            comparison = "at least" if self.include_minimum else "greater than"
            return f"must be {comparison} {self.minimum:g}"
        return f"must be at most {self.maximum:g}"

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Quarantine rows outside the range.

        Args:
            df (pd.DataFrame): The table with a numeric column.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

        Returns:
            RuleResult: Rows within the range, and rejected rows with a ``reason``.
        """
        values = df[self.column]
        ok = pd.Series(True, index=df.index)
        if self.minimum is not None:
            ok &= values >= self.minimum if self.include_minimum else values > self.minimum
        if self.maximum is not None:
            ok &= values <= self.maximum
        reason = f"{self.column} {self._requirement()}, got " + values[~ok].astype(str)
        return RuleResult(data=df[ok], rejected=df[~ok].assign(reason=reason))


class RejectUnexpectedValues:
    """Quarantine rows whose value is not in an allowed set."""

    severity = Severity.REJECT

    def __init__(self, table: str, column: str, allowed: set[str]) -> None:
        """Build the rule for one categorical column.

        Args:
            table (str): Table to check.
            column (str): Column to check.
            allowed (set[str]): Every accepted value.
        """
        self.table = table
        self.column = column
        self.allowed = allowed
        self.rule_id = f"{table.upper()}_{column.upper()}_VALUE"
        self.description = f"{table}.{column} must be one of: {', '.join(sorted(allowed))}."

    def apply(self, df: pd.DataFrame, tables: Mapping[str, pd.DataFrame]) -> RuleResult:
        """Quarantine rows with a value outside the allowed set.

        Args:
            df (pd.DataFrame): The table to check.
            tables (Mapping[str, pd.DataFrame]): Other tables; unused.

        Returns:
            RuleResult: Rows with allowed values, and rejected rows with a ``reason``.
        """
        ok = df[self.column].isin(self.allowed)
        reason = (
            f"{self.column} '"
            + df.loc[~ok, self.column].astype(str)
            + f"' is not one of: {', '.join(sorted(self.allowed))}"
        )
        return RuleResult(data=df[ok], rejected=df[~ok].assign(reason=reason))
