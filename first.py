"""Streamlit billing interface with English and Marathi language support."""

from __future__ import annotations

from pathlib import Path
from datetime import date

import pandas as pd
import streamlit as st

from project_v import PURITY_FACTORS, adjusted_price, calculate_total
from project_v.database import load_invoices, load_pledges, record_pledge_payment, save_invoice, save_pledge
from project_v.invoices import Invoice, create_invoice
from project_v.pledges import Pledge, create_pledge, default_due_date
from project_v.price_provider import get_live_price
from project_v.receipts import invoice_csv, invoice_pdf, invoice_text

DATABASE_FILE = Path(__file__).parent / "data" / "invoices.sqlite3"
UNIT_LABELS = {
    "en": {"Grams": "Grams", "Tola": "Tola", "Ounces": "Ounces", "Milligrams": "Milligrams"},
    "mr": {"Grams": "ग्रॅम", "Tola": "तोळा", "Ounces": "औंस", "Milligrams": "मिलीग्रॅम"},
}

TEXT = {
    "en": {
        "language": "मराठी", "title": "💰 Gold Jewellery Billing",
        "caption": "Live 24K price is cached for 5 minutes. Manual fallback remains available.",
        "live_settings": "Live settings", "refresh": "Refresh live gold price",
        "live_price": "Live 24K price: ₹{price:,.2f}/g\\ Updated: {updated}",
        "unavailable": "Live price unavailable. Enter the price manually.\\{error}",
        "gst_default": "GST default: {rate:.2f}% (from .env)", "customer": "Customer details",
        "name": "Name", "age": "Age", "city": "City", "item_count": "Number of jewellery items",
        "item": "Jewellery item {number}", "description": "Description", "purity": "Purity",
        "weight": "Weight", "unit": "Unit", "price": "Base 24K price / gram (₹)",
        "selected_rate": "{purity} rate / gram: ₹{price:,.2f}",
        "making": "Making / gram (₹)", "wastage": "Wastage (%)", "stones": "Stone charges (₹)",
        "gst": "GST (%)", "calculate": "Calculate invoice", "calculated": "Invoice {number} calculated successfully.",
        "total_weight": "Total weight", "subtotal": "Subtotal", "gst_metric": "GST", "final_total": "Final total",
        "txt": "Download TXT", "csv": "Download CSV", "pdf": "Download PDF", "save": "Save invoice to SQLite",
        "saved": "Invoice saved.", "history": "Saved invoices", "empty": "No invoices saved yet.",
        "comparison": "Invoice total comparison over time", "english": "English", "error": "Error",
    },
    "mr": {
        "language": "English", "title": "💰 सोन्याच्या दागिन्यांचे बिलिंग",
        "caption": "24K सोन्याचा सध्याचा दर 5 मिनिटांसाठी जतन केला जातो. मॅन्युअल दराचा पर्याय उपलब्ध आहे.",
        "live_settings": "सध्याच्या दराची सेटिंग्ज", "refresh": "सोन्याचा सध्याचा दर अपडेट करा",
        "live_price": "सध्याचा दर: ₹{price:,.2f}/ग्रॅम\\nअपडेट वेळ: {updated}",
        "unavailable": "सध्याचा दर उपलब्ध नाही. दर मॅन्युअली भरा.\\n\\n{error}",
        "gst_default": "GST दर: {rate:.2f}%", "customer": "ग्राहकाची माहिती",
        "name": "नाव", "age": "वय", "city": "शहर", "item_count": "दागिन्यांची संख्या",
        "item": "दागिना क्रमांक {number}", "description": "वर्णन", "purity": "शुद्धता",
        "weight": "वजन", "unit": "एकक", "price": "24K दर / ग्रॅम (₹)",
        "making": "घडणावळ / ग्रॅम (₹)", "wastage": "घट (%)", "stones": "खड्यांची किंमत (₹)",
        "gst": "GST (%)", "calculate": "बिलाची गणना करा", "calculated": "इनव्हॉइस {number} यशस्वीरित्या तयार झाले.",
        "total_weight": "एकूण वजन", "subtotal": "एकूण उपरक्कम", "gst_metric": "GST", "final_total": "अंतिम रक्कम",
        "txt": "TXT डाउनलोड करा", "csv": "CSV डाउनलोड करा", "pdf": "PDF डाउनलोड करा", "save": "इनव्हॉइस SQLite मध्ये जतन करा",
        "saved": "इनव्हॉइस जतन झाले.", "history": "जतन केलेली इनव्हॉइस", "empty": "अजून कोणतेही इनव्हॉइस जतन केलेले नाही.",
        "comparison": "वेगवेगळ्या वेळेतील इनव्हॉइस रकमेची तुलना", "english": "English", "error": "त्रुटी",
    },
}


