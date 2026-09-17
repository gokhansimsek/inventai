import pandas as pd

from retail_analytics.kpis.revenue import revenue_by


def test_revenue_is_quantity_times_price_after_discount_summed_per_store() -> None:
    sales = pd.DataFrame(
        {
            "store_id": ["S-001", "S-001", "S-002"],
            "quantity": [2, 1, 3],
            "selling_price": [100.0, 50.0, 10.0],
            "discount_pct": [10.0, 0.0, 50.0],
        }
    )

    result = revenue_by(sales, ["store_id"])

    assert result.to_dict("records") == [
        {"store_id": "S-001", "revenue": 230.0},
        {"store_id": "S-002", "revenue": 15.0},
    ]
