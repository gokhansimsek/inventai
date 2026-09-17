import pandas as pd

from retail_analytics.validation.flag_rules import (
    FlagCostAboveRecommendedPrice,
    FlagFutureDates,
    FlagInventoryImbalance,
    FlagPriceFarFromRecommended,
)


def test_inventory_rows_that_do_not_balance_are_flagged_and_kept() -> None:
    inventory = pd.DataFrame(
        {
            "store_id": ["S-1", "S-2"],
            "opening_stock": [10, 10],
            "received_qty": [5, 5],
            "sold_qty": [3, 3],
            "closing_stock": [12, 14],
        }
    )

    result = FlagInventoryImbalance().apply(inventory, {})

    assert len(result.data) == 2
    assert result.flagged[["store_id", "reason"]].to_dict("records") == [
        {"store_id": "S-2", "reason": "opening 10 + received 5 - sold 3 = 12, but closing is 14"}
    ]


def test_articles_costing_more_than_their_recommended_price_are_flagged() -> None:
    articles = pd.DataFrame(
        {
            "article_id": ["A1", "A2"],
            "purchase_price": [80.0, 120.0],
            "recommended_selling_price": [100.0, 100.0],
        }
    )

    result = FlagCostAboveRecommendedPrice().apply(articles, {})

    assert len(result.data) == 2
    assert result.flagged[["article_id", "reason"]].to_dict("records") == [
        {
            "article_id": "A2",
            "reason": "purchase_price 120.00 is above recommended_selling_price 100.00",
        }
    ]


def test_dates_after_the_run_date_are_flagged_and_kept() -> None:
    stores = pd.DataFrame(
        {
            "store_id": ["S-1", "S-2"],
            "opening_date": pd.to_datetime(["2020-01-01", "2027-03-15"]),
        }
    )

    result = FlagFutureDates("stores", "opening_date", as_of=pd.Timestamp("2026-09-17")).apply(
        stores, {}
    )

    assert len(result.data) == 2
    assert result.flagged[["store_id", "reason"]].to_dict("records") == [
        {"store_id": "S-2", "reason": "opening_date 2027-03-15 is after the run date 2026-09-17"}
    ]


def test_selling_prices_far_from_the_recommended_price_are_flagged() -> None:
    articles = pd.DataFrame({"article_id": ["A1"], "recommended_selling_price": [100.0]})
    sales = pd.DataFrame(
        {
            "transaction_id": ["T1", "T2", "T3"],
            "article_id": ["A1", "A1", "A1"],
            "selling_price": [104.0, 40.0, 250.0],
        }
    )

    result = FlagPriceFarFromRecommended(tolerance=0.5).apply(sales, {"articles": articles})

    assert len(result.data) == 3
    assert result.flagged[["transaction_id", "reason"]].to_dict("records") == [
        {"transaction_id": "T2", "reason": "selling_price 40.00 is 60% below recommended 100.00"},
        {"transaction_id": "T3", "reason": "selling_price 250.00 is 150% above recommended 100.00"},
    ]
