import pandas as pd

from retail_analytics.validation.transaction_rules import (
    ConvertKurusToLira,
    InferFutureDatesFromIdOrder,
    RejectNonPositiveQuantity,
)


def test_kurus_prices_are_converted_to_lira() -> None:
    sales = pd.DataFrame(
        {
            "transaction_id": ["TXN-1", "TXN-2"],
            "selling_price": [49582.0, 501.0],
            "currency": ["KRS", "TRY"],
        }
    )

    result = ConvertKurusToLira().apply(sales, {})

    assert result.data["selling_price"].tolist() == [495.82, 501.0]
    assert result.data["currency"].tolist() == ["TRY", "TRY"]
    assert result.fixed_count == 1
    assert result.rejected.empty


def test_non_positive_quantities_are_quarantined_with_a_reason() -> None:
    sales = pd.DataFrame({"transaction_id": ["TXN-1", "TXN-2", "TXN-3"], "quantity": [2, -3, 0]})

    result = RejectNonPositiveQuantity().apply(sales, {})

    assert result.data["transaction_id"].tolist() == ["TXN-1"]
    assert result.rejected["transaction_id"].tolist() == ["TXN-2", "TXN-3"]
    assert result.rejected["reason"].tolist() == [
        "quantity must be positive, got -3",
        "quantity must be positive, got 0",
    ]


AS_OF = pd.Timestamp("2026-09-17")


def test_future_dates_take_the_date_of_the_preceding_transaction_id() -> None:
    sales = pd.DataFrame(
        {
            "transaction_id": ["TXN-5", "TXN-7", "TXN-6", "TXN-8", "TXN-9"],
            "date": pd.to_datetime(
                ["2024-03-01", "2027-01-15", "2024-03-02", "2024-03-03", "2027-02-01"]
            ),
        }
    )

    result = InferFutureDatesFromIdOrder(as_of=AS_OF).apply(sales, {})

    dates = result.data.set_index("transaction_id")["date"]
    assert dates["TXN-7"] == pd.Timestamp("2024-03-02")
    assert dates["TXN-9"] == pd.Timestamp("2024-03-03")
    assert result.fixed_count == 2
    assert result.flagged[["transaction_id", "original_date", "reason"]].to_dict("records") == [
        {
            "transaction_id": "TXN-7",
            "original_date": pd.Timestamp("2027-01-15"),
            "reason": "future date replaced with the date of preceding transaction TXN-6",
        },
        {
            "transaction_id": "TXN-9",
            "original_date": pd.Timestamp("2027-02-01"),
            "reason": "future date replaced with the date of preceding transaction TXN-8",
        },
    ]


def test_future_dates_are_quarantined_when_ids_are_not_in_date_order() -> None:
    sales = pd.DataFrame(
        {
            "transaction_id": ["TXN-1", "TXN-2", "TXN-3"],
            "date": pd.to_datetime(["2024-03-05", "2024-03-01", "2027-01-15"]),
        }
    )

    result = InferFutureDatesFromIdOrder(as_of=AS_OF).apply(sales, {})

    assert result.data["transaction_id"].tolist() == ["TXN-1", "TXN-2"]
    assert result.rejected["reason"].tolist() == [
        "future date, and transaction ids are not in date order so no date can be inferred"
    ]
