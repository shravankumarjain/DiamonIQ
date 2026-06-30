"""
Diamond IQ — Shared Component System  v4.0
Theme: Professional Dark Analytics

Inspired by Baseball Savant, ESPN Stats & Info, Trackman dashboards.
Dark but fully readable. Every chart, card and text element is legible.
Designed to feel like a real MLB analytics tool, not a student project.

Key principle: data-forward dark theme where colour carries meaning,
not decoration. Green = good outcome. Red = bad. Gold = primary accent.
Everything on the dark background has sufficient contrast ratio (WCAG AA).

Palette:
  BG_PAGE  #13151A  deep navy-black page background
  BG_CARD  #1E2130  card surface — lighter than page
  BG_CARD2 #252A3A  elevated/hover card
  BG_INPUT #2A2F42  input fields
  BORDER   #2E3550  subtle card borders
  NAVY     #1D6FA4  mid-blue (replaces dominant navy — too dark on dark bg)
  GOLD     #F0B429  amber gold — primary accent
  BLUE_ACC #4B91D4  light blue — links, highlights
  GREEN    #22C55E  good / safe / above average
  RED      #EF4444  bad / danger / below average
  AMBER    #F59E0B  warning / caution
  TEXT_PRI #F1F5F9  near-white primary text
  TEXT_SEC #94A3B8  slate secondary text
  TEXT_MUT #475569  muted grey (for labels, captions)
  SIDEBAR  #0F172A  darkest — sidebar background
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Optional

# ── Palette ───────────────────────────────────────────────────────────────────
BG_PAGE  = "#13151A"
BG_CARD  = "#1E2130"
BG_CARD2 = "#252A3A"
BG_INPUT = "#2A2F42"
BORDER   = "#2E3550"
SIDEBAR  = "#0F172A"
NAVY     = "#1D6FA4"
GOLD     = "#F0B429"
BLUE_ACC = "#4B91D4"
GREEN    = "#22C55E"
RED      = "#EF4444"
AMBER    = "#F59E0B"
TEXT_PRI = "#F1F5F9"
TEXT_SEC = "#94A3B8"
TEXT_MUT = "#475569"
SURFACE  = BG_CARD2
MUTED    = TEXT_SEC

def rgba(hex_col: str, alpha: float) -> str:
    h = hex_col.lstrip("#")
    r, g, b = int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
    return f"rgba({r},{g},{b},{alpha})"

PITCH_COLORS = {
    "FF":    "#60A5FA",   # Four-seam   — bright blue
    "SI":    "#34D399",   # Sinker      — emerald
    "SL":    "#F87171",   # Slider      — coral red
    "CU":    "#C084FC",   # Curveball   — violet
    "CH":    "#FCD34D",   # Changeup    — yellow
    "FC":    "#22D3EE",   # Cutter      — cyan
    "FS":    "#FB923C",   # Splitter    — orange
    "ST":    "#F472B6",   # Sweeper     — pink
    "SV":    "#A78BFA",   # Slurve      — light purple
    "KC":    "#6EE7B7",   # Knuckle-cv  — mint
    "KN":    "#9CA3AF",   # Knuckleball — grey
    "PO":    "#4B5563",   # Pitchout    — dark grey
    "OTHER": "#6B7280",
}

# Full pitch name lookup — Statcast pitch_type code → readable name.
# Used by pitch_full_name() and the inline glossary badges on every page.
PITCH_NAMES = {
    "FF": "Four-seam fastball",
    "SI": "Sinker",
    "SL": "Slider",
    "CU": "Curveball",
    "CH": "Changeup",
    "FC": "Cutter",
    "FS": "Splitter",
    "ST": "Sweeper",
    "SV": "Slurve",
    "KC": "Knuckle curve",
    "KN": "Knuckleball",
    "PO": "Pitchout",
    "EP": "Eephus",
    "FA": "Fastball (generic)",
    "FO": "Forkball",
}

# Plain-English glossary for every metric abbreviation used across the platform.
# Powers the in-page "What do these mean?" reference panel.
METRIC_GLOSSARY = [
    ("CSW%",   "Called Strike + Whiff percentage",
     "Pitches resulting in a called strike or swing-and-miss, as a share of all pitches thrown. MLB average is roughly 28%. The single best one-number measure of pitch quality."),
    ("Whiff%", "Swing-and-miss percentage",
     "Of all swings taken at this pitch, the percentage that missed entirely. Higher means batters cannot make contact even when they try."),
    ("RV/100", "Run Value per 100 pitches",
     "Runs saved (negative) or given up (positive) per 100 pitches of this type, based on how the game state changed after each pitch. The same metric MLB front offices use to rank individual pitches. Zero is league average."),
    ("xwOBA",  "Expected Weighted On-Base Average",
     "Predicts the batting outcome from exit velocity and launch angle rather than what actually happened, removing luck and defence. Same scale as batting average roughly, .310 is league average, under .290 is strong pitching."),
    ("ACWR",   "Acute:Chronic Workload Ratio",
     "Recent pitch-count workload (last 7 days) divided by longer-term workload (last 28 days). The standard sports-science formula for spotting overuse before injury. 0.8 to 1.3 is the safe range."),
    ("EV",     "Exit Velocity",
     "How fast the ball leaves the bat off contact, in miles per hour. Higher exit velocity against a pitcher signals harder, more dangerous contact."),
    ("Barrel%", "Barrel percentage",
     "Share of batted balls hit with the ideal combination of exit velocity and launch angle for extra-base hits. A high Barrel% against a pitcher is a red flag."),
    ("BF",     "Batters Faced",
     "Total number of plate appearances against this pitcher in the selected season."),
    ("MLBAM ID", "MLB Advanced Media ID",
     "The unique identifier MLB uses for every player in its Statcast database. Used internally to fetch pitch-level data for the selected pitcher."),
]


def pitch_full_name(pt: str) -> str:
    """Return the readable pitch name for a Statcast pitch_type code, e.g. 'FF' -> 'Four-seam fastball'."""
    return PITCH_NAMES.get(str(pt).upper(), str(pt))


def pitch_badge(pt: str) -> str:
    """
    Small inline HTML badge showing a pitch code with its full name, colour-coded
    to match the pitch's chart colour. Use anywhere a bare pitch code like 'FF'
    or 'ST' appears in prose so the reader doesn't have to guess what it means.
    """
    name = pitch_full_name(pt)
    col  = pitch_color(pt)
    return (
        f'<span style="display:inline-flex;align-items:center;gap:5px;'
        f'background:{rgba(col, 0.12)};border:1px solid {rgba(col, 0.35)};'
        f'border-radius:5px;padding:1px 7px;font-size:0.82em;white-space:nowrap;">'
        f'<span style="width:7px;height:7px;border-radius:50%;background:{col};'
        f'display:inline-block;"></span>'
        f'<b style="color:{col};">{str(pt).upper()}</b>'
        f'<span style="color:{TEXT_SEC};">{name}</span>'
        f'</span>'
    )


def pitch_legend_strip(pitch_types) -> str:
    """
    Render a compact horizontal strip of pitch_badge() elements for every pitch
    type present on a page. Call once near the top of a page that uses raw
    pitch codes in charts, so the reader has the legend right there.
    """
    if pitch_types is None or len(pitch_types) == 0:
        return ""
    badges = "".join(
        f'<span style="margin-right:10px;margin-bottom:6px;display:inline-block;">'
        f'{pitch_badge(pt)}</span>'
        for pt in sorted(set(str(p).upper() for p in pitch_types))
    )
    return f'<div style="margin-bottom:14px;line-height:2;">{badges}</div>'

# ── CSS ───────────────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
/* ── Page background ── */
.stApp,
[data-testid="stAppViewContainer"],
section.main,
.main .block-container {
    background-color: #13151A !important;
}
[data-testid="stHeader"] {
    background-color: #13151A !important;
    border-bottom: 1px solid #2E3550 !important;
}
[data-testid="stToolbar"] { background: transparent !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div:first-child {
    background-color: #0F172A !important;
    border-right: 1px solid #2E3550 !important;
}

/* Sidebar text — white/light on dark */
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] .stCaption {
    color: #94A3B8 !important;
}

/* Selectbox labels in sidebar — gold */
[data-testid="stSidebar"] .stSelectbox > label,
[data-testid="stSidebar"] .stMultiSelect > label,
[data-testid="stSidebar"] .stSlider > label {
    color: #F0B429 !important;
    font-weight: 700 !important;
    font-size: 0.70rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
}

/* ══════════════════════════════════════════════════════════════════
   SELECTBOX — COMPLETE FIX
   Targets every element Streamlit uses for dropdowns.
   Closed box: dark bg, white text.
   Open list:  dark bg, white text, blue hover.
   ══════════════════════════════════════════════════════════════════ */

/* Closed select box */
[data-baseweb="select"] > div {
    background-color: #1E2A3A !important;
    border: 1px solid #4B91D4 !important;
}
/* All text/spans inside the closed box */
[data-baseweb="select"] div,
[data-baseweb="select"] span,
[data-baseweb="select"] input {
    color: #F1F5F9 !important;
    background-color: transparent !important;
}
[data-baseweb="select"] svg { fill: #94A3B8 !important; }

/* ── Open dropdown list — the white popup ── */
/* Streamlit renders the list in a portal using [data-baseweb="list"] inside a popover */
[data-baseweb="popover"] {
    background-color: #1E2130 !important;
}
[data-baseweb="popover"] > div,
[data-baseweb="popover"] > div > div {
    background-color: #1E2130 !important;
    border: 1px solid #2E3550 !important;
    border-radius: 8px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.7) !important;
}
/* The scrollable list container */
[data-baseweb="list"],
[data-baseweb="menu"] {
    background-color: #1E2130 !important;
}
/* Every element inside the list */
[data-baseweb="list"] *,
[data-baseweb="menu"] * {
    background-color: #1E2130 !important;
    color: #F1F5F9 !important;
}
/* Individual option items */
[data-baseweb="list"] li,
[data-baseweb="menu"] li,
[role="option"] {
    background-color: #1E2130 !important;
    color: #F1F5F9 !important;
    font-size: 0.88rem !important;
    padding: 8px 14px !important;
    cursor: pointer !important;
}
/* Hover and selected states */
[data-baseweb="list"] li:hover,
[data-baseweb="menu"] li:hover,
[role="option"]:hover {
    background-color: #1D6FA4 !important;
    color: #FFFFFF !important;
}
[aria-selected="true"],
[data-baseweb="list"] li[aria-selected="true"],
[role="option"][aria-selected="true"] {
    background-color: #164E63 !important;
    color: #FFFFFF !important;
}
[data-testid="stSidebar"] hr { border-color: #2E3550 !important; }
[data-testid="stSidebar"] [data-baseweb="slider"] [role="slider"] {
    background: #F0B429 !important;
}

/* ── Main content typography ── */
h1, h2, h3, h4, h5 { color: #F1F5F9 !important; }
.stMarkdown p, p, li { color: #CBD5E1; }
.stCaption, small { color: #64748B !important; }
strong, b { color: #F1F5F9; }

/* ── DataFrames ── */
[data-testid="stDataFrame"] {
    background: #1E2130 !important;
    border: 1px solid #2E3550 !important;
    border-radius: 8px;
    overflow: hidden;
}
[data-testid="stDataFrame"] th {
    background: #0F172A !important;
    color: #F0B429 !important;
    font-size: 0.72rem !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    border-bottom: 1px solid #2E3550 !important;
}
[data-testid="stDataFrame"] td {
    color: #CBD5E1 !important;
    border-color: #2E3550 !important;
}
[data-testid="stDataFrame"] tr:hover td {
    background: #252A3A !important;
}

/* ── Plain markdown tables (st.markdown with | pipe | syntax | ) ──
   These render as raw <table> HTML and were invisible — no contrast CSS
   existed for them, only for the interactive st.dataframe() widget. ── */
.stMarkdown table {
    background: #1E2130 !important;
    border: 1px solid #2E3550 !important;
    border-radius: 8px;
    border-collapse: collapse;
    width: 100%;
    overflow: hidden;
}
.stMarkdown table th {
    background: #0F172A !important;
    color: #F0B429 !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 10px 14px !important;
    border: 1px solid #2E3550 !important;
    text-align: left;
}
.stMarkdown table td {
    color: #CBD5E1 !important;
    background: #1E2130 !important;
    padding: 9px 14px !important;
    border: 1px solid #2E3550 !important;
    font-size: 0.86rem;
}
.stMarkdown table tr:hover td {
    background: #252A3A !important;
}
.stMarkdown table strong,
.stMarkdown table b {
    color: #F1F5F9 !important;
}

/* ── Dividers ── */
hr { border: none; border-top: 1px solid #2E3550 !important; }


/* ── Streamlit alerts — full dark override ── */
/* Target every alert type by role and data attributes */
[data-testid="stAlert"],
[data-testid="stAlert"] > div,
div[role="alert"] {
    background-color: #1E2130 !important;
    border: 1px solid #2E3550 !important;
    border-radius: 8px !important;
    color: #CBD5E1 !important;
}
/* All text inside alerts must be light */
[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] div,
div[role="alert"] p,
div[role="alert"] span,
div[role="alert"] div {
    color: #CBD5E1 !important;
    background-color: transparent !important;
}
/* Warning — amber left border */
[data-testid="stAlert"][data-baseweb="notification"],
.stWarning > div,
[data-testid="stAlert"]:has(svg[aria-label*="warning" i]),
[data-testid="stAlert"]:has(svg[data-testid*="warning" i]) {
    border-left: 4px solid #F59E0B !important;
}
/* Info — blue left border */
[data-testid="stAlert"]:has(svg[aria-label*="info" i]),
.stInfo > div {
    border-left: 4px solid #4B91D4 !important;
}
/* Error — red left border */
[data-testid="stAlert"]:has(svg[aria-label*="error" i]),
.stError > div {
    border-left: 4px solid #EF4444 !important;
}
/* Success — green left border */
.stSuccess > div {
    border-left: 4px solid #22C55E !important;
}
/* Alert icon SVGs */
[data-testid="stAlert"] svg {
    fill: #F59E0B !important;
    color: #F59E0B !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #1E2130 !important;
    border: 1px solid #2E3550 !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary {
    color: #F1F5F9 !important;
    background: #1E2130 !important;
}
[data-testid="stExpander"] summary:hover {
    background: #252A3A !important;
}
[data-testid="stExpander"] > div > div {
    background: #1E2130 !important;
    color: #CBD5E1 !important;
}


/* ── Metric cards ── */
.diq-card {
    background: #1E2130;
    border-radius: 8px;
    padding: 14px 18px;
    border: 1px solid #2E3550;
    border-left: 4px solid #1D6FA4;
    margin-bottom: 8px;
}
.diq-card .label {
    font-size: 0.68rem; color: #64748B;
    text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 4px;
}
.diq-card .value {
    font-size: 1.5rem; font-weight: 700; color: #F1F5F9; line-height: 1.1;
}
.diq-card .sub { font-size: 0.74rem; color: #64748B; margin-top: 2px; }
.diq-card.good  { border-left-color: #22C55E; }
.diq-card.warn  { border-left-color: #F59E0B; }
.diq-card.bad   { border-left-color: #EF4444; }
.diq-card.gold  { border-left-color: #F0B429; }

/* ── Stat boxes ── */
.stat-box {
    background: #1E2130;
    border: 1px solid #2E3550;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
}
.stat-box .stat-value {
    font-size: 1.8rem; font-weight: 700; color: #F1F5F9; line-height: 1;
}
.stat-box .stat-label {
    font-size: 0.68rem; color: #64748B;
    text-transform: uppercase; letter-spacing: 0.07em; margin-top: 4px;
}
.stat-box .stat-delta { font-size: 0.78rem; margin-top: 4px; color: #94A3B8; }
.stat-box.good  .stat-value { color: #22C55E; }
.stat-box.warn  .stat-value { color: #F59E0B; }
.stat-box.bad   .stat-value { color: #EF4444; }
.stat-box.gold  .stat-value { color: #F0B429; }

/* ── Pitcher context bar ── */
.pitcher-context-bar {
    background: #1E2130;
    border: 1px solid #2E3550;
    border-left: 4px solid #F0B429;
    border-radius: 8px;
    padding: 10px 18px;
    margin-bottom: 18px;
}
.pcb-name { font-size: 1.0rem; font-weight: 700; color: #F0B429; margin-right: 4px; }
.pcb-dot  { color: #2E3550; margin: 0 6px; }
.pcb-stat { font-size: 0.80rem; color: #64748B; }
.pcb-stat b { color: #F1F5F9; font-weight: 600; }

/* ── Page header ── */
.diq-page-header {
    border-bottom: 1px solid #2E3550;
    padding-bottom: 12px;
    margin-bottom: 20px;
}
.diq-page-header h2 {
    color: #F1F5F9 !important; margin: 0; font-size: 1.4rem;
}
.diq-page-header .subtitle { color: #64748B; font-size: 0.84rem; margin-top: 3px; }

/* ── Section header ── */
.section-header {
    font-size: 0.66rem; font-weight: 700; color: #475569;
    text-transform: uppercase; letter-spacing: 0.11em;
    margin: 20px 0 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid #2E3550;
}

/* ── Coach's Insight ── */
.coaches-insight {
    background: #0F172A;
    border-radius: 10px;
    padding: 18px 22px;
    margin-top: 24px;
    border: 1px solid #F0B42930;
    border-left: 4px solid #F0B429;
}
.coaches-insight .ci-label {
    font-size: 0.66rem; font-weight: 700; color: #F0B429;
    text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 6px;
}
.coaches-insight .ci-text {
    font-size: 0.94rem; color: #CBD5E1; line-height: 1.65;
}
.coaches-insight .ci-action {
    font-size: 0.82rem; color: #64748B; margin-top: 8px; font-style: italic;
}

/* ── Traffic light cards ── */
.tl-card {
    border-radius: 10px; padding: 24px; text-align: center;
    border: 1px solid #2E3550; background: #1E2130;
}
.tl-card.safe    { background: #052e16; border-color: #22C55E30; }
.tl-card.caution { background: #1c1400; border-color: #F59E0B30; }
.tl-card.danger  { background: #1c0a0a; border-color: #EF444430; }
.tl-card.under   { background: #0c1a2e; border-color: #4B91D430; }

/* ── Badges ── */
.badge { display:inline-block; padding:2px 8px; border-radius:10px; font-size:0.72rem; font-weight:700; }
.badge-green { background:#052e16; color:#22C55E; border:1px solid #22C55E30; }
.badge-amber { background:#1c1400; color:#F59E0B; border:1px solid #F59E0B30; }
.badge-red   { background:#1c0a0a; color:#EF4444; border:1px solid #EF444430; }
.badge-blue  { background:#0c1a2e; color:#4B91D4; border:1px solid #4B91D430; }

/* ── Module cards on home page ── */
.module-card {
    background: #1E2130;
    border: 1px solid #2E3550;
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 6px;
    transition: border-color 0.2s;
}
.module-card:hover { border-color: #F0B429; }
</style>
"""

