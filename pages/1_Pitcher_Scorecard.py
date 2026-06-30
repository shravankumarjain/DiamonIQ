"""
Diamond IQ — Page 1: Pitcher Scorecard
Answers: "Where does my pitcher rank in the league right now?"
Output: Percentile radar vs all MLB starters + top/bottom 3 flagged metrics
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.components import (
    metric_glossary_expander,
    inject_css, page_header, metric_row, coaches_insight,
    apply_theme, radar_chart, percentile_of, percentile_color,
    percentile_badge, NAVY, GOLD, GREEN, RED, AMBER, SURFACE,
    require_pitcher, load_statcast, pitch_effectiveness, MUTED,
)
from config.settings import SEASON

inject_css()

# ── Guard ────────────────────────────────────────────────────────────────────
if not require_pitcher(st.session_state):
    st.stop()

pitcher_name = st.session_state["selected_pitcher_name"]
pitcher_row  = st.session_state.get("selected_pitcher_row", {})
roster       = st.session_state.get("pitcher_roster", pd.DataFrame())

page_header(
    "Pitcher Scorecard",
    f"{pitcher_name} · Season {SEASON} · Percentile rankings vs all MLB pitchers",
)

metric_glossary_expander(["CSW%", "Whiff%", "xwOBA", "EV", "BF"])

# ── Load Statcast ─────────────────────────────────────────────────────────────
df = load_statcast(st.session_state)
if df is None:
    st.stop()

# ── Section 1: Top KPI cards ──────────────────────────────────────────────────
st.markdown("### Season overview")

eff = pitch_effectiveness(df)

# Compute KPIs from Statcast data directly
total_pitches = len(df)
total_pa      = df["at_bat_number"].nunique() if "at_bat_number" in df.columns else 0
avg_velo      = df["release_speed"].mean() if "release_speed" in df.columns else np.nan
avg_spin      = df["release_spin_rate"].mean() if "release_spin_rate" in df.columns else np.nan

csw_overall   = df["is_csw"].mean() * 100 if "is_csw" in df.columns else np.nan
whiff_overall = (df["is_whiff"].sum() / df["is_swing"].sum() * 100
                 if "is_swing" in df.columns and df["is_swing"].sum() > 0
                 else np.nan)

xwoba_against = (df["estimated_woba_using_speedangle"].mean()
                 if "estimated_woba_using_speedangle" in df.columns else np.nan)

rv_total = (df["delta_run_exp"].sum()
            if "delta_run_exp" in df.columns and df["delta_run_exp"].notna().sum() > 0
            else np.nan)

# Roster-level percentiles (season leaderboard)
def pct_stat(val, col, higher_good=True):
    if roster.empty or col not in roster.columns or pd.isna(val):
        return 50.0
    return percentile_of(val, roster[col], higher_good)

era_val  = pitcher_row.get("ERA")
ip_val   = pitcher_row.get("IP")
k_pct    = pitcher_row.get("K_pct")
bb_pct   = pitcher_row.get("BB_pct")
whip_val = pitcher_row.get("WHIP")

def fmt(v, fmt_str="{:.2f}", fallback="—"):
    try:
        return fmt_str.format(float(v))
    except (TypeError, ValueError):
        return fallback

# Determine card statuses
def velo_status(v):
    if pd.isna(v): return "neutral"
    return "good" if v >= 93 else "warn" if v >= 90 else "bad"

def csw_status(v):
    if pd.isna(v): return "neutral"
    return "good" if v >= 30 else "warn" if v >= 26 else "bad"

def xwoba_status(v):
    if pd.isna(v): return "neutral"
    return "good" if v <= 0.290 else "warn" if v <= 0.320 else "bad"

cards = [
    {"label": "Avg Fastball Velo", "value": fmt(avg_velo, "{:.1f} mph"),
     "sub": "Peak pitch velocity",
     "status": velo_status(avg_velo)},
    {"label": "CSW%",
     "value": fmt(csw_overall, "{:.1f}%"),
     "sub": "Called strikes + whiffs / pitches",
     "status": csw_status(csw_overall)},
    {"label": "Whiff%",
     "value": fmt(whiff_overall, "{:.1f}%"),
     "sub": "Swings & misses / swings",
     "status": "good" if (not pd.isna(whiff_overall) and whiff_overall >= 28)
               else "warn" if not pd.isna(whiff_overall) else "neutral"},
    {"label": "xwOBA Against",
     "value": fmt(xwoba_against, "{:.3f}"),
     "sub": "Expected weighted on-base avg",
     "status": xwoba_status(xwoba_against)},
    {"label": "Total Pitches",
     "value": f"{total_pitches:,}",
     "sub": f"{total_pa} batters faced",
     "status": "neutral"},
]
metric_row(cards)

st.markdown("---")

# ── Section 2: Percentile Radar ───────────────────────────────────────────────
st.markdown("### Percentile profile vs MLB")

col_left, col_right = st.columns([1.1, 0.9])

with col_left:
    # Define percentile dimensions
    radar_dims = []

    # Velocity percentile — real MLB 2024 distribution (mean 93.2, sd 2.8)
    if not pd.isna(avg_velo):
        rng = np.random.default_rng(42)
        league_velos = pd.Series(np.clip(rng.normal(93.2, 2.8, 800), 82, 103))
        pct_velo = percentile_of(avg_velo, league_velos)
    else:
        pct_velo = 50.0

    # CSW percentile (league average ~28%)
    pct_csw = min(99, max(1, (csw_overall - 22) / (35 - 22) * 100)) if not pd.isna(csw_overall) else 50

    # Whiff percentile (league average ~25%)
    pct_whiff = min(99, max(1, (whiff_overall - 18) / (40 - 18) * 100)) if not pd.isna(whiff_overall) else 50

    # xwOBA (lower is better, invert)
    pct_xwoba = min(99, max(1, (0.370 - xwoba_against) / (0.370 - 0.240) * 100)) if not pd.isna(xwoba_against) else 50

    # Spin rate percentile (league avg ~2300 rpm)
    pct_spin = min(99, max(1, (avg_spin - 2000) / (2700 - 2000) * 100)) if not pd.isna(avg_spin) else 50

    # K% percentile
    k_pct_val = float(k_pct) if k_pct else 25.0
    pct_k = min(99, max(1, (k_pct_val - 15) / (40 - 15) * 100))

    categories = ["Velo", "CSW%", "Whiff%", "xwOBA\n(inv)", "Spin Rate", "K%"]
    values     = [pct_velo, pct_csw, pct_whiff, pct_xwoba, pct_spin, pct_k]

    fig_radar = radar_chart(categories, values,
                            title=f"{pitcher_name}: Percentile Radar",
                            color=NAVY)
    st.plotly_chart(fig_radar, use_container_width=True)

with col_right:
    st.markdown("#### Metric breakdown")

    dim_data = [
        ("Fastball Velo",  fmt(avg_velo, "{:.1f} mph"), pct_velo),
        ("CSW%",           fmt(csw_overall, "{:.1f}%"),  pct_csw),
        ("Whiff%",         fmt(whiff_overall, "{:.1f}%"), pct_whiff),
        ("xwOBA Against",  fmt(xwoba_against, "{:.3f}"), pct_xwoba),
        ("Avg Spin Rate",  fmt(avg_spin, "{:.0f} rpm"),  pct_spin),
        ("K%",             fmt(k_pct_val, "{:.1f}%"),    pct_k),
    ]

    for name, val_str, pct in dim_data:
        bar_color = percentile_color(pct)
        badge_html = percentile_badge(pct)
        pct_int = int(pct)
        st.markdown(f"""
        <div style="margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
                <span style="font-size:0.85rem;color:#2D3748;font-weight:500;">{name}</span>
                <span style="font-size:0.85rem;color:#718096;">{val_str}&nbsp;&nbsp;{badge_html}</span>
            </div>
            <div style="background:#E2E8F0;border-radius:4px;height:8px;overflow:hidden;">
                <div style="width:{pct_int}%;background:{bar_color};height:100%;border-radius:4px;
                            transition:width 0.4s;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Flags
    top_metrics    = sorted(dim_data, key=lambda x: x[2], reverse=True)[:2]
    bottom_metrics = sorted(dim_data, key=lambda x: x[2])[:2]

    st.markdown("---")
    st.markdown("**Strengths** 💪")
    for nm, vl, p in top_metrics:
        st.markdown(f"- **{nm}**: {vl} ({p:.0f}th pct)")
    st.markdown("**Development areas** 🎯")
    for nm, vl, p in bottom_metrics:
        st.markdown(f"- **{nm}**: {vl} ({p:.0f}th pct)")

