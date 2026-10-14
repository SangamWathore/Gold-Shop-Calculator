"""Gold jewellery pledge and loan calculations."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date, datetime, timedelta
from uuid import uuid4

from project_v import PURITY_FACTORS, adjusted_price


@dataclass(frozen=True)
class Pledge:
    """Represent jewellery deposited as collateral for a customer loan."""

    pledge_number: str
    customer_name: str
    customer_age: int
    customer_city: str
    description: str
    purity: str
    gross_weight_grams: float
    stone_weight_grams: float
    net_gold_weight_grams: float
    base_price_24k_per_gram: float
    purity_price_per_gram: float
    gold_value: float
    ltv_percent: float
    maximum_loan: float
    requested_loan: float
    monthly_interest_percent: float
    due_date: str
    storage_reference: str
    notes: str
    status: str
    amount_paid: float
    created_at: str
    photo_paths: tuple[str, ...] = ()

    @property
    def outstanding_amount(self) -> float:
        """Return the remaining principal before any future interest calculation."""
        return max(self.requested_loan - self.amount_paid, 0.0)


def create_pledge(
    *, customer_name: str, customer_age: int, customer_city: str,
    description: str, purity: str, gross_weight_grams: float,
    stone_weight_grams: float, base_price_24k: float, ltv_percent: float,
    requested_loan: float, monthly_interest_percent: float,
    due_date: date, storage_reference: str, notes: str,
    photo_paths: tuple[str, ...] = (),
) -> Pledge:
    """Validate pledge details and calculate the collateral value and loan limit."""
    if not customer_name.strip() or not customer_city.strip():
        raise ValueError("Customer name and city are required.")
    if customer_age < 1 or customer_age > 120:
        raise ValueError("Customer age must be between 1 and 120.")
    if purity not in PURITY_FACTORS:
        raise ValueError("Select a valid gold purity.")
    for label, value in {
        "Gross weight": gross_weight_grams, "Stone weight": stone_weight_grams,
        "24K price": base_price_24k, "LTV percentage": ltv_percent,
        "Requested loan": requested_loan, "Monthly interest": monthly_interest_percent,
    }.items():
        if value < 0:
            raise ValueError(f"{label} cannot be negative.")
    if stone_weight_grams > gross_weight_grams:
        raise ValueError("Stone weight cannot be greater than gross weight.")
    if not 0 < ltv_percent <= 100:
        raise ValueError("LTV percentage must be greater than 0 and at most 100.")
    if due_date < date.today():
        raise ValueError("Due date cannot be in the past.")

    net_weight = gross_weight_grams - stone_weight_grams
    purity_price = adjusted_price(base_price_24k, purity)
    gold_value = net_weight * purity_price
    maximum_loan = gold_value * ltv_percent / 100
    if requested_loan > maximum_loan:
        raise ValueError(f"Requested loan cannot exceed the maximum loan of ₹{maximum_loan:,.2f}.")
    return Pledge(
        pledge_number=f"PLG-{datetime.now():%Y%m%d}-{uuid4().hex[:6].upper()}",
        customer_name=customer_name.strip(), customer_age=customer_age,
        customer_city=customer_city.strip(), description=description.strip(), purity=purity,
        gross_weight_grams=gross_weight_grams, stone_weight_grams=stone_weight_grams,
        net_gold_weight_grams=net_weight, base_price_24k_per_gram=base_price_24k,
        purity_price_per_gram=purity_price, gold_value=gold_value,
        ltv_percent=ltv_percent, maximum_loan=maximum_loan, requested_loan=requested_loan,
        monthly_interest_percent=monthly_interest_percent, due_date=due_date.isoformat(),
        storage_reference=storage_reference.strip(), notes=notes.strip(), status="Active",
        amount_paid=0.0, created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        photo_paths=photo_paths,
    )


def pledge_to_dict(pledge: Pledge) -> dict[str, object]:
    """Convert a pledge into a database-ready dictionary."""
    return asdict(pledge)


def default_due_date(days: int = 90) -> date:
    """Return a default pledge due date a set number of days from today."""
    return date.today() + timedelta(days=days)
