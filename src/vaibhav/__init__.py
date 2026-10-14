"""Reusable calculation and validation helpers for the gold calculator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

PURITY_FACTORS = {
    "24K": 1.0,
    "22K": 22 / 24,
    "18K": 18 / 24,
    "14K": 14 / 24,
}

UNIT_TO_GRAMS = {
    "Grams": 1.0,
    "Tola": 11.6638038,
    "Ounces": 31.1034768,
    "Milligrams": 0.001,
}


def main() -> None:
    """Print the command used to start the Streamlit application."""
    print("Run the application with: uv run streamlit run first.py")


@dataclass(frozen=True)
class Calculation:
    """Store every input and result needed for a customer receipt."""

    name: str
    age: int
    city: str
    purity: str
    input_weight: float
    unit: str
    weight_grams: float
    base_price_per_gram: float
    adjusted_price_per_gram: float
    gold_value: float
    making_charges: float
    wastage_charges: float
    stone_charges: float
    subtotal: float
    gst: float
    gst_rate: float
    total: float
    created_at: str


def validate_customer(name: str, age: int, city: str) -> list[str]:
    """Return validation errors for customer name, age, and city fields."""
    errors: list[str] = []
    if not name.strip() or not all(char.isalpha() or char in " .-'" for char in name):
        errors.append("Name must contain letters and may include spaces, dots, or hyphens.")
    if age < 1 or age > 120:
        errors.append("Age must be between 1 and 120.")
    if not city.strip() or not all(char.isalpha() or char in " .-'" for char in city):
        errors.append("City must contain letters and may include spaces, dots, or hyphens.")
    return errors


def validate_positive_values(**values: float) -> list[str]:
    """Return validation errors for numeric values that must not be negative."""
    errors: list[str] = []
    for label, value in values.items():
        if value < 0:
            errors.append(f"{label.replace('_', ' ').capitalize()} cannot be negative.")
    return errors


def convert_to_grams(weight: float, unit: str) -> float:
    """Convert a weight from grams, tola, ounces, or milligrams to grams."""
    if weight < 0:
        raise ValueError("Weight cannot be negative.")
    if unit not in UNIT_TO_GRAMS:
        raise ValueError(f"Unsupported weight unit: {unit}")
    return weight * UNIT_TO_GRAMS[unit]


def adjusted_price(base_price: float, purity: str) -> float:
    """Calculate the price per gram for the selected gold purity."""
    if base_price < 0:
        raise ValueError("Gold price cannot be negative.")
    if purity not in PURITY_FACTORS:
        raise ValueError(f"Unsupported purity: {purity}")
    return base_price * PURITY_FACTORS[purity]


def calculate_total(
    *,
    name: str,
    age: int,
    city: str,
    purity: str,
    weight: float,
    unit: str,
    base_price: float,
    making_charge_per_gram: float,
    wastage_percent: float,
    stone_charges: float,
    gst_percent: float,
) -> Calculation:
    """Calculate gold value, jewellery charges, GST, and the final amount."""
    errors = validate_customer(name, age, city)
    errors.extend(validate_positive_values(
        weight=weight,
        base_price=base_price,
        making_charge_per_gram=making_charge_per_gram,
        wastage_percent=wastage_percent,
        stone_charges=stone_charges,
        gst_percent=gst_percent,
    ))
    if wastage_percent > 100:
        errors.append("Wastage percentage cannot be greater than 100.")
    if gst_percent > 100:
        errors.append("GST percentage cannot be greater than 100.")
    if purity not in PURITY_FACTORS:
        errors.append("Select a valid gold purity.")
    if unit not in UNIT_TO_GRAMS:
        errors.append("Select a valid weight unit.")
    if errors:
        raise ValueError(" ".join(errors))

    grams = convert_to_grams(weight, unit)
    price = adjusted_price(base_price, purity)
    gold_value = grams * price
    making = grams * making_charge_per_gram
    wastage = gold_value * wastage_percent / 100
    subtotal = gold_value + making + wastage + stone_charges
    gst = subtotal * gst_percent / 100
    return Calculation(
        name=name.strip(), age=age, city=city.strip(), purity=purity,
        input_weight=weight, unit=unit, weight_grams=grams,
        base_price_per_gram=base_price, adjusted_price_per_gram=price,
        gold_value=gold_value, making_charges=making,
        wastage_charges=wastage, stone_charges=stone_charges,
        subtotal=subtotal, gst=gst, gst_rate=gst_percent,
        total=subtotal + gst,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )


def calculation_to_dict(calculation: Calculation) -> dict[str, Any]:
    """Convert a calculation into a flat dictionary for CSV and history storage."""
    return {field: getattr(calculation, field) for field in calculation.__dataclass_fields__}


def receipt_text(calculation: Calculation) -> str:
    """Create a human-readable plain-text customer receipt."""
    c = calculation
    rows = [
        "GOLD JEWELLERY RECEIPT",
        "=" * 28,
        f"Date: {c.created_at}", f"Customer: {c.name}", f"Age: {c.age}",
        f"City: {c.city}", f"Purity: {c.purity}",
        f"Weight: {c.input_weight:.4f} {c.unit} ({c.weight_grams:.4f} g)",
        "-" * 28, f"Gold value:       ₹{c.gold_value:,.2f}",
        f"Making charges:   ₹{c.making_charges:,.2f}",
        f"Wastage charges:  ₹{c.wastage_charges:,.2f}",
        f"Stone charges:    ₹{c.stone_charges:,.2f}",
        f"Subtotal:         ₹{c.subtotal:,.2f}",
        f"GST ({c.gst_rate:.2f}%):       ₹{c.gst:,.2f}",
        "=" * 28, f"TOTAL:            ₹{c.total:,.2f}",
    ]
    return "\n".join(rows) + "\n"
