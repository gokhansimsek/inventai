import pandas as pd

from retail_analytics.kpis.articles import rank_articles


def _enriched() -> pd.DataFrame:
    # Article totals: A units 10, revenue 1000, margin 100 (10%)
    #                 B units 5,  revenue 500,  margin 300 (60%)
    #                 C units 1,  revenue 50,   margin 40  (80%), too few units for % lists
    #                 D units 4,  revenue 300,  margin -30 (-10%)
    return pd.DataFrame(
        {
            "transaction_id": ["T1", "T2", "T3", "T4", "T5"],
            "article_id": ["A", "A", "B", "C", "D"],
            "article_name": ["a", "a", "b", "c", "d"],
            "category": ["X", "X", "X", "Y", "Y"],
            "quantity": [6, 4, 5, 1, 4],
            "revenue": [600.0, 400.0, 500.0, 50.0, 300.0],
            "cost": [540.0, 360.0, 200.0, 10.0, 330.0],
        }
    )


def _ids(rankings: dict[str, pd.DataFrame], name: str) -> list[str]:
    return rankings[name]["article_id"].tolist()


def test_articles_are_ranked_top_and_bottom_by_revenue_and_margin() -> None:
    rankings = rank_articles(_enriched(), n=2, min_units_for_margin_pct=3)

    assert _ids(rankings, "top_by_revenue") == ["A", "B"]
    assert _ids(rankings, "bottom_by_revenue") == ["C", "D"]
    assert _ids(rankings, "top_by_margin_try") == ["B", "A"]
    assert _ids(rankings, "bottom_by_margin_try") == ["D", "C"]
    assert _ids(rankings, "top_by_margin_pct") == ["B", "A"]
    assert _ids(rankings, "bottom_by_margin_pct") == ["D", "A"]


def test_ranked_rows_carry_rank_and_article_totals() -> None:
    top = rank_articles(_enriched(), n=2, min_units_for_margin_pct=3)["top_by_revenue"]

    assert top.iloc[0][["rank", "article_id", "units", "revenue", "gross_margin"]].to_dict() == {
        "rank": 1,
        "article_id": "A",
        "units": 10,
        "revenue": 1000.0,
        "gross_margin": 100.0,
    }
    assert top.iloc[0]["gross_margin_pct"] == 0.1