PLOTLY_DARK = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#1E2130",
    font=dict(family="Inter, system-ui, sans-serif", size=11, color="#94A3B8"),
    margin=dict(l=48, r=24, t=40, b=36),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        bgcolor="rgba(0,0,0,0)", font=dict(color="#94A3B8", size=10),
    ),
    xaxis=dict(gridcolor="#2E3550", linecolor="#2E3550",
               tickcolor="#475569", zerolinecolor="#2E3550",
               tickfont=dict(color="#94A3B8")),
    yaxis=dict(gridcolor="#2E3550", linecolor="#2E3550",
               tickcolor="#475569", zerolinecolor="#2E3550",
               tickfont=dict(color="#94A3B8")),
    coloraxis_colorbar=dict(tickfont=dict(color="#94A3B8")),
)


def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def apply_theme(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(**PLOTLY_DARK)
    if title:
        fig.update_layout(title=dict(
            text=title,
            font=dict(size=13, color=TEXT_PRI),
        ))
    # Ensure all axes are styled
    fig.update_xaxes(gridcolor="#2E3550", linecolor="#2E3550", tickfont=dict(color="#94A3B8"))
    fig.update_yaxes(gridcolor="#2E3550", linecolor="#2E3550", tickfont=dict(color="#94A3B8"))
    return fig


# ── Pitcher context bar ────────────────────────────────────────────────────────
def pitcher_context_bar():
    name  = st.session_state.get("selected_pitcher_name", "")
    row   = st.session_state.get("selected_pitcher_row", {})
    mlbam = st.session_state.get("selected_pitcher_mlbam", 0)

    if not name or mlbam == 0:
        st.markdown(
            f'<div class="pitcher-context-bar">'
            f'<span class="pcb-name">⚾ No pitcher selected</span>'
            f'<span class="pcb-dot">·</span>'
            f'<span class="pcb-stat">Use the sidebar dropdown to choose a pitcher</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    def _s(key, fmt="{:.2f}", fb="—"):
        v = row.get(key)
        try:
            f = float(v)
            if f == f:
                return fmt.format(f)
        except (TypeError, ValueError):
            pass
        return fb

    era   = _s("ERA",   "{:.2f}")
    xwoba = _s("xwOBA", "{:.3f}")
    ev    = _s("AvgEV", "{:.1f}")
    pa    = _s("pa",    "{:.0f}")

    parts = [f'<span class="pcb-name">⚾ {name}</span>']
    if era   != "—": parts.append(f'<span class="pcb-dot">·</span><span class="pcb-stat"><b>{era}</b> ERA</span>')
    parts.append(f'<span class="pcb-dot">·</span><span class="pcb-stat"><b>{xwoba}</b> xwOBA vs</span>')
    if ev    != "—": parts.append(f'<span class="pcb-dot">·</span><span class="pcb-stat"><b>{ev}</b> mph avg EV</span>')
    if pa    != "—": parts.append(f'<span class="pcb-dot">·</span><span class="pcb-stat"><b>{pa}</b> BF</span>')
    parts.append(f'<span class="pcb-dot">·</span><span class="pcb-stat" style="color:{TEXT_MUT};">MLBAM {mlbam}</span>')

    st.markdown(
        f'<div class="pitcher-context-bar">{"".join(parts)}</div>',
        unsafe_allow_html=True,
    )


# ── Page header ────────────────────────────────────────────────────────────────
def page_header(title: str, subtitle: str = "", icon: str = "⚾"):
    pitcher_context_bar()
    st.markdown(
        f'<div class="diq-page-header">'
        f'<h2>{icon} {title}</h2>'
        + (f'<div class="subtitle">{subtitle}</div>' if subtitle else "")
        + '</div>',
        unsafe_allow_html=True,
    )


# ── Section header ─────────────────────────────────────────────────────────────
def section_header(title: str):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


# ── Metric cards ───────────────────────────────────────────────────────────────
def metric_card(label: str, value: str, sub: str = "", status: str = "neutral") -> str:
    cls = f"diq-card {status}" if status != "neutral" else "diq-card"
    return (
        f'<div class="{cls}">'
        f'<div class="label">{label}</div>'
        f'<div class="value">{value}</div>'
        + (f'<div class="sub">{sub}</div>' if sub else "")
        + "</div>"
    )

def metric_row(cards: list):
    cols = st.columns(len(cards))
    for col, c in zip(cols, cards):
        with col:
            st.markdown(
                metric_card(c.get("label",""), c.get("value","—"),
                            c.get("sub",""), c.get("status","neutral")),
                unsafe_allow_html=True,
            )


# ── Stat boxes ─────────────────────────────────────────────────────────────────
def stat_box(value: str, label: str, delta: str = "", status: str = "") -> str:
    cls  = f"stat-box {status}" if status else "stat-box"
    if delta:
        d_col = GREEN if ("▲" in delta or "+" in delta) else RED if ("▼" in delta or "−" in delta) else TEXT_SEC
        delta_html = f'<div class="stat-delta" style="color:{d_col};">{delta}</div>'
    else:
        delta_html = ""
    return (
        f'<div class="{cls}">'
        f'<div class="stat-value">{value}</div>'
        f'<div class="stat-label">{label}</div>'
        f'{delta_html}'
        f'</div>'
    )

def stat_row(stats: list):
    cols = st.columns(len(stats))
    for col, s in zip(cols, stats):
        with col:
            st.markdown(stat_box(s.get("value","—"), s.get("label",""),
                                  s.get("delta",""), s.get("status","")),
                         unsafe_allow_html=True)


# ── Coach's Insight ────────────────────────────────────────────────────────────
def coaches_insight(insight: str, action: str = ""):
    action_html = f'<div class="ci-action">▶ {action}</div>' if action else ""
    st.markdown(
        f'<div class="coaches-insight">'
        f'<div class="ci-label">⚾ Coach\'s Insight</div>'
        f'<div class="ci-text">{insight}</div>'
        f'{action_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Percentile helpers ─────────────────────────────────────────────────────────
def percentile_of(value: float, series: pd.Series, higher_is_better: bool = True) -> float:
    if series.empty or pd.isna(value):
        return 50.0
    clean = series.dropna()
    if clean.empty:
        return 50.0
    rank = float((clean < value).sum() / len(clean) * 100)
    return rank if higher_is_better else 100 - rank

def percentile_color(pct: float) -> str:
    if pct >= 67: return GREEN
    if pct >= 33: return AMBER
    return RED

def percentile_badge(pct: float) -> str:
    cls = "badge-green" if pct >= 67 else "badge-amber" if pct >= 33 else "badge-red"
    return f'<span class="badge {cls}">{pct:.0f}th</span>'


# ── Radar chart ────────────────────────────────────────────────────────────────
def radar_chart(categories: list, values: list, title: str = "", color: str = BLUE_ACC) -> go.Figure:
    cats = categories + [categories[0]]
    vals = values + [values[0]]
    fig  = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals, theta=cats, fill="toself",
        fillcolor=rgba(BLUE_ACC, 0.15),
        line=dict(color=color, width=2),
        name="Pitcher",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, 100],
                tickfont=dict(size=9, color=TEXT_MUT),
                gridcolor=BORDER, linecolor=BORDER,
            ),
            angularaxis=dict(
                tickfont=dict(size=10, color=TEXT_SEC),
                linecolor=BORDER,
            ),
            bgcolor=BG_CARD,
        ),
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=50, b=40),
    )
    if title:
        fig.update_layout(title=dict(text=title, font=dict(size=13, color=TEXT_PRI)))
    return fig


