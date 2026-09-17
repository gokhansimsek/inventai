import pandas as pd
import pytest

from retail_analytics.kpis.sales import enrich_sales, summarise_sales

ARTICLES = pd.DataFrame(
    {
        "article_id": ["A1", "A2"],
        "article_name": ["Rice", "Kite"],
        "category": ["Food", "Toys"],
        "sub_category": ["Grains", "Outdoor"],
        "brand": ["X", "Y"],
        "purchase_price": [60.0, 5.0],
    }
)
STORES = pd.DataFrame(
    {"store_id": ["S-1", "S-2"], "store_name": ["One", "Two"], "region": ["North", "South"]}
)


def _sales() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "transaction_id": ["T1", "T2", "T3"],
            "date": pd.to_datetime(["2024-03-05", "2024-03-06", "2024-03-12"]),
            "store_id": ["S-1", "S-1", "S-2"],
            "article_id": ["A1", "A2", "A1"],
            "quantity": [2, 1, 3],
            "selling_price": [100.0, 50.0, 10.0],
            "discount_pct": [10.0, 0.0, 50.0],
        }
    )


def test_each_sale_line_gets_revenue_after_discount_cost_and_its_attributes() -> None:
    enriched = enrich_sales(_sales(), ARTICLES, STORES)

    assert enriched["revenue"].tolist() == [180.0, 50.0, 15.0]
    assert enriched["cost"].tolist() == [120.0, 5.0, 180.0]
    assert enriched["category"].tolist() == ["Food", "Toys", "Food"]
    assert enriched["region"].tolist() == ["North", "North", "South"]
    assert enriched["week"].tolist() == [pd.Timestamp("2024-03-04")] * 2 + [
        pd.Timestamp("2024-03-11")
    ]


def test_revenue_and_gross_margin_are_summarised_per_store() -> None:
    summary = summarise_sales(enrich_sales(_sales(), ARTICLES, STORES), ["store_id"])

    s1, s2 = summary.to_dict("records")
    assert s1 | {"gross_margin_pct": 0} == {
        "store_id": "S-1",
        "transactions": 2,
        "units": 3,
        "revenue": 230.0,
        "cost": 125.0,
        "gross_margin": 105.0,
        "gross_margin_pct": 0,
    }
    assert s1["gross_margin_pct"] == pytest.approx(105 / 230)
    assert (s2["revenue"], s2["cost"], s2["gross_margin"]) == (15.0, 180.0, -165.0)
    assert s2["gross_margin_pct"] == pytest.approx(-11.0)


def test_summary_without_dimensions_is_one_total_row() -> None:
    summary = summarise_sales(enrich_sales(_sales(), ARTICLES, STORES), [])

    assert summary[["transactions", "units", "revenue", "cost"]].to_dict("records") == [
        {"transactions": 3, "units": 6, "revenue": 245.0, "cost": 305.0}
    ]
