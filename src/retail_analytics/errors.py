"""Errors that stop a run.

Row-level problems never raise: they are quarantined or flagged. These errors
are for problems that make every number untrustworthy (a missing file, a
missing column) or a request that cannot be served (bad config or filter).
"""


class PipelineError(Exception):
    """Base class for errors that abort a run with a clear message."""


class InputDataError(PipelineError):
    """An input file is missing or structurally broken."""


class ConfigError(PipelineError):
    """The configuration or a CLI filter is invalid."""
