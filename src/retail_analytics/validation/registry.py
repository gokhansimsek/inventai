"""The ordered list of rules the pipeline runs.

Order matters:
1. Master data (stores, articles) before the tables that reference it, so rows
   pointing at a rejected master row are rejected too.
2. Within a table: exact copies on the raw text, then missing-value spellings,
   then types, then value fixes and row-level checks, then key conflicts (so an
   invalid version of a row is already gone), then references, then flags.
"""

import pandas as pd

from retail_analytics.validation.base import Rule
from retail_analytics.validation.flag_rules import (
    FlagCostAboveRecommendedPrice,
    FlagFutureDates,
    FlagInventoryImbalance,
    FlagPriceFarFromRecommended,
)
from retail_analytics.validation.generic_rules import (
    NormaliseMissingValues,
    ParseDates,
    RejectConflictingKeys,
    RejectExactCopies,
    RejectOutOfRange,
    RejectUnexpectedValues,
    RejectUnknownReference,
)
from retail_analytics.validation.schemas import CoerceToSchema
from retail_analytics.validation.transaction_rules import (
    ConvertKurusToLira,
    InferFutureDatesFromIdOrder,
    RejectNonPositiveQuantity,
)

STORE_TYPES = {"Hypermarket", "Supermarket", "Express"}
CURRENCIES = {"TRY", "KRS"}
STOCK_COLUMNS = ("opening_stock", "received_qty", "sold_qty", "closing_stock")


def default_rules(as_of: pd.Timestamp, price_tolerance: float) -> list[Rule]:
    """Build the rules the pipeline runs.

    Args:
        as_of (pd.Timestamp): Run date; later dates are treated as impossible.
        price_tolerance (float): Relative deviation from the recommended price beyond
            which a sale is flagged as a price outlier.

    Returns:
        list[Rule]: Rules in execution order.
    """
    return [
        *_store_rules(as_of),
        *_article_rules(),
        *_transaction_rules(as_of, price_tolerance),
        *_inventory_rules(),
    ]


def _store_rules(as_of: pd.Timestamp) -> list[Rule]:
    """Build the rules for stores.

    Args:
        as_of (pd.Timestamp): Run date for the future opening date check.

    Returns:
        list[Rule]: Store rules in execution order.
    """
    return [
        RejectExactCopies("stores"),
        CoerceToSchema("stores"),
        ParseDates("stores", "opening_date"),
        RejectOutOfRange("stores", "area_sqft", minimum=0, include_minimum=False),
        RejectUnexpectedValues("stores", "store_type", STORE_TYPES),
        RejectConflictingKeys("stores", ["store_id"]),
        FlagFutureDates("stores", "opening_date", as_of),
    ]


def _article_rules() -> list[Rule]:
    """Build the rules for articles.

    Returns:
        list[Rule]: Article rules in execution order.
    """
    return [
        RejectExactCopies("articles"),
        CoerceToSchema("articles"),
        RejectOutOfRange("articles", "purchase_price", minimum=0, include_minimum=False),
        RejectOutOfRange("articles", "recommended_selling_price", minimum=0, include_minimum=False),
        RejectConflictingKeys("articles", ["article_id"]),
        FlagCostAboveRecommendedPrice(),
    ]


def _transaction_rules(as_of: pd.Timestamp, price_tolerance: float) -> list[Rule]:
    """Build the rules for transactions.

    Args:
        as_of (pd.Timestamp): Run date for the future date check.
        price_tolerance (float): Relative deviation that flags a price outlier.

    Returns:
        list[Rule]: Transaction rules in execution order.
    """
    return [
        RejectExactCopies("transactions"),
        NormaliseMissingValues("transactions", "customer_id"),
        CoerceToSchema("transactions"),
        ParseDates("transactions", "date"),
        InferFutureDatesFromIdOrder(as_of),
        RejectUnexpectedValues("transactions", "currency", CURRENCIES),
        ConvertKurusToLira(),
        RejectNonPositiveQuantity(),
        RejectOutOfRange("transactions", "selling_price", minimum=0, include_minimum=False),
        RejectOutOfRange("transactions", "discount_pct", minimum=0, maximum=100),
        RejectConflictingKeys("transactions", ["transaction_id"]),
        RejectUnknownReference("transactions", "store_id", "stores"),
        RejectUnknownReference("transactions", "article_id", "articles"),
        FlagPriceFarFromRecommended(price_tolerance),
    ]


def _inventory_rules() -> list[Rule]:
    """Build the rules for inventory.

    Returns:
        list[Rule]: Inventory rules in execution order.
    """
    return [
        RejectExactCopies("inventory"),
        CoerceToSchema("inventory"),
        ParseDates("inventory", "date"),
        *(RejectOutOfRange("inventory", column, minimum=0) for column in STOCK_COLUMNS),
        RejectConflictingKeys("inventory", ["date", "store_id", "article_id"]),
        RejectUnknownReference("inventory", "store_id", "stores"),
        RejectUnknownReference("inventory", "article_id", "articles"),
        FlagInventoryImbalance(),
    ]
