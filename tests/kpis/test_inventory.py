from datetime import date

import pandas as pd
import pytest

from retail_analytics.kpis.inventory import compare_sales_with_inventory, inventory_turnover

ARTICLES = pd.DataFrame({"article_id": ["A", "B"], "purchase_price": [10.0, 2.0]})


def _inventory() -> pd.DataFrame:
    # S-1 week of 03-04: A avg stock 8 x 10 = 80, B avg 40 x 2 = 80 -> value 160; COGS 40 + 40
    # S-1 week of 03-11: A avg stock 15 x 10 = 150                  -> value 150; COGS 100
    # S-2 week of 03-04: A avg stock 5 x 10 = 50                    -> value 50;  COGS 0
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-03-04", "2024-03-04", "2024-03-11", "2024-03-04"]),
            "store_id": ["S-1", "S-1", "S-1", "S-2"],
            "article_id": ["A", "B", "A", "A"],
            "opening_stock": [10, 50, 20, 5],
            "received_qty": [0, 0, 0, 0],
            "sold_qty": [4, 20, 10, 0],
            "closing_stock": [6, 30, 10, 5],
        }
    )


def test_turnover_is_cost_of_goods_sold_over_average_weekly_inventory_at_cost() -> None:
    result = inventory_turnover(_inventory(), ARTICLES, date_from=None, date_to=None)

    by_store = result.by_store.set_index("store_id")
    assert by_store.loc["S-1", "weeks"] == 2
    assert by_store.loc["S-1", "cogs"] == 180.0
    assert by_store.loc["S-1", "avg_inventory_value"] == 155.0
    assert by_store.loc["S-1", "turnover"] == pytest.approx(180 / 155)
    assert by_store.loc["S-2", "turnover"] == 0.0
    assert result.weeks == [pd.Timestamp("2024-03-04"), pd.Timestamp("2024-03-11")]


def test_only_weeks_entirely_inside_the_date_range_are_used() -> None:
    result = inventory_turnover(
        _inventory(), ARTICLES, date_from=date(2024, 3, 6), date_to=date(2024, 3, 17)
    )

    assert result.weeks == [pd.Timestamp("2024-03-11")]
    assert result.by_store.to_dict("records") == [
        {
            "store_id": "S-1",
            "weeks": 1,
            "cogs": 100.0,
            "avg_inventory_value": 150.0,
            "turnover": pytest.approx(100 / 150),
        }
    ]


def test_a_range_shorter_than_any_full_week_gives_no_turnover() -> None:
    result = inventory_turnover(
        _inventory(), ARTICLES, date_from=date(2024, 3, 5), date_to=date(2024, 3, 9)
    )

    assert result.weeks == []
    assert result.by_store.empty


def test_sales_are_compared_with_inventory_for_the_same_store_article_weeks() -> None:
    sales = pd.DataFrame(
        {
            "store_id": ["S-1", "S-1", "S-1", "S-1", "S-1"],
            "article_id": ["A", "A", "C", "B", "A"],
            "week": pd.to_datetime(
                ["2024-03-04", "2024-03-04", "2024-03-04", "2024-03-11", "2024-03-11"]
            ),
            "quantity": [3, 2, 9, 1, 10],
        }
    )
    weeks = [pd.Timestamp("2024-03-04"), pd.Timestamp("2024-03-11")]

    comparison = compare_sales_with_inventory(sales, _inventory(), weeks)

    assert comparison.to_dict("records") == [
        {
            "store_id": "S-1",
            "week": pd.Timestamp("2024-03-04"),
            "articles": 2,
            "inventory_sold_qty": 24,
            "transaction_units": 5,
            "difference": -19,
        },
        {
            "store_id": "S-1",
            "week": pd.Timestamp("2024-03-11"),
            "articles": 1,
            "inventory_sold_qty": 10,
            "transaction_units": 10,
            "difference": 0,
        },
        {
            "store_id": "S-2",
            "week": pd.Timestamp("2024-03-04"),
            "articles": 1,
            "inventory_sold_qty": 0,
            "transaction_units": 0,
            "difference": 0,
        },
    ]
