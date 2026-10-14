# Gold Jewellery Billing System

A Streamlit billing application for manually entered gold prices.

 ## Run

 ```powershell
uv sync
uv run streamlit run first.py
 ```

The app supports multiple items per invoice, live currencyapi gold pricing, 24K/22K/18K/14K purity, weight conversion, making charges, wastage, stone charges, GST, validation, TXT/CSV/PDF receipts, SQLite invoice history, and comparison charts.

Gold prices are intentionally entered manually. Live pricing will be added later.

Run tests with:

```powershell
uv run pytest
```
