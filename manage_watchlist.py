"""
manage_watchlist.py
Simple command-line tool to manage your stock watchlist without
touching code every time. Run this whenever you want to add, remove,
or view stocks.

Usage:
    python manage_watchlist.py add RELIANCE.NS 3000 1200
    python manage_watchlist.py remove RELIANCE.NS
    python manage_watchlist.py list
"""

import sys
import database as db


def main():
    db.init_db()

    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1].lower()

    if command == "add":
        if len(sys.argv) < 3:
            print("Usage: python manage_watchlist.py add TICKER [above] [below]")
            return
        ticker = sys.argv[2]
        above = float(sys.argv[3]) if len(sys.argv) > 3 else None
        below = float(sys.argv[4]) if len(sys.argv) > 4 else None
        db.add_stock(ticker, above=above, below=below)
        print(f"Added {ticker.upper()} (above={above}, below={below})")

    elif command == "remove":
        if len(sys.argv) < 3:
            print("Usage: python manage_watchlist.py remove TICKER")
            return
        ticker = sys.argv[2]
        db.remove_stock(ticker)
        print(f"Removed {ticker.upper()}")

    elif command == "list":
        stocks = db.get_watchlist()
        if not stocks:
            print("Watchlist is empty. Add stocks with: python manage_watchlist.py add TICKER")
            return
        print(f"\n{'Ticker':<15}{'Above':<10}{'Below':<10}{'Added On'}")
        print("-" * 55)
        for s in stocks:
            above = s['above'] if s['above'] is not None else "-"
            below = s['below'] if s['below'] is not None else "-"
            print(f"{s['ticker']:<15}{str(above):<10}{str(below):<10}{s['added_on'][:10]}")
        print(f"\nTotal: {len(stocks)} stocks")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)


if __name__ == "__main__":
    main()
