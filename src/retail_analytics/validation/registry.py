"""The ordered list of rules the pipeline runs. Order matters: types first."""

from retail_analytics.validation.base import Rule
from retail_analytics.validation.schemas import CoerceToSchema
from retail_analytics.validation.transaction_rules import (
    ConvertKurusToLira,
    RejectNonPositiveQuantity,
)


def default_rules() -> list[Rule]:
    """Build the rules the pipeline runs.

    Returns:
        list[Rule]: Rules in execution order; type coercion comes first.
    """
    return [
        CoerceToSchema("stores"),
        CoerceToSchema("articles"),
        CoerceToSchema("transactions"),
        CoerceToSchema("inventory"),
        ConvertKurusToLira(),
        RejectNonPositiveQuantity(),
    ]
