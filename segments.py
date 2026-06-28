"""
segments.py
Two stacked donut pie charts for each company:
  Top    → Revenue by segment
  Bottom → Operating Income by segment

Rules:
  - Same segment = same colour across BOTH charts always
  - Labels auto (inside large slices, outside small ones) — all white
  - No legend
  - Titles below each chart in white
  - Total below each title in dimmer white
  - Transparent background
"""

import json
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots

SEGMENTS_FILE = os.path.join(os.path.dirname(__file__), "segments.json")

PALETTE = [
    "#2E86AB",  # steel blue
    "#E84855",  # red
    "#3BB273",  # green
    "#F4A261",  # orange
    "#9B5DE5",  # purple
    "#F7B731",  # yellow
    "#8C8C8C",  # grey
    "#00B4D8",  # cyan
    "#D62828",  # dark red
    "#4CAF50",  # lime green
    "#FF6B9D",  # pink
    "#C77DFF",  # lavender
]


def _load():
    if not os.path.exists(SEGMENTS_FILE):
        return {}
    with open(SEGMENTS_FILE) as f:
        return json.load(f)


def get_company_segments(ticker: str):
    return _load().get(ticker.upper())


def _colour_map(all_segment_names: list) -> dict:
    return {
        name: PALETTE[i % len(PALETTE)]
        for i, name in enumerate(sorted(all_segment_names))
    }


def render_segment_charts(ticker: str):
    data = get_company_segments(ticker)
    if not data:
        return None

    year     = data.get("year", "")
    currency = data.get("currency", "INR Cr")

    revenue   = {k: v for k, v in data.get("revenue", {}).items() if v > 0}
    op_income = {k: v for k, v in data.get("operating_income", {}).items() if v > 0}

    if not revenue and not op_income:
        return None

    all_segments = set(revenue.keys()) | set(op_income.keys())
    cmap = _colour_map(all_segments)

    # 2 rows, 1 col — stacked vertically
    fig = make_subplots(
        rows=2, cols=1,
        specs=[[{"type": "pie"}], [{"type": "pie"}]],
        vertical_spacing=0.12,
    )

    # ── Top chart: Revenue ───────────────────────────────────────────
    if revenue:
        rev_labels = list(revenue.keys())
        rev_values = list(revenue.values())

        fig.add_trace(go.Pie(
            name="Revenue",
            labels=rev_labels,
            values=rev_values,
            marker=dict(
                colors=[cmap[s] for s in rev_labels],
                line=dict(color="#FFFFFF", width=2),
            ),
            hole=0.38,
            textinfo="label+percent",
            textposition="auto",
            textfont=dict(size=11, color="#FFFFFF"),
            outsidetextfont=dict(size=11, color="#FFFFFF"),
            insidetextfont=dict(size=11, color="#FFFFFF"),
            insidetextorientation="radial",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Revenue: ₹%{value:,.0f} " + currency + "<br>"
                "Share: %{percent}<extra></extra>"
            ),
            showlegend=False,
            domain={"row": 0, "column": 0},
        ), row=1, col=1)

    # ── Bottom chart: Operating Income ───────────────────────────────
    if op_income:
        oi_labels = list(op_income.keys())
        oi_values = list(op_income.values())

        fig.add_trace(go.Pie(
            name="Operating Income",
            labels=oi_labels,
            values=oi_values,
            marker=dict(
                colors=[cmap[s] for s in oi_labels],
                line=dict(color="#FFFFFF", width=2),
            ),
            hole=0.38,
            textinfo="label+percent",
            textposition="auto",
            textfont=dict(size=11, color="#FFFFFF"),
            outsidetextfont=dict(size=11, color="#FFFFFF"),
            insidetextfont=dict(size=11, color="#FFFFFF"),
            insidetextorientation="radial",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "Operating Income: ₹%{value:,.0f} " + currency + "<br>"
                "Share: %{percent}<extra></extra>"
            ),
            showlegend=False,
            domain={"row": 1, "column": 0},
        ), row=2, col=1)

    rev_total = sum(revenue.values()) if revenue else 0
    oi_total  = sum(op_income.values()) if op_income else 0

    fig.update_layout(
        height=1000,
        margin=dict(t=20, b=80, l=60, r=60),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=13, color="#FFFFFF"),
        showlegend=False,
        annotations=[
            # Title below top chart
            dict(
                text="<b>REVENUE</b>",
                x=0.5, y=0.52,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=15, color="#FFFFFF"),
                xanchor="center",
            ),
            # Total below REVENUE title
            dict(
                text=f"Total: ₹{rev_total:,.0f} {currency}" if rev_total else "",
                x=0.5, y=0.495,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=12, color="#AAAAAA"),
                xanchor="center",
            ),
            # Title below bottom chart
            dict(
                text="<b>OPERATING INCOME</b>",
                x=0.5, y=-0.04,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=15, color="#FFFFFF"),
                xanchor="center",
            ),
            # Total below OPERATING INCOME title
            dict(
                text=f"Total: ₹{oi_total:,.0f} {currency}" if oi_total else "",
                x=0.5, y=-0.075,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=12, color="#AAAAAA"),
                xanchor="center",
            ),
        ],
    )

    return fig
