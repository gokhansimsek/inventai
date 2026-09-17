import pandas as pd

from retail_analytics.kpis.returns import summarise_possible_returns


def test_possible_returns_total_the_negative_quantity_rows_at_their_absolute_value() -> None:
    quarantine = pd.DataFrame(
        {
            "rule_id": [
                "TRANSACTIONS_QUANTITY_NOT_POSITIVE",
                "TRANSACTIONS_QUANTITY_NOT_POSITIVE",
                "TRANSACTIONS_STORE_ID_UNKNOWN",
            ],
            "quantity": [-2, -1, 4],
            "selling_price": [100.0, 50.0, 10.0],
            "discount_pct": [10.0, 0.0, 0.0],
        }
    )

    summary = summarise_possible_returns(quarantine)

    assert summary.to_dict("records") == [{"transactions": 2, "units": 3, "value": 230.0}]
