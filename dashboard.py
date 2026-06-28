"""
dashboard.py
Main Streamlit app — your stock research dashboard.

Run with:
    streamlit run dashboard.py

Current features (Stage 1 + News):
- Lists all companies in your watchlist (from SQLite)
- Click any company to see its news from the last 3 months

Run `python seed_watchlist.py` first if your database is empty.
"""

import streamlit as st
import database as db
from news import get_news_for_ticker, get_company_name
import annual_report
import segments as seg

st.set_page_config(
    page_title="Stock Research Dashboard",
    page_icon="📈",
    layout="wide",
)

db.init_db()


# Manually curated annual report PDF URLs. There's no API that can find
# these automatically — each company hosts its own report at a different
# URL, so these need to be found and added by hand as you go.
# Start with one (Reliance) for testing; add the other 19 as you find them.
ANNUAL_REPORT_URLS = {
    "RELIANCE.NS":   "https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=cc08294f-ec68-4f15-aaa4-c14a3c4bdfb2.pdf",
    "HDFCBANK.NS":   "https://www.bseindia.com/xml-data/corpfiling/AttachHis/411e22d2-0720-4cec-b659-9ccd639f0f1a.pdf",
    "BHARTIARTL.NS": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/c2194c0b-bec7-42ba-9675-afdf7a9e7e9c.pdf",
    "ICICIBANK.NS":  "https://www.bseindia.com/xml-data/corpfiling/AttachHis/d80c4401-bed9-4aa4-b532-00255b963376.pdf",
    "SBIN.NS":       "https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=faa17496-838f-432d-a39f-32d82156799c.pdf",
    "TCS.NS":        "https://www.bseindia.com/xml-data/corpfiling/AttachHis/ad42e748-d73c-4c79-8c52-bcf1b1399bc1.pdf",
    "BAJFINANCE.NS": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/0670e08f-bc55-4155-9cbe-89e4637b3b05.pdf",
    "LT.NS":         "https://www.bseindia.com/xml-data/corpfiling/AttachHis/825f9859-e7f2-4e90-8583-01a38850f795.pdf",
    "LICI.NS":       "https://www.bseindia.com/xml-data/corpfiling/AttachHis/7eecfc8a-4aeb-4c89-bdec-5b8ed7193156.pdf",
    "HINDUNILVR.NS": "https://www.hul.co.in/files/annual-report-2025-26.pdf",
    "INFY.NS":       "https://www.bseindia.com/stockinfo/AnnPdfOpen.aspx?Pname=19dd605c-2b6b-4084-8dca-9d578a3eb7a0.pdf",
    "ITC.NS":        "https://www.bseindia.com/xml-data/corpfiling/AttachHis/8ba4a189-5fd2-4851-af6f-ec365f7edea2.pdf",
    "KOTAKBANK.NS":  "https://www.bseindia.com/xml-data/corpfiling/AttachHis/16d6f679-14fe-444e-8ff6-8ee3bd68bd08.pdf",
    "HCLTECH.NS":    "https://www.bseindia.com/xml-data/corpfiling/AttachHis/ddf08009-d43c-4949-b149-643731211e1d.pdf",
    "AXISBANK.NS":   "https://www.bseindia.com/xml-data/corpfiling/AttachHis/9144823a-85ee-4db6-a75f-fba16387ce0a.pdf",
    "MARUTI.NS":     "https://www.bseindia.com/xml-data/corpfiling/AttachHis/b6b3feef-628a-443c-9e63-665a5e057547.pdf",
    "TITAN.NS":      "https://www.bseindia.com/xml-data/corpfiling/AttachHis/92f76ec9-cc9b-4534-ad82-2cbd920a55b7.pdf",
    "SUNPHARMA.NS":  "https://www.bseindia.com/xml-data/corpfiling/AttachHis/511405ab-48e8-4d89-84af-aaa2e083e816.pdf",
    "ULTRACEMCO.NS": "https://www.bseindia.com/xml-data/corpfiling/AttachHis/d7e47648-aef8-427b-b56e-b442f5e5ac3d.pdf",
    "M&M.NS":        "https://www.bseindia.com/xml-data/corpfiling/AttachHis/525dfa1c-b55e-4f2e-9367-66d688d0bd0c.pdf",
}


def format_published_date(article):
    """Returns a clean, human-readable date string for an article."""
    dt = article.get("published_dt")
    if dt:
        return dt.strftime("%d %b %Y, %I:%M %p")
    return article.get("published", "Date unknown")


def render_news_panel(ticker: str, company_name: str):
    """Renders the news section for a selected company."""
    st.subheader(f"📰 News — {company_name} (last 3 months)")

    with st.spinner(f"Fetching news for {company_name}..."):
        articles = get_news_for_ticker(ticker, months=3)

    if not articles:
        st.info(
            "No news found in the last 3 months. This can happen for "
            "lower-coverage companies, or if Google News RSS is temporarily "
            "rate-limiting requests — try again in a moment."
        )
        return

    st.caption(f"Found {len(articles)} articles")

    for article in articles:
        with st.container(border=True):
            st.markdown(f"**[{article['title']}]({article['link']})**")
            meta_col1, meta_col2 = st.columns([1, 1])
            with meta_col1:
                if article["source"]:
                    st.caption(f"📌 {article['source']}")
            with meta_col2:
                st.caption(f"🕒 {format_published_date(article)}")


