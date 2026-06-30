"""
Diamond IQ — Pitcher Intelligence Suite
Home.py v5.0 — Leads with who/what/how, full glossary, every module showcased.
"""
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Diamond IQ | Pitcher Intelligence Suite",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded",
)

import sys, os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.components import (
    inject_css, section_header, rgba, metric_glossary_expander,
    BG_PAGE, BG_CARD, BG_CARD2, BORDER, SIDEBAR,
    NAVY, GOLD, BLUE_ACC, GREEN, RED, AMBER,
    TEXT_PRI, TEXT_SEC, TEXT_MUT, MUTED,
)
from config.settings import APP_NAME, APP_SUBTITLE, APP_VERSION, SEASON

inject_css()

@st.cache_data(show_spinner=False)
def load_roster() -> pd.DataFrame:
    try:
        from src.data_io.loaders import build_pitcher_roster
        return build_pitcher_roster(SEASON)
    except Exception:
        return pd.DataFrame()

# First load after a fresh deploy has no cached parquet files yet, so this
# triggers a live download from Baseball Savant. Show a spinner so it doesn't
# look frozen during that one-time wait (subsequent visits are instant).
with st.spinner("Loading season roster from Baseball Savant — first load only, ~10-20 s…"):
    roster = load_roster()

def _get(row: dict, *keys, fmt="{}", fallback="—"):
    for k in keys:
        v = row.get(k)
        if v is not None and str(v) not in ("nan", ""):
            try:
                return fmt.format(float(v))
            except (TypeError, ValueError):
                return str(v)
    return fallback

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        f'<div style="padding:12px 0 16px;">'
        f'<div style="font-size:1.25rem;font-weight:700;color:{GOLD};">⚾ Diamond IQ</div>'
        f'<div style="font-size:0.75rem;color:{TEXT_MUT};margin-top:2px;">{APP_SUBTITLE}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    selected_name, selected_row = None, {}

    if roster.empty:
        st.error("Roster not loaded.\n\nRun:\n```\npython scripts/01_download_base_data.py\n```")
    else:
        name_col      = "player_name" if "player_name" in roster.columns else roster.columns[0]
        pitcher_names = sorted(roster[name_col].dropna().unique().tolist())
        default_pitcher = next(
            (p for p in ["Zack Wheeler","Gerrit Cole","Chris Sale",
                          "Logan Webb","Spencer Strider","Corbin Burnes"]
             if p in pitcher_names),
            pitcher_names[0] if pitcher_names else "",
        )
        selected_name = st.selectbox(
            "Select Pitcher",
            options=pitcher_names,
            index=pitcher_names.index(default_pitcher) if default_pitcher in pitcher_names else 0,
            help="Any MLB pitcher with ≥10 batters faced in 2024.",
            key="home_pitcher_select",
        )
        row_df       = roster[roster[name_col] == selected_name]
        selected_row = row_df.iloc[0].to_dict() if not row_df.empty else {}

        st.markdown("---")

        pa    = _get(selected_row, "pa",    fmt="{:.0f}")
        xwoba = _get(selected_row, "xwOBA", fmt="{:.3f}")
        ev    = _get(selected_row, "AvgEV", fmt="{:.1f}")
        era   = _get(selected_row, "ERA",   fmt="{:.2f}")
        ip    = _get(selected_row, "IP",    fmt="{:.1f}")
        mlbam = selected_row.get("mlbam_id", "—")

        def _stat_line(label, value, unit=""):
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;'
                f'padding:5px 0;border-bottom:1px solid {BORDER};">'
                f'<span style="font-size:0.76rem;color:{TEXT_MUT};">{label}</span>'
                f'<span style="font-size:0.80rem;font-weight:600;color:{TEXT_PRI};">'
                f'{value}{" " + unit if unit else ""}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if era   != "—": _stat_line("ERA",            era)
        if ip    != "—": _stat_line("Innings pitched", ip)
        _stat_line("Batters faced",  pa)
        _stat_line("xwOBA against",  xwoba)
        if ev    != "—": _stat_line("Avg exit velo",   ev, "mph")
        st.markdown(
            f'<div style="font-size:0.68rem;color:{TEXT_MUT};margin-top:8px;">'
            f'MLBAM {mlbam}</div>',
            unsafe_allow_html=True,
        )
        st.markdown("---")
        st.caption(f"Season {SEASON} · v{APP_VERSION}")

    st.session_state["selected_pitcher_name"]  = selected_name
    st.session_state["selected_pitcher_row"]   = selected_row
    st.session_state["selected_pitcher_mlbam"] = int(selected_row.get("mlbam_id", 0)) if selected_row else 0
    st.session_state["pitcher_roster"]         = roster

