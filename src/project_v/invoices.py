"""Invoice models and calculations for one or more jewellery items."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from project_v import Calculation


@dataclass(frozen=True)
class Invoice:
    """Represent a customer invoice containing multiple calculated items."""

    invoice_number: str
    customer_name: str
    customer_age: int
    customer_city: str
    items: tuple[Calculation, ...]
    created_at: str

    @property
    def subtotal(self) -> float:
        """Return the sum of all item subtotals."""
        return sum(item.subtotal for item in self.items)

    @property
    def gst(self) -> float:
        """Return the sum of GST for all invoice items."""
        return sum(item.gst for item in self.items)

    @property
    def total(self) -> float:
        """Return the total payable amount for the invoice."""
        return sum(item.total for item in self.items)

    @property
    def weight_grams(self) -> float:
        """Return the combined weight of all invoice items in grams."""
        return sum(item.weight_grams for item in self.items)


def create_invoice(customer_name: str, customer_age: int, customer_city: str, items: list[Calculation]) -> Invoice:
    """Create a uniquely numbered invoice from one or more calculated items."""
    if not items:
        raise ValueError("Add at least one jewellery item before creating an invoice.")
    return Invoice(
        invoice_number=f"INV-{datetime.now():%Y%m%d}-{uuid4().hex[:6].upper()}",
        customer_name=customer_name.strip(), customer_age=customer_age,
        customer_city=customer_city.strip(), items=tuple(items),
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
