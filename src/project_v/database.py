"""SQLite persistence for customer invoices."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from project_v import Calculation
from project_v.invoices import Invoice
from project_v.pledges import Pledge, pledge_to_dict


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


def initialize_pledge_tables(database_path: Path) -> None:
    """Create SQLite tables for gold pledges and their repayments."""
    initialize_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("""CREATE TABLE IF NOT EXISTS pledges (
            pledge_number TEXT PRIMARY KEY, pledge_json TEXT NOT NULL,
            created_at TEXT NOT NULL, customer_name TEXT NOT NULL,
            requested_loan REAL NOT NULL, amount_paid REAL NOT NULL,
            status TEXT NOT NULL, due_date TEXT NOT NULL
        )""")
        connection.execute("""CREATE TABLE IF NOT EXISTS pledge_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, pledge_number TEXT NOT NULL,
            payment_amount REAL NOT NULL, payment_date TEXT NOT NULL,
            note TEXT, FOREIGN KEY(pledge_number) REFERENCES pledges(pledge_number)
        )""")
        connection.commit()
    finally:
        connection.close()


def save_pledge(database_path: Path, pledge: Pledge) -> None:
    """Save a new pledge and its collateral details in SQLite."""
    initialize_pledge_tables(database_path)
    data = pledge_to_dict(pledge)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            "INSERT INTO pledges VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (pledge.pledge_number, json.dumps(data), pledge.created_at, pledge.customer_name,
             pledge.requested_loan, pledge.amount_paid, pledge.status, pledge.due_date),
        )
        connection.commit()
    finally:
        connection.close()


def load_pledges(database_path: Path) -> list[dict[str, object]]:
    """Return saved pledge summaries ordered from newest to oldest."""
    initialize_pledge_tables(database_path)
    connection = sqlite3.connect(database_path)
    try:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT * FROM pledges ORDER BY created_at DESC").fetchall()
    finally:
        connection.close()
    return [dict(row) for row in rows]


def record_pledge_payment(database_path: Path, pledge_number: str, amount: float, note: str = "") -> None:
    """Record a pledge repayment and update its paid amount and status."""
    if amount <= 0:
        raise ValueError("Payment amount must be greater than zero.")
    initialize_pledge_tables(database_path)
    connection = sqlite3.connect(database_path)
    try:
        row = connection.execute("SELECT requested_loan, amount_paid FROM pledges WHERE pledge_number = ?", (pledge_number,)).fetchone()
        if row is None:
            raise ValueError("Pledge was not found.")
        requested_loan, amount_paid = row
        new_amount_paid = amount_paid + amount
        if new_amount_paid > requested_loan:
            raise ValueError("Payment cannot be greater than the outstanding loan.")
        status = "Redeemed" if new_amount_paid >= requested_loan else "Active"
        connection.execute("INSERT INTO pledge_payments (pledge_number, payment_amount, payment_date, note) VALUES (?, ?, ?, ?)",
                           (pledge_number, amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), note))
        connection.execute("UPDATE pledges SET amount_paid = ?, status = ? WHERE pledge_number = ?",
                           (new_amount_paid, status, pledge_number))
        connection.commit()
    finally:
        connection.close()
