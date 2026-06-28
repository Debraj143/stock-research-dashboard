"""
seed_watchlist.py
One-time script to populate your database with your 20 target companies.

Run this once:
    python seed_watchlist.py

Safe to run multiple times — uses INSERT OR IGNORE under the hood,
so it won't create duplicates.
"""

import database as db

# Your 20 companies. Thresholds are left as None for now — you can set
# real above/below alert levels later via manage_watchlist.py once
# Stage 2 (signal engine) is built. For now this just seeds the list
# so the news/research dashboard has companies to show.
COMPANIES = [
    ("RELIANCE.NS",   "Reliance Industries"),
    ("HDFCBANK.NS",   "HDFC Bank"),
    ("BHARTIARTL.NS", "Bharti Airtel"),
    ("ICICIBANK.NS",  "ICICI Bank"),
    ("SBIN.NS",       "State Bank of India"),
    ("TCS.NS",        "Tata Consultancy Services"),
    ("BAJFINANCE.NS", "Bajaj Finance"),
    ("LT.NS",         "Larsen & Toubro"),
    ("LICI.NS",       "Life Insurance Corporation of India"),
    ("HINDUNILVR.NS", "Hindustan Unilever"),
    ("INFY.NS",       "Infosys"),
    ("ITC.NS",        "ITC"),
    ("KOTAKBANK.NS",  "Kotak Mahindra Bank"),
    ("HCLTECH.NS",    "HCL Technologies"),
    ("AXISBANK.NS",   "Axis Bank"),
    ("MARUTI.NS",     "Maruti Suzuki India"),
    ("TITAN.NS",      "Titan Company"),
    ("SUNPHARMA.NS",  "Sun Pharmaceutical Industries"),
    ("ULTRACEMCO.NS", "UltraTech Cement"),
    ("M&M.NS",        "Mahindra & Mahindra"),
]

if __name__ == "__main__":
    db.init_db()
    for ticker, name in COMPANIES:
        db.add_stock(ticker, name=name)
        print(f"Added: {name} ({ticker})")

    print(f"\nDone. {len(COMPANIES)} companies seeded.")
    print("Run 'python manage_watchlist.py list' to verify.")