# ── Strike zone ────────────────────────────────────────────────────────────────
def add_strike_zone(fig: go.Figure, row: int = 1, col: int = 1):
    fig.add_shape(type="rect", x0=-0.83, x1=0.83, y0=1.5, y1=3.5,
                  line=dict(color=GOLD, width=1.5, dash="dash"),
                  fillcolor="rgba(0,0,0,0)", row=row, col=col)
    return fig


# ── Pitch colour ───────────────────────────────────────────────────────────────
def pitch_color(pt: str) -> str:
    return PITCH_COLORS.get(str(pt).upper(), PITCH_COLORS["OTHER"])


# ── Guards ─────────────────────────────────────────────────────────────────────
def require_pitcher(session_state) -> bool:
    name  = session_state.get("selected_pitcher_name")
    mlbam = session_state.get("selected_pitcher_mlbam", 0)
    if not name or mlbam == 0:
        pitcher_context_bar()
        st.warning("⚾ **No pitcher selected.** Use the sidebar dropdown.")
        return False
    return True


def load_statcast(session_state) -> Optional[pd.DataFrame]:
    mlbam     = session_state.get("selected_pitcher_mlbam", 0)
    name      = session_state.get("selected_pitcher_name", "")
    cache_key = f"sc_{mlbam}"
    if cache_key in session_state:
        return session_state[cache_key]
    from config.settings import SEASON
    from src.data_io.loaders import get_pitcher_statcast
    with st.spinner(f"Downloading Statcast data for **{name}**…"):
        try:
            df = get_pitcher_statcast(mlbam, SEASON)
            session_state[cache_key] = df
            return df
        except Exception as exc:
            st.error(f"Could not load data for **{name}** (MLBAM {mlbam}).\n\n`{exc}`")
            return None


