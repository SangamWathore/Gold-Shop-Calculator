"""Live gold-price retrieval with caching and safe environment configuration."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

TROY_OUNCE_IN_GRAMS = 31.1034768


def currencyapi_to_inr_per_gram(xau_per_inr: float) -> float:
    """Convert currencyapi's XAU-per-INR rate into INR per gram of 24K gold."""
    if xau_per_inr <= 0:
        raise ValueError("currencyapi returned a non-positive XAU rate.")
    price_per_troy_ounce = 1 / xau_per_inr
    return price_per_troy_ounce / TROY_OUNCE_IN_GRAMS


@st.cache_data(ttl=300, show_spinner=False)
def get_live_price() -> tuple[float, str]:
    """Fetch currencyapi's latest 24K INR-per-gram price and its timestamp."""
    api_key = os.getenv("CURRENCY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("CURRENCY_API_KEY is not configured in .env")
    query = urlencode({"base_currency": "INR", "currencies": "XAU"})
    request = Request(
        f"https://api.currencyapi.com/v3/latest?{query}",
        headers={"apikey": api_key, "User-Agent": "vaibhav-gold-billing/1.0"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
        raise RuntimeError(f"Unable to fetch live gold price: {error}") from error
    try:
        xau_per_inr = float(payload["data"]["XAU"]["value"])
        price = currencyapi_to_inr_per_gram(xau_per_inr)
    except (KeyError, TypeError, ValueError) as error:
        message = payload.get("message", "invalid response") if isinstance(payload, dict) else "invalid response"
        raise RuntimeError(f"currencyapi returned an invalid gold rate ({message}).") from error
    timestamp = payload.get("meta", {}).get("last_updated_at") or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return price, str(timestamp)


def configured_gst_rate() -> float:
    """Read the GST percentage from .env, defaulting to 3% when absent or invalid."""
    try:
        rate = float(os.getenv("GST_RATE", "3"))
    except ValueError:
        rate = 3.0
    return rate if 0 <= rate <= 100 else 3.0
