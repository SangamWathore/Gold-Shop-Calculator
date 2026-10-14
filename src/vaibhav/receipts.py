"""TXT, CSV, and PDF receipt generation."""

from __future__ import annotations

import csv
import io

from vaibhav.invoices import Invoice


def invoice_text(invoice: Invoice) -> str:
    """Create a readable text receipt for a multi-item invoice."""
    lines = ["GOLD JEWELLERY INVOICE", "=" * 32, f"Invoice: {invoice.invoice_number}",
             f"Date: {invoice.created_at}", f"Customer: {invoice.customer_name}",
             f"Age: {invoice.customer_age}", f"City: {invoice.customer_city}", ""]
    for number, item in enumerate(invoice.items, 1):
        lines.extend([f"Item {number}: {item.purity} gold", f"  Weight: {item.input_weight:.4f} {item.unit} ({item.weight_grams:.4f} g)",
                      f"  Gold value: ₹{item.gold_value:,.2f}", f"  Charges: ₹{item.making_charges + item.wastage_charges + item.stone_charges:,.2f}",
                      f"  GST: ₹{item.gst:,.2f}", f"  Item total: ₹{item.total:,.2f}"])
    lines.extend(["=" * 32, f"Subtotal: ₹{invoice.subtotal:,.2f}", f"GST: ₹{invoice.gst:,.2f}", f"TOTAL: ₹{invoice.total:,.2f}"])
    return "\n".join(lines) + "\n"


def invoice_csv(invoice: Invoice) -> bytes:
    """Create a CSV receipt containing invoice and item details."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Invoice", invoice.invoice_number])
    writer.writerow(["Customer", invoice.customer_name])
    writer.writerow(["Date", invoice.created_at])
    writer.writerow([])
    writer.writerow(["Item", "Purity", "Weight (g)", "Gold value", "GST", "Total"])
    for number, item in enumerate(invoice.items, 1):
        writer.writerow([number, item.purity, item.weight_grams, item.gold_value, item.gst, item.total])
    writer.writerow(["TOTAL", "", invoice.weight_grams, "", invoice.gst, invoice.total])
    return output.getvalue().encode("utf-8")


def invoice_pdf(invoice: Invoice) -> bytes:
    """Create a PDF receipt using ReportLab, raising a helpful error if unavailable."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as error:
        raise RuntimeError("PDF support requires ReportLab. Run: uv sync") from error
    output = io.BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    _, height = A4
    y = height - 50
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, "GOLD JEWELLERY INVOICE")
    pdf.setFont("Helvetica", 10)
    y -= 25
    for line in invoice_text(invoice).splitlines():
        if y < 50:
            pdf.showPage(); y = height - 50
        pdf.drawString(50, y, line.replace("₹", "INR "))
        y -= 15
    pdf.save()
    return output.getvalue()