# ── Analytics helpers ──────────────────────────────────────────────────────────
def pitch_effectiveness(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if not {"pitch_type","description","delta_run_exp"}.issubset(df.columns):
        return pd.DataFrame()
    rows, total = [], len(df)
    for pt, grp in df.groupby("pitch_type"):
        n      = len(grp)
        swings = grp.get("is_swing",  pd.Series([False]*n, index=grp.index)).sum()
        whiffs = grp.get("is_whiff",  pd.Series([False]*n, index=grp.index)).sum()
        csw    = grp.get("is_csw",    pd.Series([False]*n, index=grp.index)).sum()
        cs     = grp.get("is_called_strike", pd.Series([False]*n, index=grp.index)).sum()
        rv100  = grp["delta_run_exp"].sum() / n * 100 if grp["delta_run_exp"].notna().sum() > 0 else float("nan")
        xwoba  = grp["estimated_woba_using_speedangle"].mean() if "estimated_woba_using_speedangle" in grp.columns else float("nan")
        rows.append({
            "pitch_type": pt, "n": n, "usage_pct": n / total * 100,
            "csw_pct":    csw / n * 100,
            "whiff_pct":  whiffs / swings * 100 if swings > 0 else 0,
            "cs_pct":     cs / n * 100,
            "rv_per_100": rv100, "xwoba_against": xwoba,
        })
    return pd.DataFrame(rows).sort_values("usage_pct", ascending=False)


def calculate_acwr(df: pd.DataFrame, acute_window: int = 7, chronic_window: int = 28) -> pd.DataFrame:
    if df is None or df.empty or "game_date" not in df.columns:
        return pd.DataFrame()
    daily = df.groupby("game_date").size().reset_index(name="pitches").sort_values("game_date")
    daily["acute_load"]   = daily["pitches"].rolling(acute_window,  min_periods=1).mean()
    daily["chronic_load"] = daily["pitches"].rolling(chronic_window, min_periods=1).mean()
    daily["acwr"] = (daily["acute_load"] / daily["chronic_load"]).replace([float("inf"), float("-inf")], float("nan"))
    def zone(v):
        if v != v: return "unknown"
        if v < 0.8:  return "underload"
        if v <= 1.3: return "optimal"
        if v <= 1.5: return "caution"
        return "danger"
    daily["acwr_zone"] = daily["acwr"].apply(zone)
    return daily


def velocity_decay(df: pd.DataFrame, pitch_type: str = None) -> dict:
    if df is None or df.empty: return {}
    sub = df.copy()
    if pitch_type and "pitch_type" in sub.columns:
        sub = sub[sub["pitch_type"] == pitch_type]
    if "inning" not in sub.columns or "release_speed" not in sub.columns: return {}
    by_inn = (sub.groupby("inning")["release_speed"]
              .agg(["mean","count"]).reset_index()
              .rename(columns={"mean":"avg_velo","count":"n"}))
    by_inn = by_inn[by_inn["n"] >= 3]
    if len(by_inn) < 3:
        return {"by_inning": by_inn, "slope": 0, "r2": 0, "flag": False}
    from scipy import stats
    slope, _, r, p, _ = stats.linregress(by_inn["inning"], by_inn["avg_velo"])
    return {"by_inning": by_inn, "slope": slope, "r2": r**2, "pval": p,
            "flag": (slope < -0.3) and (p < 0.10)}


def release_point_drift(df: pd.DataFrame, n_games: int = 5) -> dict:
    if df is None or df.empty: return {}
    if not {"game_date","release_pos_x","release_pos_z"}.issubset(df.columns): return {}
    by_game = (df.groupby("game_date")[["release_pos_x","release_pos_z"]]
               .mean().reset_index().sort_values("game_date"))
    if len(by_game) < 2:
        return {"by_game": by_game, "drift_x": 0, "drift_z": 0, "flag": False}
    bx, bz  = by_game["release_pos_x"].mean(), by_game["release_pos_z"].mean()
    recent  = by_game.tail(n_games)
    dx = abs(recent["release_pos_x"].mean() - bx) * 12
    dz = abs(recent["release_pos_z"].mean() - bz) * 12
    return {"by_game": by_game, "baseline_x": bx, "baseline_z": bz,
            "drift_x": dx, "drift_z": dz, "flag": (dx > 1.0) or (dz > 1.0)}


def pitch_transition_matrix(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty or "pitch_type" not in df.columns: return pd.DataFrame()
    sort_cols = ["game_date","at_bat_number","pitch_number"] if "pitch_number" in df.columns else ["game_date"]
    df2 = df.sort_values(sort_cols).copy()
    df2["next_pitch"] = df2["pitch_type"].shift(-1)
    if "at_bat_number" in df2.columns:
        df2 = df2[df2["at_bat_number"] == df2["at_bat_number"].shift(-1)]
    df2 = df2.dropna(subset=["pitch_type","next_pitch"])
    if df2.empty: return pd.DataFrame()
    counts = pd.crosstab(df2["pitch_type"], df2["next_pitch"])
    return counts.div(counts.sum(axis=1), axis=0).round(3)


def stuff_grade(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return pd.DataFrame()
    feats = [c for c in ["release_speed","release_spin_rate","pfx_x","pfx_z","release_extension"] if c in df.columns]
    if len(feats) < 3 or "is_whiff" not in df.columns: return pd.DataFrame()
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    rows = []
    for pt, grp in df.groupby("pitch_type"):
        gc = grp[feats + ["is_whiff"]].dropna()
        if len(gc) < 50: continue
        Xs = StandardScaler().fit_transform(gc[feats].values)
        try:
            lr = LogisticRegression(max_iter=300, random_state=42)
            lr.fit(Xs, gc["is_whiff"].astype(int).values)
            p  = lr.predict_proba(Xs)[:,1].mean()
        except Exception:
            p = gc["is_whiff"].mean()
        grade = float(np.clip(50 + (p - 0.24) / 0.24 * 30, 20, 80))
        rows.append({"pitch_type": pt, "n": len(gc), "whiff_prob": round(p,3),
                     "stuff_grade": round(grade,1),
                     "avg_velo": round(gc["release_speed"].mean(),1) if "release_speed" in gc.columns else float("nan"),
                     "avg_spin": round(gc["release_spin_rate"].mean(),0) if "release_spin_rate" in gc.columns else float("nan")})
    return pd.DataFrame(rows).sort_values("stuff_grade", ascending=False)


def no_data_placeholder(msg: str = "No data available."):
    st.info(f"ℹ️ {msg}")


def metric_glossary_expander(terms: list = None, label: str = "What do these terms mean?"):
    """
    Render a collapsed expander with plain-English definitions for the metric
    abbreviations used on the current page. Call near the top of any page that
    uses CSW%, RV/100, xwOBA, ACWR, EV, Barrel%, or pitch codes like FF/SI/ST.

    terms: optional list of abbreviation strings to filter METRIC_GLOSSARY to
           just the ones relevant on this page, e.g. ["CSW%", "Whiff%", "RV/100"].
           If None, shows the full glossary.
    """
    entries = METRIC_GLOSSARY
    if terms:
        wanted = {t.upper() for t in terms}
        entries = [e for e in METRIC_GLOSSARY if e[0].upper() in wanted]
    if not entries:
        return
    with st.expander(f"📖 {label}"):
        for abbr, full, desc in entries:
            st.markdown(
                f'<div style="margin-bottom:10px;">'
                f'<span style="color:{GOLD};font-weight:700;">{abbr}</span>'
                f'<span style="color:{TEXT_MUT};"> — {full}</span>'
                f'<div style="color:{TEXT_SEC};font-size:0.85rem;margin-top:2px;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )