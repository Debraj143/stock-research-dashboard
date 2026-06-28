"""
news.py
Fetches news headlines for a company using Google News RSS, filtered
to the last N months (default 3).

No API key needed — Google News RSS is a free public feed.

Usage:
    from news import get_news_for_ticker
    articles = get_news_for_ticker("RELIANCE.NS", months=3)
"""

import feedparser
import urllib.parse
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime


def get_news(company_name: str, months: int = 3, limit: int = 60):
    """
    Fetches news for a company by name, filtered to the last `months` months.

    Google News RSS doesn't support a date-range parameter directly, so
    we fetch a generous batch (sorted newest-first by Google) and filter
    by the published date ourselves. If a company has light news flow,
    fewer than `limit` articles may come back within the window — that's
    expected, not a bug.

    Returns a list of dicts: [{title, link, published, published_dt, source}, ...]
    sorted newest first.
    """
    query = urllib.parse.quote(f"{company_name} stock")
    url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"

    feed = feedparser.parse(url)
    cutoff = datetime.now(tz=None).astimezone() - timedelta(days=months * 30)

    articles = []
    for entry in feed.entries:
        title = entry.title
        source = ""
        if " - " in title:
            title, source = title.rsplit(" - ", 1)

        # Parse the published date so we can filter by it
        published_dt = None
        if entry.get("published"):
            try:
                published_dt = parsedate_to_datetime(entry.published)
            except (ValueError, TypeError):
                published_dt = None

        # Skip articles outside our window (if we can't parse the date,
        # we keep the article rather than silently dropping it)
        if published_dt is not None and published_dt < cutoff:
            continue

        articles.append({
            "title": title.strip(),
            "source": source.strip(),
            "link": entry.link,
            "published": entry.get("published", ""),
            "published_dt": published_dt,
        })

        if len(articles) >= limit:
            break

    # Sort newest first (Google usually already does this, but don't rely on it)
    articles.sort(key=lambda a: a["published_dt"] or datetime.min.replace(tzinfo=None), reverse=True)

    return articles


# Your 20-company watchlist mapped to clean, search-friendly company names.
TICKER_TO_NAME = {
    "RELIANCE.NS":  "Reliance Industries",
    "HDFCBANK.NS":  "HDFC Bank",
    "BHARTIARTL.NS": "Bharti Airtel",
    "ICICIBANK.NS": "ICICI Bank",
    "SBIN.NS":      "State Bank of India",
    "TCS.NS":       "Tata Consultancy Services",
    "BAJFINANCE.NS": "Bajaj Finance",
    "LT.NS":        "Larsen & Toubro",
    "LICI.NS":      "Life Insurance Corporation of India",
    "HINDUNILVR.NS": "Hindustan Unilever",
    "INFY.NS":      "Infosys",
    "ITC.NS":       "ITC",
    "KOTAKBANK.NS": "Kotak Mahindra Bank",
    "HCLTECH.NS":   "HCL Technologies",
    "AXISBANK.NS":  "Axis Bank",
    "MARUTI.NS":    "Maruti Suzuki India",
    "TITAN.NS":     "Titan Company",
    "SUNPHARMA.NS": "Sun Pharmaceutical Industries",
    "ULTRACEMCO.NS": "UltraTech Cement",
    "M&M.NS":       "Mahindra & Mahindra",
}


def get_company_name(ticker: str) -> str:
    """
    Resolves a ticker to its full company name.
    Checks the manual mapping first, then falls back to yfinance's own
    metadata so this works for ANY NSE ticker, not just the 20 above.
    """
    ticker = ticker.upper()
    if ticker in TICKER_TO_NAME:
        return TICKER_TO_NAME[ticker]

    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        name = info.get("longName") or info.get("shortName")
        if name:
            return name
    except Exception:
        pass

    return ticker.replace(".NS", "")


def get_news_for_ticker(ticker: str, months: int = 3, limit: int = 60):
    """Convenience wrapper — pass a ticker, automatically resolves to
    company name for better search results."""
    company_name = get_company_name(ticker)
    return get_news(company_name, months=months, limit=limit)


if __name__ == "__main__":
    # Quick manual test across a couple of companies
    for ticker in ["RELIANCE.NS", "TITAN.NS"]:
        print(f"\n{'='*60}\nNews for {get_company_name(ticker)} ({ticker}) — last 3 months\n{'='*60}")
        articles = get_news_for_ticker(ticker)

        if not articles:
            print("No articles found in this window.")
        else:
            for a in articles:
                print(f"• {a['title']}")
                print(f"  {a['source']} | {a['published']}")
                print(f"  {a['link']}\n")