# ── Main page ─────────────────────────────────────────────────────────────────

# Hero
st.markdown(
    f'<div style="border-bottom:1px solid {BORDER};padding-bottom:18px;margin-bottom:22px;">'
    f'<div style="display:flex;align-items:baseline;gap:12px;">'
    f'<h1 style="color:{GOLD};font-size:2.9rem;margin:0;font-weight:1100;">⚾ Diamond IQ</h1>'
    # f'<span style="font-size:0.85rem;color:{TEXT_MUT};">MLB {SEASON} · Statcast-powered</span>'
    f'</div>'
    f'<div style="font-size:1.90rem;color:{TEXT_SEC};margin-top:4px;">'
    f'Pitching Intelligence Suite</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Who / What / How — answered immediately, before anything else ─────────────
section_header("WHO THIS IS FOR · WHAT IT DOES · HOW IT HELPS")

wwh_cols = st.columns(3)
wwh_content = [
    ("WHO", BLUE_ACC,
     "The MLB pitching coach",
     "Not a general manager, not a scout, not medical staff. One stakeholder: the coach "
     "who decides what a pitcher throws tonight and whether he stays in the game."),
    ("WHAT", GOLD,
     "Turns Statcast data into a pre-game plan",
     "Every pitch this season, run through 8 connected models — ranking, mechanics, "
     "location, effectiveness, sequencing, fatigue, pitch quality, and a prescriptive "
     "script for tonight's actual batting order."),
    ("HOW", GREEN,
     "Tells the coach exactly what to do",
     "Not just charts. Each page ends with a plain-English recommendation: which pitch "
     "to lead with, when to pull him, which batter is the toughest out tonight."),
]
for col_w, (tag, accent, title, desc) in zip(wwh_cols, wwh_content):
    with col_w:
        st.markdown(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};'
            f'border-top:3px solid {accent};border-radius:8px;padding:16px;height:100%;">'
            f'<div style="font-size:0.66rem;font-weight:700;color:{accent};'
            f'text-transform:uppercase;letter-spacing:0.10em;margin-bottom:8px;">{tag}</div>'
            f'<div style="font-size:0.95rem;font-weight:700;color:{TEXT_PRI};margin-bottom:6px;">{title}</div>'
            f'<div style="font-size:0.80rem;color:{TEXT_SEC};line-height:1.55;">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# Pitcher context bar
if selected_name:
    mlbam2 = selected_row.get("mlbam_id","—")
    era2   = _get(selected_row, "ERA",   fmt="{:.2f}")
    xwoba2 = _get(selected_row, "xwOBA", fmt="{:.3f}")
    ev2    = _get(selected_row, "AvgEV", fmt="{:.1f}")
    pa2    = _get(selected_row, "pa",    fmt="{:.0f}")

    parts = [f'<span style="font-size:1.0rem;font-weight:700;color:{GOLD};">⚾ {selected_name}</span>']
    sep = f'<span style="color:{BORDER};margin:0 8px;">·</span>'
    if era2  != "—": parts.append(f'{sep}<span style="font-size:0.80rem;color:{TEXT_SEC};"><b style="color:{TEXT_PRI};">{era2}</b> ERA</span>')
    parts.append(f'{sep}<span style="font-size:0.80rem;color:{TEXT_SEC};"><b style="color:{TEXT_PRI};">{xwoba2}</b> xwOBA vs</span>')
    if ev2   != "—": parts.append(f'{sep}<span style="font-size:0.80rem;color:{TEXT_SEC};"><b style="color:{TEXT_PRI};">{ev2}</b> mph EV</span>')
    if pa2   != "—": parts.append(f'{sep}<span style="font-size:0.80rem;color:{TEXT_SEC};"><b style="color:{TEXT_PRI};">{pa2}</b> BF</span>')
    parts.append(f'{sep}<span style="font-size:0.74rem;color:{TEXT_MUT};">MLBAM {mlbam2}</span>')

    st.markdown(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-left:4px solid {GOLD};'
        f'border-radius:8px;padding:10px 18px;margin-bottom:20px;">'
        f'{"".join(parts)}'
        f'</div>',
        unsafe_allow_html=True,
    )
elif roster.empty:
    st.warning("No pitcher data found. Run `python scripts/01_download_base_data.py`.")
    st.stop()

# ── Module showcase — every page, with the actual decision it supports ────────
section_header("EVERY MODULE, AND THE DECISION IT SUPPORTS")

modules = [
    ("1", "Pitcher Scorecard",    "Where does he rank right now?",
     "Percentile radar against every qualified MLB pitcher this season.", BLUE_ACC),
    ("2", "Arsenal Profile",      "Is his mechanics where it should be?",
     "Movement shape, spin rate, and release-point drift, start to start.", BLUE_ACC),
    ("3", "Zone Intelligence",    "Is he hitting his spots?",
     "Location heatmaps split by pitch type, count, and batter handedness.", BLUE_ACC),
    ("4", "Pitch Effectiveness",  "Which pitches are actually working?",
     "Run Value per 100 pitches, CSW%, and xwOBA trend across the season.", GREEN),
    ("5", "Pitch Sequencing",     "Is he setting hitters up, or predictable?",
     "Markov transition matrix showing what pitch follows what, and how exploitable that pattern is.", GREEN),
    ("6", "Workload & Fatigue",   "Should he start, and when do we pull him?",
     "ACWR injury-risk ratio, inning-by-inning velocity decay, and a clear start/pull verdict.", AMBER),
    ("7", "Stuff Grade Model",    "How good is each pitch on a scout's scale?",
     "Machine-learning model scoring every pitch 20 to 80, same scale scouts use.", AMBER),
    ("8", "Game Planning Engine", "How do we attack tonight's entire lineup?",
     "Prescriptive script per batter, a Monte Carlo at-bat simulator, and a full 9-batter scouting report.", RED),
]

for num, name, question, desc, accent in modules:
    st.markdown(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};'
        f'border-left:3px solid {rgba(accent,0.6)};'
        f'border-radius:8px;padding:12px 16px;margin-bottom:8px;">'
        f'<div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;">'
        f'<span style="font-size:0.68rem;color:{TEXT_MUT};min-width:14px;">{num}</span>'
        f'<span style="font-size:0.90rem;font-weight:700;color:{TEXT_PRI};">{name}</span>'
        f'<span style="font-size:0.78rem;color:{accent};font-style:italic;">"{question}"</span>'
        f'</div>'
        f'<div style="font-size:0.78rem;color:{TEXT_SEC};margin-top:4px;margin-left:24px;">{desc}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ── Workflow ───────────────────────────────────────────────────────────────────
section_header("HOW TO USE THIS, START TO FINISH")
steps = [
    ("1", BLUE_ACC, "Select a pitcher",   "Sidebar dropdown — any MLB pitcher from the 2024 season."),
    ("2", GREEN,    "Check readiness",    "Page 6 gives an immediate start/pull recommendation."),
    ("3", GOLD,     "Study the arsenal",  "Pages 1–5 cover ranking, mechanics, location, effectiveness, sequencing."),
    ("4", RED,      "Build the game plan","Page 8 generates the full lineup scouting report before first pitch."),
]
step_cols = st.columns(4)
for col_w, (num, accent, title, desc) in zip(step_cols, steps):
    with col_w:
        st.markdown(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;'
            f'padding:14px;height:100%;">'
            f'<div style="min-width:26px;height:26px;border-radius:50%;'
            f'background:{rgba(accent,0.12)};border:1px solid {rgba(accent,0.35)};'
            f'display:flex;align-items:center;justify-content:center;'
            f'font-size:0.72rem;font-weight:700;color:{accent};margin-bottom:8px;">{num}</div>'
            f'<div style="font-size:0.85rem;font-weight:700;color:{TEXT_PRI};margin-bottom:4px;">{title}</div>'
            f'<div style="font-size:0.76rem;color:{TEXT_SEC};line-height:1.5;">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Full glossary, always available before navigating anywhere ────────────────
section_header("READING THE PLATFORM — ABBREVIATIONS AND PITCH CODES")
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.markdown(f'<div style="font-size:0.82rem;font-weight:700;color:{TEXT_PRI};margin-bottom:8px;">Metric abbreviations</div>', unsafe_allow_html=True)
    metric_glossary_expander(label="Open the full metric glossary")

with col_g2:
    st.markdown(f'<div style="font-size:0.82rem;font-weight:700;color:{TEXT_PRI};margin-bottom:8px;">Pitch type codes</div>', unsafe_allow_html=True)
    from src.components import PITCH_NAMES, pitch_badge
    with st.expander("Open the full pitch code reference"):
        common_codes = ["FF", "SI", "SL", "CU", "CH", "FC", "FS", "ST", "SV", "KC", "KN"]
        for code in common_codes:
            st.markdown(
                f'<div style="margin-bottom:6px;">{pitch_badge(code)}</div>',
                unsafe_allow_html=True,
            )

st.markdown("---")

# ── Status row ──────────────────────────────────────────────────────────────────
roster_count = len(roster) if not roster.empty else 0
cached_count = sum(1 for k in st.session_state
                   if k.startswith("sc_") and st.session_state[k] is not None)

col_s1, col_s2, col_s3 = st.columns(3)
for col_w, lbl, val, sub, vc in [
    (col_s1, "Roster",         f"{roster_count:,}", f"Pitchers · {SEASON}",         TEXT_PRI),
    (col_s2, "Cached",         str(cached_count),   "Statcast datasets in session",  TEXT_PRI),
    (col_s3, "Data source",    "Statcast",          "Baseball Savant · Parquet",     GREEN),
]:
    with col_w:
        st.markdown(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};'
            f'border-radius:8px;padding:14px 16px;">'
            f'<div style="font-size:0.65rem;color:{TEXT_MUT};text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:3px;">{lbl}</div>'
            f'<div style="font-size:1.5rem;font-weight:700;color:{vc};">{val}</div>'
            f'<div style="font-size:0.73rem;color:{TEXT_SEC};margin-top:2px;">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)
with st.expander("Data sources & technical details"):
    st.markdown(f"""
| Source | Content | Method |
|---|---|---|
| **MLB Statcast** | Pitch-level tracking — velocity, spin, movement, location, outcome | `pybaseball.statcast_pitcher()` |
| **Baseball Savant** | Season leaderboard — xwOBA, exit velocity, barrel rate | Direct CSV endpoint |

**Season:** {SEASON} · **Cache:** Apache Parquet (snappy)  
**First load per pitcher:** 30–90 s · **Subsequent loads:** &lt;1 s  
**Roster:** {roster_count:,} pitchers with ≥10 batters faced
    """)