def render_overview_panel(ticker: str, company_name: str):
    """Renders the annual report summary + download section."""
    pdf_url = ANNUAL_REPORT_URLS.get(ticker)

    if not pdf_url:
        st.info(
            f"Annual report URL not yet added for {company_name}. "
            "This needs to be manually sourced from the company's investor "
            "relations page and added to ANNUAL_REPORT_URLS in dashboard.py."
        )
        return

    existing = db.get_report(ticker)
    has_cached_summary = existing and existing.get("summary")

    col1, col2 = st.columns([3, 1])
    with col1:
        if has_cached_summary:
            st.caption(f"Summary generated: {existing['summarized_at'][:10]}")
    with col2:
        refresh = st.button("🔄 Regenerate summary", use_container_width=True)

    if not has_cached_summary or refresh:
        with st.spinner(
            f"Downloading and summarizing {company_name}'s annual report... "
            "this can take 30-60 seconds for a long report."
        ):
            try:
                result = annual_report.get_or_create_summary(
                    ticker, pdf_url, force_refresh=refresh
                )
            except Exception as e:
                st.error(f"Couldn't generate summary: {e}")
                return
    else:
        result = {
            "summary": existing["summary"],
            "pdf_local_path": existing["pdf_local_path"],
        }

    # PDF download button
    if result.get("pdf_local_path"):
        try:
            with open(result["pdf_local_path"], "rb") as f:
                st.download_button(
                    label="📄 Download original Annual Report (PDF)",
                    data=f.read(),
                    file_name=f"{company_name.replace(' ', '_')}_Annual_Report.pdf",
                    mime="application/pdf",
                )
        except FileNotFoundError:
            st.warning("PDF file not found locally — try regenerating the summary.")

    st.markdown("---")
    st.markdown(result["summary"])


def render_segments_panel(ticker: str, company_name: str):
    """Renders two side-by-side pie charts: Revenue and Operating Income by segment."""
    st.subheader(f"📊 Segment Breakdown — {company_name}")

    fig = seg.render_segment_charts(ticker)

    if fig is None:
        st.info(
            f"Segment data not yet added for {company_name}. "
            "Data is hardcoded annually from MarketScreener — "
            "it will be added progressively for all 20 companies."
        )
        return

    data = seg.get_company_segments(ticker)
    st.caption(
        f"Source: MarketScreener  |  Year: {data.get('year', 'N/A')}  |  "
        f"Currency: {data.get('currency', 'INR Cr')}  |  "
        "Note: Inter-segment eliminations and negative entries excluded from charts."
    )

    st.plotly_chart(fig, use_container_width=True)

    # Summary metrics below the charts
    revenue = {k: v for k, v in data.get("revenue", {}).items() if v > 0}
    op_income = {k: v for k, v in data.get("operating_income", {}).items() if v > 0}

    if revenue and op_income:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Revenue breakdown**")
            rev_total = sum(revenue.values())
            for seg_name, val in sorted(revenue.items(), key=lambda x: -x[1]):
                pct = val / rev_total * 100
                st.markdown(f"- {seg_name}: ₹{val:,.0f} Cr &nbsp;&nbsp; `{pct:.1f}%`")
        with col2:
            st.markdown("**Operating Income breakdown**")
            oi_total = sum(op_income.values())
            for seg_name, val in sorted(op_income.items(), key=lambda x: -x[1]):
                pct = val / oi_total * 100
                st.markdown(f"- {seg_name}: ₹{val:,.0f} Cr &nbsp;&nbsp; `{pct:.1f}%`")


def main():
    st.title("📈 Stock Research Dashboard")
    st.caption("Equity research portfolio — proof of work")

    watchlist = db.get_watchlist()

    if not watchlist:
        st.warning(
            "Your watchlist is empty. Run `python seed_watchlist.py` in your "
            "terminal first, then refresh this page."
        )
        return

    # Sidebar: company selector
    st.sidebar.header("Companies")
    company_options = {
        f"{stock['name']} ({stock['ticker']})": stock['ticker']
        for stock in watchlist
    }

    selected_label = st.sidebar.radio(
        "Select a company",
        options=list(company_options.keys()),
        label_visibility="collapsed",
    )
    selected_ticker = company_options[selected_label]
    selected_name = next(s['name'] for s in watchlist if s['ticker'] == selected_ticker)

    st.sidebar.markdown("---")
    st.sidebar.caption(f"Tracking {len(watchlist)} companies")

    # Main panel
    st.header(f"{selected_name}")
    st.caption(f"Ticker: `{selected_ticker}`")

    tab_news, tab_overview, tab_segments = st.tabs(["📰 News", "ℹ️ Overview", "📊 Segments"])

    with tab_news:
        render_news_panel(selected_ticker, selected_name)

    with tab_overview:
        render_overview_panel(selected_ticker, selected_name)

    with tab_segments:
        render_segments_panel(selected_ticker, selected_name)


if __name__ == "__main__":
    main()