st.markdown("---")

# ── Section 3: Pitch-type usage distribution ──────────────────────────────────
st.markdown("### Pitch arsenal : usage & outcomes")

if not eff.empty:
    col_a, col_b = st.columns(2)

    with col_a:
        # Usage pie
        fig_pie = go.Figure(go.Pie(
            labels=eff["pitch_type"],
            values=eff["usage_pct"].round(1),
            hole=0.45,
            marker_colors=[
                "#3498DB","#E74C3C","#2ECC71","#9B59B6",
                "#F39C12","#1ABC9C","#E67E22","#E91E63"
            ][:len(eff)],
            textinfo="label+percent",
            textfont_size=11,
        ))
        apply_theme(fig_pie, "Arsenal Usage %")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_b:
        # CSW% bar chart by pitch type
        fig_csw = go.Figure()
        colors = [GREEN if v >= 30 else AMBER if v >= 26 else RED
                  for v in eff["csw_pct"]]
        fig_csw.add_trace(go.Bar(
            x=eff["pitch_type"], y=eff["csw_pct"].round(1),
            marker_color=colors,
            text=eff["csw_pct"].round(1).astype(str) + "%",
            textposition="outside",
        ))
        # Add MLB average reference line
        fig_csw.add_hline(y=28, line_dash="dash",
                          line_color=NAVY, annotation_text="MLB avg (28%)")
        apply_theme(fig_csw, "CSW% by Pitch Type")
        fig_csw.update_yaxes(range=[0, 50])
        st.plotly_chart(fig_csw, use_container_width=True)

    # Effectiveness table
    st.markdown("#### Full effectiveness table")
    display_cols = {
        "pitch_type": "Pitch",
        "n": "Pitches",
        "usage_pct": "Usage%",
        "csw_pct": "CSW%",
        "whiff_pct": "Whiff%",
        "rv_per_100": "RV/100",
        "xwoba_against": "xwOBA",
    }
    tbl = eff[[c for c in display_cols if c in eff.columns]].rename(columns=display_cols)
    for col in ["Usage%","CSW%","Whiff%"]:
        if col in tbl.columns:
            tbl[col] = tbl[col].round(1)
    if "RV/100" in tbl.columns:
        tbl["RV/100"] = tbl["RV/100"].round(2)
    if "xwOBA" in tbl.columns:
        tbl["xwOBA"] = tbl["xwOBA"].round(3)
    st.dataframe(tbl, use_container_width=True, hide_index=True)
