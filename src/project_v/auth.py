"""Registration and password authentication for shopkeeper accounts."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

AUTH_DATABASE = Path(__file__).parents[2] / "data" / "invoices.sqlite3"
load_dotenv()


def hash_password(password: str) -> str:
    """Create a salted PBKDF2 password hash for database storage."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored salted PBKDF2 hash."""
    try:
        salt_hex, digest_hex = stored_hash.split("$", maxsplit=1)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), 310_000)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def initialize_user_table() -> None:
    """Create the shopkeeper account table if it does not already exist."""
    AUTH_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(AUTH_DATABASE)
    try:
        connection.execute("""CREATE TABLE IF NOT EXISTS shopkeepers (
            username TEXT PRIMARY KEY, password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'staff', created_at TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )""")
        connection.commit()
    finally:
        connection.close()


def registration_code() -> str:
    """Read the private registration code from Streamlit secrets or local .env."""
    try:
        secret_code = str(st.secrets.get("REGISTRATION_CODE", "")).strip()
    except FileNotFoundError:
        secret_code = ""
    return secret_code or os.getenv("REGISTRATION_CODE", "").strip()


def register_user(username: str, password: str, confirmation: str, code: str) -> tuple[bool, str]:
    """Validate and register a new shopkeeper account in SQLite."""
    username = username.strip()
    if len(username) < 3 or not username.replace("_", "").isalnum():
        return False, "Username must contain at least 3 letters or numbers."
    if len(password) < 8:
        return False, "Password must contain at least 8 characters."
    if password != confirmation:
        return False, "Passwords do not match."
    expected_code = registration_code()
    if not expected_code:
        return False, "Registration is not configured. Add REGISTRATION_CODE to secrets."
    if not hmac.compare_digest(code.strip(), expected_code):
        return False, "Invalid registration code."
    initialize_user_table()
    connection = sqlite3.connect(AUTH_DATABASE)
    try:
        connection.execute(
            "INSERT INTO shopkeepers (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
            (username, hash_password(password), "staff", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        connection.commit()
    except sqlite3.IntegrityError:
        return False, "That username is already registered."
    finally:
        connection.close()
    return True, "Registration successful. You can now log in."


def authenticate(username: str, password: str) -> bool:
    """Authenticate an active shopkeeper account from SQLite."""
    initialize_user_table()
    connection = sqlite3.connect(AUTH_DATABASE)
    try:
        row = connection.execute("SELECT password_hash, role FROM shopkeepers WHERE username = ? AND active = 1", (username.strip(),)).fetchone()
    finally:
        connection.close()
    if row is None or not verify_password(password, row[0]):
        return False
    st.session_state.authenticated_user = username.strip()
    st.session_state.user_role = row[1]
    return True


def render_login() -> bool:
    """Render registration and login tabs and return whether access is authenticated."""
    if st.session_state.get("authenticated_user"):
        return True
    st.title("Shopkeeper Access")
    st.caption("Register first, then log in to view customer and pledge details.")
    register_tab, login_tab = st.tabs(["Register", "Log in"])
    with register_tab:
        with st.form("registration_form"):
            username = st.text_input("Choose username")
            password = st.text_input("Choose password", type="password")
            confirmation = st.text_input("Confirm password", type="password")
            code = st.text_input("Private registration code", type="password")
            submitted = st.form_submit_button("Register", type="primary")
        if submitted:
            success, message = register_user(username, password, confirmation, code)
            (st.success if success else st.error)(message)
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", type="primary")
        if submitted:
            if authenticate(username, password):
                st.rerun()
            st.error("Incorrect username or password.")
    return False


def render_logout() -> None:
    """Display the current shopkeeper and provide a logout control."""
    username = st.session_state.get("authenticated_user", "")
    role = st.session_state.get("user_role", "staff")
    with st.sidebar:
        st.caption(f"Signed in: {username} ({role})")
        if st.button("Log out"):
            st.session_state.pop("authenticated_user", None)
            st.session_state.pop("user_role", None)
            st.rerun()