def tr(key: str, **values: object) -> str:
    """Return the selected-language translation for a page label."""
    language = st.session_state.get("language", "en")
    if language == "mr" and key == "selected_rate":
        return f"{values['purity']} \u0926\u0930 / \u0917\u094d\u0930\u0945\u092e: ₹{float(values['price']):,.2f}"
    return TEXT[language][key].format(**values)


def mt(english: str, marathi: str) -> str:
    """Return a pledge-flow label in the currently selected language."""
    return marathi if st.session_state.get("language", "en") == "mr" else english


def item_form(number: int, default_price: float) -> dict[str, object]:
    """Render one jewellery-item form and return its input values."""
    st.markdown(f"#### {tr('item', number=number)}")
    first, second, third = st.columns(3)
    language = st.session_state.get("language", "en")
    description = first.text_input(tr("description"), value=f"Item {number}" if language == "en" else f"दागिना {number}", key=f"description_{number}")
    purity = second.selectbox(tr("purity"), ["24K", "22K", "20K", "18K", "14K"], key=f"purity_{number}")
    weight = third.number_input(tr("weight"), min_value=0.0, value=1.0, step=0.1, key=f"weight_{number}")
    display_units = list(UNIT_LABELS[language].values())
    selected_unit = first.selectbox(tr("unit"), display_units, key=f"unit_{number}")
    unit = next(name for name, label in UNIT_LABELS[language].items() if label == selected_unit)
    language = st.session_state.get("language", "en")
    price_label = f"{purity} price / gram (₹)" if language == "en" else f"{purity} दर / ग्रॅम (₹)"
    price = second.number_input(price_label, min_value=0.0, value=adjusted_price(default_price, purity), step=100.0, key=f"price_{number}_{purity}")
    making = third.number_input(tr("making"), min_value=0.0, value=500.0, step=50.0, key=f"making_{number}")
    wastage = first.number_input(tr("wastage"), min_value=0.0, max_value=100.0, value=0.0, step=0.5, key=f"wastage_{number}")
    stones = second.number_input(tr("stones"), min_value=0.0, value=0.0, step=100.0, key=f"stones_{number}")
    return {"description": description, "purity": purity, "weight": weight, "unit": unit,
            "price": price, "making": making, "wastage": wastage, "stones": stones}


def build_invoice(customer: dict[str, object], item_inputs: list[dict[str, object]]) -> Invoice:
    """Validate all form values, calculate every item, and create one invoice."""
    items = [calculate_total(name=str(customer["name"]), age=int(customer["age"]), city=str(customer["city"]),
                             purity=str(item["purity"]), weight=float(item["weight"]), unit=str(item["unit"]),
                             base_price=float(item["price"]) / PURITY_FACTORS[str(item["purity"])], making_charge_per_gram=float(item["making"]),
                             wastage_percent=float(item["wastage"]), stone_charges=float(item["stones"]),
                             gst_percent=0.0) for item in item_inputs]
    return create_invoice(str(customer["name"]), int(customer["age"]), str(customer["city"]), items)


def render_invoice(invoice: Invoice) -> None:
    """Display invoice totals and provide TXT, CSV, and PDF downloads."""
    st.success(tr("calculated", number=invoice.invoice_number))
    first, second, third = st.columns(3)
    first.metric(tr("total_weight"), f"{invoice.weight_grams:.3f} g")
    second.metric(tr("subtotal"), f"₹{invoice.subtotal:,.2f}")
    third.metric(tr("final_total"), f"₹{invoice.total:,.2f}")
    rows = [{"Item": index, "Purity": item.purity, "Weight (g)": item.weight_grams,
             "Gold value (₹)": item.gold_value, "Total (₹)": item.total}
            for index, item in enumerate(invoice.items, 1)]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    st.download_button(tr("txt"), invoice_text(invoice), f"{invoice.invoice_number}.txt", "text/plain")
    st.download_button(tr("csv"), invoice_csv(invoice), f"{invoice.invoice_number}.csv", "text/csv")
    try:
        st.download_button(tr("pdf"), invoice_pdf(invoice), f"{invoice.invoice_number}.pdf", "application/pdf")
    except RuntimeError as error:
        st.warning(str(error))
    if st.button(tr("save")):
        save_invoice(DATABASE_FILE, invoice)
        st.success(tr("saved"))


