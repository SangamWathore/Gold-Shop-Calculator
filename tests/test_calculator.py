"""Automated tests for gold calculations and invoices."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

import pytest

from project_v import calculate_total, convert_to_grams
from project_v.invoices import create_invoice


def make_item():
    """Create a valid sample jewellery calculation for tests."""
    return calculate_total(name="Asha", age=30, city="Pune", purity="22K", weight=10,
                           unit="Grams", base_price=14826, making_charge_per_gram=500,
                           wastage_percent=5, stone_charges=1000, gst_percent=3)


def test_purity_and_unit_conversion():
    """Verify purity adjustment and tola conversion."""
    assert calculate_total(name="A", age=20, city="Pune", purity="18K", weight=1,
                           unit="Grams", base_price=24000, making_charge_per_gram=0,
                           wastage_percent=0, stone_charges=0, gst_percent=0).adjusted_price_per_gram == 18000
    assert convert_to_grams(1, "Tola") == pytest.approx(11.6638038)


def test_invalid_customer_is_rejected():
    """Verify invalid customer values raise a useful validation error."""
    with pytest.raises(ValueError, match="Name"):
        calculate_total(name="", age=0, city="123", purity="24K", weight=1,
                        unit="Grams", base_price=1, making_charge_per_gram=0,
                        wastage_percent=0, stone_charges=0, gst_percent=0)


def test_invoice_totals_include_multiple_items():
    """Verify an invoice aggregates all item totals."""
    first, second = make_item(), make_item()
    invoice = create_invoice("Asha", 30, "Pune", [first, second])
    assert invoice.total == pytest.approx(first.total + second.total)
