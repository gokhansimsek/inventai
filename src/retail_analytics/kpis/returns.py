"""Possible returns: sales rows quarantined for a negative quantity."""

import pandas as pd

RETURNS_RULE_ID = "TRANSACTIONS_QUANTITY_NOT_POSITIVE"


def summarise_possible_returns(quarantined_sales: pd.DataFrame) -> pd.DataFrame:
    """Total the rows quarantined for a non-positive quantity.

    They are excluded from revenue because nothing links them to an original sale,
    but their value shows the business what may be returns.

    Args:
        quarantined_sales (pd.DataFrame): Quarantined transactions with ``rule_id``,
            ``quantity``, ``selling_price`` (TRY) and ``discount_pct``.

    Returns:
        pd.DataFrame: One row with ``transactions``, ``units`` (absolute) and ``value``
            (absolute quantity x price after discount, in TRY).
    """
    if quarantined_sales.empty:
        return pd.DataFrame([{"transactions": 0, "units": 0, "value": 0.0}])
    rows = quarantined_sales[quarantined_sales["rule_id"] == RETURNS_RULE_ID]
    units = rows["quantity"].abs()
    value = units * rows["selling_price"] * (1 - rows["discount_pct"] / 100)
    return pd.DataFrame(
        [{"transactions": len(rows), "units": int(units.sum()), "value": float(value.sum())}]
    )
