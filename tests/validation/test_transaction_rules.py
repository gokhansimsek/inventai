import pandas as pd

from retail_analytics.validation.transaction_rules import (
    ConvertKurusToLira,
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

    result = ConvertKurusToLira().apply(sales)

    assert result.data["selling_price"].tolist() == [495.82, 501.0]
    assert result.data["currency"].tolist() == ["TRY", "TRY"]
    assert result.fixed_count == 1
    assert result.rejected.empty


def test_non_positive_quantities_are_quarantined_with_a_reason() -> None:
    sales = pd.DataFrame({"transaction_id": ["TXN-1", "TXN-2", "TXN-3"], "quantity": [2, -3, 0]})

    result = RejectNonPositiveQuantity().apply(sales)

    assert result.data["transaction_id"].tolist() == ["TXN-1"]
    assert result.rejected["transaction_id"].tolist() == ["TXN-2", "TXN-3"]
    assert result.rejected["reason"].tolist() == [
        "quantity must be positive, got -3",
        "quantity must be positive, got 0",
    ]
