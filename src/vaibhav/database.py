"""SQLite persistence for customer invoices."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from pathlib import Path

from vaibhav import Calculation
from vaibhav.invoices import Invoice


def initialize_database(database_path: Path) -> None:
    """Create the invoice and invoice-item tables if they do not exist."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("""CREATE TABLE IF NOT EXISTS invoices (
            invoice_number TEXT PRIMARY KEY, customer_name TEXT NOT NULL,
            customer_age INTEGER NOT NULL, customer_city TEXT NOT NULL,
            created_at TEXT NOT NULL, subtotal REAL NOT NULL,
            gst REAL NOT NULL, total REAL NOT NULL, weight_grams REAL NOT NULL
        )""")
        connection.execute("""CREATE TABLE IF NOT EXISTS invoice_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_number TEXT NOT NULL,
            item_number INTEGER NOT NULL, item_json TEXT NOT NULL,
            FOREIGN KEY(invoice_number) REFERENCES invoices(invoice_number)
        )""")
        connection.commit()
    finally:
        connection.close()


def save_invoice(database_path: Path, invoice: Invoice) -> None:
    """Save an invoice and all of its items in one SQLite transaction."""
    initialize_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("INSERT INTO invoices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", (
            invoice.invoice_number, invoice.customer_name, invoice.customer_age,
            invoice.customer_city, invoice.created_at, invoice.subtotal,
            invoice.gst, invoice.total, invoice.weight_grams,
        ))
        connection.executemany(
            "INSERT INTO invoice_items (invoice_number, item_number, item_json) VALUES (?, ?, ?)",
            [(invoice.invoice_number, index, json.dumps(asdict(item))) for index, item in enumerate(invoice.items, 1)],
        )
        connection.commit()
    finally:
        connection.close()


def load_invoices(database_path: Path) -> list[dict[str, object]]:
    """Return saved invoice summaries ordered from newest to oldest."""
    initialize_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM invoices ORDER BY created_at DESC").fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]