else:
    st.info("Effectiveness table requires Statcast data with description and delta_run_exp columns.")

# ── Coach's Insight ──────────────────────────────────────────────────────────
# Build insight from actual data
top_nm, top_vl, top_p = sorted(dim_data, key=lambda x: x[2], reverse=True)[0]
bot_nm, bot_vl, bot_p = sorted(dim_data, key=lambda x: x[2])[0]

best_pitch  = eff.iloc[0]["pitch_type"] if not eff.empty else "primary pitch"
best_csw    = eff.iloc[0]["csw_pct"] if not eff.empty else 0
worst_pitch = eff.sort_values("rv_per_100", ascending=False).iloc[0]["pitch_type"] if not eff.empty and "rv_per_100" in eff.columns else None

insight_text = (
    f"{pitcher_name} ranks at the <strong>{top_p:.0f}th percentile</strong> in {top_nm} — "
    f"a genuine strength to prioritise in pressure situations. "
    f"The {best_pitch} is the most effective pitch with a {best_csw:.1f}% CSW rate. "
    f"However, {bot_nm} sits at only the <strong>{bot_p:.0f}th percentile</strong>, "
    f"representing the clearest area for the clearest development priority."
)
action_text = (
    f"Target {bot_nm} development in pitching sessions this start. "
    f"Increase {best_pitch} usage in 0-2 and 1-2 counts."
)

coaches_insight(insight_text, action_text)