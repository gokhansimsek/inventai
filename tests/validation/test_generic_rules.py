import pandas as pd

from retail_analytics.validation.generic_rules import (
    NormaliseMissingValues,
    ParseDates,
    RejectConflictingKeys,
    RejectExactCopies,
    RejectOutOfRange,
    RejectUnexpectedValues,
)


def test_exact_copies_are_quarantined_and_the_first_copy_is_kept() -> None:
    sales = pd.DataFrame({"transaction_id": ["T1", "T1", "T2"], "quantity": ["2", "2", "1"]})

    result = RejectExactCopies("transactions").apply(sales, {})

    assert result.data["transaction_id"].tolist() == ["T1", "T2"]
    assert result.rejected.to_dict("records") == [
        {"transaction_id": "T1", "quantity": "2", "reason": "exact copy of an earlier row"}
    ]


def test_rows_sharing_a_key_with_different_values_are_all_quarantined() -> None:
    sales = pd.DataFrame({"transaction_id": ["T1", "T1", "T2"], "quantity": ["2", "5", "1"]})

    result = RejectConflictingKeys("transactions", ["transaction_id"]).apply(sales, {})

    assert result.data["transaction_id"].tolist() == ["T2"]
    assert result.rejected["quantity"].tolist() == ["2", "5"]
    assert (
        result.rejected["reason"].tolist()
        == ["transaction_id 'T1' appears on 2 rows with different values"] * 2
    )


def test_missing_value_spellings_become_null() -> None:
    sales = pd.DataFrame({"customer_id": ["CUST-1", "", "N/A", "NULL", "NA", "n/a"]})

    result = NormaliseMissingValues("transactions", "customer_id").apply(sales, {})

    assert result.data["customer_id"].isna().tolist() == [False, True, True, True, True, True]
    assert result.data["customer_id"].iloc[0] == "CUST-1"
    assert result.fixed_count == 5


def test_iso_and_day_first_dates_parse_and_anything_else_is_quarantined() -> None:
    sales = pd.DataFrame(
        {
            "transaction_id": ["T1", "T2", "T3", "T4"],
            "date": ["2024-03-05", "25-03-2024", "03/25/2024", "2024-02-30"],
        }
    )

    result = ParseDates("transactions", "date").apply(sales, {})

    assert result.data["date"].tolist() == [pd.Timestamp("2024-03-05"), pd.Timestamp("2024-03-25")]
    assert result.fixed_count == 1
    assert result.rejected[["transaction_id", "reason"]].to_dict("records") == [
        {"transaction_id": "T3", "reason": "date '03/25/2024' is not YYYY-MM-DD or DD-MM-YYYY"},
        {"transaction_id": "T4", "reason": "date '2024-02-30' is not a real calendar date"},
    ]


def test_values_outside_a_range_are_quarantined() -> None:
    sales = pd.DataFrame(
        {"transaction_id": ["T1", "T2", "T3", "T4"], "discount_pct": [0.0, 100.0, -5.0, 120.0]}
    )

    result = RejectOutOfRange("transactions", "discount_pct", minimum=0, maximum=100).apply(
        sales, {}
    )

    assert result.data["transaction_id"].tolist() == ["T1", "T2"]
    assert result.rejected["reason"].tolist() == [
        "discount_pct must be between 0 and 100, got -5.0",
        "discount_pct must be between 0 and 100, got 120.0",
    ]


def test_a_minimum_can_exclude_the_bound_itself() -> None:
    articles = pd.DataFrame({"article_id": ["A1", "A2"], "purchase_price": [10.0, 0.0]})

    result = RejectOutOfRange("articles", "purchase_price", minimum=0, include_minimum=False).apply(
        articles, {}
    )

    assert result.data["article_id"].tolist() == ["A1"]
    assert result.rejected["reason"].tolist() == ["purchase_price must be greater than 0, got 0.0"]


def test_values_outside_the_allowed_set_are_quarantined() -> None:
    sales = pd.DataFrame({"transaction_id": ["T1", "T2"], "currency": ["TRY", "USD"]})

    result = RejectUnexpectedValues("transactions", "currency", {"TRY", "KRS"}).apply(sales, {})

    assert result.data["transaction_id"].tolist() == ["T1"]
    assert result.rejected["reason"].tolist() == ["currency 'USD' is not one of: KRS, TRY"]
