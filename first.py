"""Streamlit billing interface for multi-item gold jewellery invoices."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from vaibhav import calculate_total
from vaibhav.database import load_invoices, save_invoice
from vaibhav.invoices import Invoice, create_invoice
from vaibhav.price_provider import configured_gst_rate, get_live_price
from vaibhav.receipts import invoice_csv, invoice_pdf, invoice_text

DATABASE_FILE = Path(__file__).parent / "data" / "invoices.sqlite3"


def item_form(number: int, default_price: float, default_gst: float) -> dict[str, object]:
    """Render one jewellery-item form and return its input values."""
    st.markdown(f"#### Jewellery item {number}")
    first, second, third = st.columns(3)
    description = first.text_input("Description", value=f"Item {number}", key=f"description_{number}")
    purity = second.selectbox("Purity", ["24K", "22K", "18K", "14K"], key=f"purity_{number}")
    weight = third.number_input("Weight", min_value=0.0, value=1.0, step=0.1, key=f"weight_{number}")
    unit = first.selectbox("Unit", ["Grams", "Tola", "Ounces", "Milligrams"], key=f"unit_{number}")
    price = second.number_input("24K price / gram (₹)", min_value=0.0, value=default_price, step=100.0, key=f"price_{number}")
    making = third.number_input("Making / gram (₹)", min_value=0.0, value=500.0, step=50.0, key=f"making_{number}")
    wastage = first.number_input("Wastage (%)", min_value=0.0, max_value=100.0, value=0.0, step=0.5, key=f"wastage_{number}")
    stones = second.number_input("Stone charges (₹)", min_value=0.0, value=0.0, step=100.0, key=f"stones_{number}")
    gst = third.number_input("GST (%)", min_value=0.0, max_value=100.0, value=default_gst, step=0.5, key=f"gst_{number}")
    return {"description": description, "purity": purity, "weight": weight, "unit": unit,
            "price": price, "making": making, "wastage": wastage, "stones": stones, "gst": gst}


def build_invoice(customer: dict[str, object], item_inputs: list[dict[str, object]]) -> Invoice:
    """Validate all form values, calculate every item, and create one invoice."""
    items = [calculate_total(name=str(customer["name"]), age=int(customer["age"]), city=str(customer["city"]),
                             purity=str(item["purity"]), weight=float(item["weight"]), unit=str(item["unit"]),
                             base_price=float(item["price"]), making_charge_per_gram=float(item["making"]),
                             wastage_percent=float(item["wastage"]), stone_charges=float(item["stones"]),
                             gst_percent=float(item["gst"])) for item in item_inputs]
    return create_invoice(str(customer["name"]), int(customer["age"]), str(customer["city"]), items)


def render_invoice(invoice: Invoice) -> None:
    """Display invoice totals and provide TXT, CSV, and PDF downloads."""
    st.success(f"Invoice {invoice.invoice_number} calculated successfully.")
    first, second, third = st.columns(3)
    first.metric("Total weight", f"{invoice.weight_grams:.3f} g")
    second.metric("GST", f"₹{invoice.gst:,.2f}")
    third.metric("Final total", f"₹{invoice.total:,.2f}")
    rows = [{"Item": index, "Purity": item.purity, "Weight (g)": item.weight_grams, "Gold value (₹)": item.gold_value, "Total (₹)": item.total}
            for index, item in enumerate(invoice.items, 1)]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.download_button("Download TXT", invoice_text(invoice), f"{invoice.invoice_number}.txt", "text/plain")
    st.download_button("Download CSV", invoice_csv(invoice), f"{invoice.invoice_number}.csv", "text/csv")
    try:
        st.download_button("Download PDF", invoice_pdf(invoice), f"{invoice.invoice_number}.pdf", "application/pdf")
    except RuntimeError as error:
        st.warning(str(error))
    if st.button("Save invoice to SQLite"):
        save_invoice(DATABASE_FILE, invoice)
        st.success("Invoice saved.")


def render_history() -> None:
    """Display saved invoices and compare their totals over time."""
    st.subheader("Saved invoices")
    rows = load_invoices(DATABASE_FILE)
    if not rows:
        st.info("No invoices saved yet.")
        return
    history = pd.DataFrame(rows)
    st.dataframe(history, hide_index=True, width="stretch")
    chart = history.assign(created_at=pd.to_datetime(history["created_at"])).set_index("created_at")[["total"]]
    st.caption("Invoice total comparison over time")
    st.line_chart(chart)


def render_app() -> None:
    """Render the complete multi-item Streamlit billing application."""
    st.set_page_config(page_title="Gold Billing", page_icon="💰", layout="wide")
    st.title("💰 Gold Jewellery Billing")
    st.caption("Live 24K price is cached for 5 minutes. Manual fallback remains available.")
    default_price = 14826.0
    price_status = "Manual fallback"
    with st.sidebar:
        st.header("Live settings")
        if st.button("Refresh live gold price"):
            get_live_price.clear()
        try:
            default_price, updated_at = get_live_price()
            price_status = f"Live price: ₹{default_price:,.2f}/g\nUpdated: {updated_at}"
            st.success(price_status)
        except RuntimeError as error:
            st.warning(f"Live price unavailable. Enter the price manually.\n\n{error}")
        default_gst = configured_gst_rate()
        st.info(f"GST default: {default_gst:.2f}% (from .env)")
    with st.form("customer_form"):
        st.subheader("Customer details")
        first, second, third = st.columns(3)
        customer = {"name": first.text_input("Name"), "age": second.number_input("Age", min_value=0, max_value=120, value=18), "city": third.text_input("City")}
        item_count = st.number_input("Number of jewellery items", min_value=1, max_value=10, value=1, step=1)
        item_inputs = [item_form(index, default_price, default_gst) for index in range(1, int(item_count) + 1)]
        submitted = st.form_submit_button("Calculate invoice", type="primary")
    if submitted:
        try:
            st.session_state.invoice = build_invoice(customer, item_inputs)
        except ValueError as error:
            st.error(str(error))
    if invoice := st.session_state.get("invoice"):
        render_invoice(invoice)
    render_history()


if __name__ == "__main__":
    render_app()
