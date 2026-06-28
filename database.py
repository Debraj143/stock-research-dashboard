"""
database.py
Stage 1 — SQLite watchlist layer.

Handles all database operations for the stock dashboard:
- Creating the schema (watchlist + alert_history tables)
- Adding / removing / updating stocks
- Fetching the current watchlist
- Logging fired alerts for history

This file has zero dependency on yfinance or Streamlit — it's a pure
data-access layer. Stage 2 (signal engine) and the dashboard will both
import from here.
"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager

DB_PATH = "stocks.db"


@contextmanager
def get_connection():
    """Context manager so every caller gets a connection that's
    always closed properly, even if an error happens mid-query."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Creates the tables if they don't already exist.
    Safe to call every time the app starts."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT NOT NULL UNIQUE,
                name        TEXT,
                above       REAL,
                below       REAL,
                added_on    TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker      TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                message     TEXT NOT NULL,
                price       REAL,
                triggered_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS annual_reports (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker        TEXT NOT NULL UNIQUE,
                pdf_url       TEXT NOT NULL,
                pdf_local_path TEXT,
                summary       TEXT,
                summarized_at TEXT,
                report_year   TEXT
            )
        """)


# ---------- Watchlist operations ----------

def add_stock(ticker: str, name: str = None, above: float = None, below: float = None):
    """Add a stock to the watchlist. Ticker should be NSE format, e.g. 'RELIANCE.NS'."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        conn.execute(
            """INSERT OR IGNORE INTO watchlist (ticker, name, above, below, added_on)
               VALUES (?, ?, ?, ?, ?)""",
            (ticker, name or ticker.replace(".NS", ""), above, below, datetime.now().isoformat())
        )


def remove_stock(ticker: str):
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        conn.execute("DELETE FROM watchlist WHERE ticker = ?", (ticker,))


def update_thresholds(ticker: str, above: float = None, below: float = None):
    """Update alert thresholds for an existing stock."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        conn.execute(
            "UPDATE watchlist SET above = ?, below = ? WHERE ticker = ?",
            (above, below, ticker)
        )


def get_watchlist():
    """Returns the full watchlist as a list of dicts."""
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM watchlist ORDER BY ticker").fetchall()
        return [dict(row) for row in rows]


def get_tickers():
    """Just the ticker symbols — useful for bulk price fetching."""
    with get_connection() as conn:
        rows = conn.execute("SELECT ticker FROM watchlist").fetchall()
        return [row["ticker"] for row in rows]


# ---------- Alert history operations ----------

def log_alert(ticker: str, signal_type: str, message: str, price: float):
    """Records a fired alert so it shows up in alert history."""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO alert_history (ticker, signal_type, message, price, triggered_at)
               VALUES (?, ?, ?, ?, ?)""",
            (ticker, signal_type, message, price, datetime.now().isoformat())
        )


def get_recent_alerts(limit: int = 50):
    """Returns most recent alerts, newest first."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM alert_history ORDER BY triggered_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]


def already_alerted_today(ticker: str, signal_type: str) -> bool:
    """Prevents alert spam — checks if this exact signal already
    fired for this stock today."""
    today = datetime.now().date().isoformat()
    with get_connection() as conn:
        row = conn.execute(
            """SELECT 1 FROM alert_history
               WHERE ticker = ? AND signal_type = ? AND triggered_at LIKE ?""",
            (ticker, signal_type, f"{today}%")
        ).fetchone()
        return row is not None


# ---------- Annual report operations ----------

def save_report_url(ticker: str, pdf_url: str, report_year: str = None):
    """Registers the PDF URL for a company's annual report.
    Call this once per company (manually curated URLs)."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO annual_reports (ticker, pdf_url, report_year)
               VALUES (?, ?, ?)
               ON CONFLICT(ticker) DO UPDATE SET pdf_url = ?, report_year = ?""",
            (ticker, pdf_url, report_year, pdf_url, report_year)
        )


def save_summary(ticker: str, summary: str, pdf_local_path: str = None):
    """Caches the generated summary so we don't re-call Gemini every page load."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        conn.execute(
            """UPDATE annual_reports
               SET summary = ?, summarized_at = ?, pdf_local_path = COALESCE(?, pdf_local_path)
               WHERE ticker = ?""",
            (summary, datetime.now().isoformat(), pdf_local_path, ticker)
        )


def get_report(ticker: str):
    """Returns the report record (url, cached summary, etc.) for a ticker, or None."""
    ticker = ticker.upper().strip()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM annual_reports WHERE ticker = ?", (ticker,)
        ).fetchone()
        return dict(row) if row else None


if __name__ == "__main__":
    # Quick manual test — run `python database.py` to sanity check everything works
    init_db()
    print("Database initialized.")

    add_stock("RELIANCE.NS", "RELIANCE", above=3000, below=1200)
    add_stock("TCS.NS", "TCS", above=4200, below=2000)
    add_stock("INFY.NS", "INFY", above=1800, below=1300)

    print("\nCurrent watchlist:")
    for stock in get_watchlist():
        print(f"  {stock['ticker']:15} above={stock['above']:<8} below={stock['below']}")

    log_alert("RELIANCE.NS", "price_below", "RELIANCE dropped below 1200", 1190.50)

    print("\nRecent alerts:")
    for alert in get_recent_alerts():
        print(f"  [{alert['triggered_at']}] {alert['message']}")

    print(f"\nAlready alerted today (RELIANCE, price_below)? {already_alerted_today('RELIANCE.NS', 'price_below')}")
    print(f"Already alerted today (TCS, price_below)? {already_alerted_today('TCS.NS', 'price_below')}")