def render_history() -> None:
    """Display saved invoices and compare their totals over time."""
    st.subheader(tr("history"))
    rows = load_invoices(DATABASE_FILE)
    if not rows:
        st.info(tr("empty"))
        return
    history = pd.DataFrame(rows)
    st.dataframe(history, hide_index=True, width="stretch")
    chart = history.assign(created_at=pd.to_datetime(history["created_at"])).set_index("created_at")[["total"]]
    st.caption(tr("comparison"))
    st.line_chart(chart)


def render_live_rate_table(base_price: float) -> None:
    """Display the live 24K base rate and calculated rates for every supported purity."""
    language = st.session_state.get("language", "en")
    rows = [{
        "Purity" if language == "en" else "शुद्धता": purity,
        "Rate / gram (₹)" if language == "en" else "दर / ग्रॅम (₹)": adjusted_price(base_price, purity),
    } for purity in ["24K", "22K", "20K", "18K", "14K"]]
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")


def render_pledge_flow(default_price: float) -> None:
    """Render the gold pledge valuation, loan, repayment, and redemption workflow."""
    st.subheader(mt("Gold Pledge / Loan Against Jewellery", "सोनेचे तारण / दागिन्यांवर कर्ज"))
    st.caption(mt("Record jewellery kept as collateral and the money given to the customer.", "ग्राहकाने तारण ठेवलेले दागिने आणि दिलेली कर्जाची रक्कम नोंदवा."))
    first, second, third = st.columns(3)
    name = first.text_input(mt("Customer name", "ग्राहकाचे नाव"), key="pledge_name")
    age = second.number_input(mt("Customer age", "ग्राहकाचे वय"), min_value=0, max_value=120, value=18, key="pledge_age")
    city = third.text_input(mt("Customer city", "ग्राहकाचे शहर"), key="pledge_city")
    first, second, third = st.columns(3)
    description = first.text_input(mt("Jewellery description", "दागिन्यांचे वर्णन"), value="Gold jewellery", key="pledge_description")
    purity = second.selectbox(mt("Gold purity", "सोन्याची शुद्धता"), ["24K", "22K", "20K", "18K", "14K"], key="pledge_purity")
    gross_weight = third.number_input(mt("Gross weight (g)", "एकूण वजन (ग्रॅम)"), min_value=0.0, value=10.0, step=0.1, key="pledge_gross_weight")
    first, second, third = st.columns(3)
    stone_weight = first.number_input(mt("Stone weight (g)", "खड्यांचे वजन (ग्रॅम)"), min_value=0.0, value=0.0, step=0.1, key="pledge_stone_weight")
    base_price = second.number_input(mt("Base 24K price / gram (₹)", "मूळ 24K दर / ग्रॅम (₹)"), min_value=0.0, value=default_price, step=100.0, key="pledge_base_price")
    ltv = third.number_input(mt("Loan-to-value (%)", "कर्ज-मूल्य प्रमाण (%)"), min_value=1.0, max_value=100.0, value=70.0, step=1.0, key="pledge_ltv")
    net_weight = max(gross_weight - stone_weight, 0.0)
    purity_price = adjusted_price(base_price, purity)
    gold_value = net_weight * purity_price
    maximum_loan = gold_value * ltv / 100
    first, second, third = st.columns(3)
    first.metric(mt("Net gold weight", "निव्वळ सोन्याचे वजन"), f"{net_weight:.3f} g")
    second.metric(mt(f"{purity} rate / gram", f"{purity} दर / ग्रॅम"), f"₹{purity_price:,.2f}")
    third.metric(mt("Maximum loan", "कमाल कर्ज"), f"₹{maximum_loan:,.2f}")
    requested_loan = st.number_input(mt("Requested loan amount (₹)", "मागितलेली कर्जाची रक्कम (₹)"), min_value=0.0, value=float(maximum_loan), step=100.0, key="pledge_requested_loan")
    monthly_interest = st.number_input(mt("Monthly interest (%)", "मासिक व्याज (%)"), min_value=0.0, value=2.0, step=0.1, key="pledge_interest")
    due_date = st.date_input(mt("Due date", "देय तारीख"), value=default_due_date(), min_value=date.today(), key="pledge_due_date")
    storage_reference = st.text_input(mt("Storage packet / locker reference", "साठवण पाकीट / लॉकर क्रमांक"), key="pledge_storage")
    notes = st.text_area(mt("Notes", "नोंदी"), key="pledge_notes")
    if st.button(mt("Create pledge record", "तारण नोंद तयार करा"), type="primary"):
        try:
            pledge = create_pledge(
                customer_name=name, customer_age=int(age), customer_city=city,
                description=description, purity=purity, gross_weight_grams=gross_weight,
                stone_weight_grams=stone_weight, base_price_24k=base_price, ltv_percent=ltv,
                requested_loan=requested_loan, monthly_interest_percent=monthly_interest,
                due_date=due_date, storage_reference=storage_reference, notes=notes,
            )
            save_pledge(DATABASE_FILE, pledge)
            st.session_state.last_pledge = pledge
            st.success(mt(f"Pledge {pledge.pledge_number} saved successfully.", f"तारण {pledge.pledge_number} यशस्वीरित्या जतन झाले."))
        except ValueError as error:
            st.error(str(error))
    render_pledge_history()


