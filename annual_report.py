"""
annual_report.py
Downloads a company's annual report PDF and generates a structured,
analyst-style summary using the Gemini API.

SETUP REQUIRED:
1. Get a free Gemini API key: https://aistudio.google.com/apikey
2. Set it as an environment variable before running:
   Windows (cmd):       set GEMINI_API_KEY=your_key_here
   Windows (PowerShell): $env:GEMINI_API_KEY="your_key_here"
   Mac/Linux:            export GEMINI_API_KEY=your_key_here

   Or create a file called .env in this folder with:
       GEMINI_API_KEY=your_key_here

Usage:
    from annual_report import get_or_create_summary
    result = get_or_create_summary("RELIANCE.NS", pdf_url="https://...")
"""

import os
import re
import requests
import pdfplumber
from google import genai
import database as db

REPORTS_DIR = "annual_reports_pdfs"
os.makedirs(REPORTS_DIR, exist_ok=True)

# Load API key from environment (or a local .env file as a fallback)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY and os.path.exists(".env"):
    with open(".env") as f:
        for line in f:
            if line.strip().startswith("GEMINI_API_KEY"):
                GEMINI_API_KEY = line.strip().split("=", 1)[1].strip()

_client = None


def get_client():
    """Lazily creates the Gemini client so import doesn't fail if the
    key isn't set yet (lets the dashboard show a friendly error instead
    of crashing on import)."""
    global _client
    if _client is None:
        if not GEMINI_API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Get a free key at "
                "https://aistudio.google.com/apikey and set it as an "
                "environment variable before running."
            )
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


SUMMARY_PROMPT = """You are an equity research analyst writing a structured briefing
for another analyst who has NOT read the full annual report. Read the annual report
text below and produce a clear, well-organized summary using Markdown formatting
with the EXACT subheadings listed below. Be specific — use real numbers, segment
names, and figures from the report wherever they appear. Do not pad with generic
statements. If a section's information genuinely isn't in the provided text, write
"Not disclosed in the provided excerpt" under that heading rather than guessing.

Use these subheadings, in this order:

## Business Overview
What the company does, its main segments/divisions, and competitive position.

## Key Financial Highlights
Revenue, profit (PAT), EBITDA margin, and how they changed vs. the prior year.
Include actual figures if present.

## Revenue by Segment
Breakdown of revenue by business segment or division, with approximate
percentages or figures if disclosed.

## Management Commentary & Strategic Outlook
What management said about future direction, growth plans, or strategic priorities.

## Key Risks & Challenges
Risk factors, headwinds, or challenges explicitly mentioned in the report.

## Capex & Investments
Major capital expenditure, expansions, or investments disclosed.

## Debt & Balance Sheet Position
Net debt, debt-to-equity, or balance sheet health commentary if present.

## Notable One-Time Items
Any one-off events — acquisitions, divestments, write-offs, litigation, etc.

Keep each section concise (3-6 bullet points or short paragraphs). This is for
someone who needs to understand the company quickly, not read the full report.

ANNUAL REPORT TEXT:
{report_text}
"""


def download_pdf(ticker: str, pdf_url: str) -> str:
    """Downloads the PDF to local disk, returns the local file path.
    Skips re-downloading if already present."""
    ticker = ticker.upper().strip()
    local_path = os.path.join(REPORTS_DIR, f"{ticker.replace('.', '_')}.pdf")

    if os.path.exists(local_path):
        return local_path

    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(pdf_url, headers=headers, timeout=60)
    response.raise_for_status()

    with open(local_path, "wb") as f:
        f.write(response.content)

    return local_path


def extract_text_from_pdf(pdf_path: str, max_pages: int = 120) -> str:
    """
    Extracts text from the PDF. Annual reports are long (150-300 pages),
    so we cap how many pages we read to keep this fast and within
    Gemini's context limits. The first ~120 pages of an Indian annual
    report typically cover everything an analyst needs (business overview,
    MD&A, financials) — the back half is usually notes, schedules, and
    boilerplate legal/compliance text.
    """
    text_chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        pages_to_read = min(total_pages, max_pages)

        for i in range(pages_to_read):
            page_text = pdf.pages[i].extract_text()
            if page_text:
                text_chunks.append(page_text)

    full_text = "\n\n".join(text_chunks)
    return full_text, total_pages, pages_to_read


def summarize_with_gemini(report_text: str) -> str:
    """Sends the extracted report text to Gemini and returns the
    structured Markdown summary."""
    client = get_client()

    # Gemini 2.0 Flash has a large context window, well suited for
    # long documents like annual reports, and is free-tier friendly.
    prompt = SUMMARY_PROMPT.format(report_text=report_text)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    return response.text


def get_or_create_summary(ticker: str, pdf_url: str, force_refresh: bool = False) -> dict:
    """
    Main entry point. Returns a dict with the summary and PDF path,
    using the cached version in the database if available, unless
    force_refresh=True.
    """
    ticker = ticker.upper().strip()
    db.init_db()

    existing = db.get_report(ticker)

    if existing and existing.get("summary") and not force_refresh:
        return {
            "summary": existing["summary"],
            "pdf_local_path": existing["pdf_local_path"],
            "from_cache": True,
            "summarized_at": existing["summarized_at"],
        }

    # Register the URL if not already saved
    db.save_report_url(ticker, pdf_url)

    # Step 1: Download
    local_path = download_pdf(ticker, pdf_url)

    # Step 2: Extract text
    report_text, total_pages, pages_read = extract_text_from_pdf(local_path)

    if not report_text.strip():
        raise RuntimeError(
            f"No extractable text found in the PDF for {ticker}. "
            "This report may be scanned images rather than real text, "
            "which would need OCR — let me know if you hit this."
        )

    # Step 3: Summarize
    summary = summarize_with_gemini(report_text)

    # Step 4: Cache
    db.save_summary(ticker, summary, pdf_local_path=local_path)

    return {
        "summary": summary,
        "pdf_local_path": local_path,
        "from_cache": False,
        "pages_read": pages_read,
        "total_pages": total_pages,
    }


if __name__ == "__main__":
    # Manual test — Reliance Industries
    TEST_TICKER = "RELIANCE.NS"
    TEST_PDF_URL = "https://www.ril.com/reports/RIL-Integrated-Annual-Report-2024-25.pdf"

    print(f"Testing pipeline for {TEST_TICKER}...")
    print(f"PDF URL: {TEST_PDF_URL}\n")

    try:
        result = get_or_create_summary(TEST_TICKER, TEST_PDF_URL)
        print(f"From cache: {result['from_cache']}")
        if not result["from_cache"]:
            print(f"Pages read: {result['pages_read']} of {result['total_pages']}")
        print("\n" + "=" * 60)
        print(result["summary"])
        print("=" * 60)
    except Exception as e:
        print(f"ERROR: {e}")