def render_pledge_history() -> None:
    """Display pledge records and allow repayments until a pledge is redeemed."""
    st.subheader(mt("Pledge records and repayments", "तारण नोंदी आणि परतफेडी"))
    rows = load_pledges(DATABASE_FILE)
    if not rows:
        st.info(mt("No pledge records yet.", "अजून कोणत्याही तारण नोंदी नाहीत."))
        return
    summaries = []
    for row in rows:
        details = row["pledge_json"]
        if isinstance(details, str):
            import json
            details = json.loads(details)
        summaries.append({
            mt("Pledge", "तारण"): row["pledge_number"], mt("Customer", "ग्राहक"): row["customer_name"],
            mt("Purity", "शुद्धता"): details["purity"], mt("Net weight (g)", "निव्वळ वजन (ग्रॅम)"): details["net_gold_weight_grams"],
            mt("Loan (₹)", "कर्ज (₹)"): row["requested_loan"], mt("Paid (₹)", "भरलेले (₹)"): row["amount_paid"],
            mt("Outstanding (₹)", "बाकी (₹)"): max(row["requested_loan"] - row["amount_paid"], 0),
            mt("Due date", "देय तारीख"): row["due_date"], mt("Status", "स्थिती"): row["status"],
        })
    st.dataframe(pd.DataFrame(summaries), hide_index=True, width="stretch")
    active = [row["pledge_number"] for row in rows if row["status"] == "Active"]
    if active:
        selected = st.selectbox(mt("Pledge for repayment", "परतफेडीसाठी तारण"), active, key="repayment_pledge")
        amount = st.number_input(mt("Payment amount (₹)", "परतफेड रक्कम (₹)"), min_value=0.0, value=0.0, step=100.0, key="repayment_amount")
        note = st.text_input(mt("Payment note", "परतफेडीची नोंद"), key="repayment_note")
        if st.button(mt("Record repayment", "परतफेड नोंदवा")):
            try:
                record_pledge_payment(DATABASE_FILE, selected, amount, note)
                st.success(mt("Repayment recorded. Refresh the page to see the updated status.", "परतफेड नोंदवली. अद्ययावत स्थिती पाहण्यासाठी पृष्ठ रिफ्रेश करा."))
            except ValueError as error:
                st.error(str(error))


def render_app() -> None:
    """Render the complete multi-item Streamlit billing application."""
    language = st.session_state.get("language", "en")
    st.set_page_config(page_title="Gold Billing", page_icon="💰", layout="wide")
    with st.sidebar:
        marathi = st.toggle("मराठी", value=language == "mr")
        st.session_state.language = "mr" if marathi else "en"
    st.title(tr("title"))
    st.caption(tr("caption"))
    default_price = 14826.0
    with st.sidebar:
        st.header(tr("live_settings"))
        if st.button(tr("refresh")):
            get_live_price.clear()
        try:
            default_price, updated_at = get_live_price()
            st.success(tr("live_price", price=default_price, updated=updated_at))
            render_live_rate_table(default_price)
        except RuntimeError as error:
            st.warning(tr("unavailable", error=error))
    sale_tab, pledge_tab = st.tabs([mt("Jewellery Sale", "दागिन्यांची विक्री"), mt("Gold Pledge / Loan", "सोने तारण / कर्ज")])
    with sale_tab:
        st.subheader(tr("customer"))
        first, second, third = st.columns(3)
        customer = {"name": first.text_input(tr("name")), "age": second.number_input(tr("age"), min_value=0, max_value=120, value=18), "city": third.text_input(tr("city"))}
        item_count = st.number_input(tr("item_count"), min_value=1, max_value=10, value=1, step=1)
        item_inputs = [item_form(index, default_price) for index in range(1, int(item_count) + 1)]
        submitted = st.button(tr("calculate"), type="primary")
        if submitted:
            try:
                st.session_state.invoice = build_invoice(customer, item_inputs)
            except ValueError as error:
                st.error(f"{tr('error')}: {error}")
        if invoice := st.session_state.get("invoice"):
            render_invoice(invoice)
        render_history()
    with pledge_tab:
        render_pledge_flow(default_price)


if __name__ == "__main__":
    render_app()
