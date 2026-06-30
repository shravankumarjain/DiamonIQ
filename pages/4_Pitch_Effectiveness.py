"""
Diamond IQ — Page 4: Pitch Effectiveness
Answers: "Which pitches are generating outs and which are hurting us?"
Output: Run Value/100, CSW%, whiff rate, xwOBA per pitch; trend over season
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.components import (
    metric_glossary_expander, pitch_legend_strip,
    inject_css, page_header, metric_row, coaches_insight, apply_theme,
    NAVY, GOLD, GREEN, RED, AMBER, SURFACE, MUTED,
    require_pitcher, load_statcast, pitch_color, pitch_effectiveness,
)
from config.settings import SEASON

inject_css()

if not require_pitcher(st.session_state):
    st.stop()

pitcher_name = st.session_state["selected_pitcher_name"]

page_header(
    "Pitch Effectiveness",
    f"{pitcher_name} · Run Value · CSW% · xwOBA · Whiff rate | pitch by pitch",
    "📊",
)

metric_glossary_expander(["CSW%", "Whiff%", "RV/100", "xwOBA"])

df = load_statcast(st.session_state)
if df is None:
    st.stop()

eff = pitch_effectiveness(df)

if eff.empty:
    st.info("Pitch effectiveness data requires Statcast columns: "
            "pitch_type, description, delta_run_exp.")
    st.stop()

st.markdown(pitch_legend_strip(eff["pitch_type"].tolist()), unsafe_allow_html=True)

# ── Section 1: Top-level cards ────────────────────────────────────────────────
st.markdown("### Season-level effectiveness")

# Best and worst pitches by Run Value/100
if "rv_per_100" in eff.columns:
    eff_valid = eff.dropna(subset=["rv_per_100"])
    if not eff_valid.empty:
        best_pt  = eff_valid.loc[eff_valid["rv_per_100"].idxmin()]   # most negative = best for pitcher
        worst_pt = eff_valid.loc[eff_valid["rv_per_100"].idxmax()]

        best_name  = best_pt["pitch_type"]
        worst_name = worst_pt["pitch_type"]
        best_rv    = best_pt["rv_per_100"]
        worst_rv   = worst_pt["rv_per_100"]
    else:
        best_name = worst_name = "—"
        best_rv = worst_rv = np.nan
else:
    best_name = worst_name = "—"
    best_rv = worst_rv = np.nan

overall_csw  = df["is_csw"].mean() * 100  if "is_csw"  in df.columns else np.nan
overall_whiff = (df["is_whiff"].sum() / df["is_swing"].sum() * 100
                 if "is_swing" in df.columns and df["is_swing"].sum() > 0 else np.nan)
overall_xwoba = (df["estimated_woba_using_speedangle"].mean()
                 if "estimated_woba_using_speedangle" in df.columns else np.nan)

def fmt(v, f="{:.2f}"):
    try: return f.format(float(v))
    except: return "—"

cards = [
    {"label": "Best pitch (RV/100)",
     "value": f"{best_name}",
     "sub": fmt(best_rv, "{:+.2f}") + " runs / 100",
     "status": "good"},
    {"label": "Worst pitch (RV/100)",
     "value": f"{worst_name}",
     "sub": fmt(worst_rv, "{:+.2f}") + " runs / 100",
     "status": "bad"},
    {"label": "Overall CSW%",
     "value": fmt(overall_csw, "{:.1f}%"),
     "sub": "Called strikes + whiffs",
     "status": "good" if not pd.isna(overall_csw) and overall_csw >= 30 else
               "warn" if not pd.isna(overall_csw) and overall_csw >= 26 else "bad"},
    {"label": "Overall Whiff%",
     "value": fmt(overall_whiff, "{:.1f}%"),
     "sub": "Swings & misses / swings",
     "status": "good" if not pd.isna(overall_whiff) and overall_whiff >= 28 else
               "warn" if not pd.isna(overall_whiff) else "neutral"},
    {"label": "xwOBA Against",
     "value": fmt(overall_xwoba, "{:.3f}"),
     "sub": "Expected weighted OBA",
     "status": "good" if not pd.isna(overall_xwoba) and overall_xwoba <= 0.290 else
               "warn" if not pd.isna(overall_xwoba) and overall_xwoba <= 0.320 else "bad"},
]
metric_row(cards)

st.markdown("---")

# ── Section 2: Run Value chart ────────────────────────────────────────────────
st.markdown("### Run Value per 100 pitches")
st.caption(
    "**RV/100** measures runs saved (negative = good) or surrendered (positive = bad) "
    "per 100 pitches, vs the expected outcome in identical game states. "
    "This is the metric MLB front offices use to evaluate pitch quality. "
    "MLB average = 0.00."
)

if "rv_per_100" in eff.columns:
    eff_rv = eff.dropna(subset=["rv_per_100"]).sort_values("rv_per_100")

    colors_rv = [GREEN if v < -0.5 else AMBER if v < 0 else RED for v in eff_rv["rv_per_100"]]
    fig_rv = go.Figure()
    fig_rv.add_trace(go.Bar(
        x=eff_rv["pitch_type"],
        y=eff_rv["rv_per_100"].round(2),
        marker_color=colors_rv,
        text=eff_rv["rv_per_100"].round(2).apply(lambda x: f"{x:+.2f}"),
        textposition="outside",
    ))
    fig_rv.add_hline(y=0, line_color=NAVY, line_width=1.5,
                     annotation_text="MLB avg (0.00)")
    apply_theme(fig_rv, "Run Value per 100 Pitches by Pitch Type")
    fig_rv.update_yaxes(title="RV / 100 pitches (negative = saves runs)")
    st.plotly_chart(fig_rv, use_container_width=True)
else:
    st.info("Run Value data requires delta_run_exp in Statcast. Available when pybaseball data is loaded.")

st.markdown("---")

# ── Section 3: CSW% vs Whiff% scatter ────────────────────────────────────────
st.markdown("### CSW% vs Whiff% : pitch quality quadrant")
st.caption(
    "Top-right = elite (high zone strikes + generates swings & misses). "
    "Bottom-left = neutral/contact pitch. Size = usage."
)

if "csw_pct" in eff.columns and "whiff_pct" in eff.columns:
    fig_quad = go.Figure()

    # Quadrant reference lines
    fig_quad.add_hline(y=28, line_dash="dash", line_color="#CBD5E0",
                       annotation_text="Avg whiff% (28)")
    fig_quad.add_vline(x=28, line_dash="dash", line_color="#CBD5E0",
                       annotation_text="Avg CSW% (28)")

    # Quadrant shading
    for x0, x1, y0, y1, label, col in [
        (28, 55, 28, 55, "Elite", "rgba(46,204,113,0.07)"),
        (0,  28, 28, 55, "Batter's count pitch", "rgba(231,76,60,0.05)"),
        (28, 55, 0,  28, "Command pitch", "rgba(243,156,18,0.05)"),
        (0,  28, 0,  28, "Hittable", "rgba(231,76,60,0.07)"),
    ]:
        fig_quad.add_shape(type="rect",
                           x0=x0, x1=x1, y0=y0, y1=y1,
                           fillcolor=col, line_width=0)

    for _, row in eff.iterrows():
        pt    = row["pitch_type"]
        c_pct = row["csw_pct"]
        w_pct = row["whiff_pct"]
        usage = row["usage_pct"]
        color = pitch_color(pt)

        fig_quad.add_trace(go.Scatter(
            x=[c_pct], y=[w_pct],
            mode="markers+text",
            marker=dict(size=max(8, usage * 1.5), color=color,
                        opacity=0.85, line=dict(color="white", width=1.5)),
            text=[pt], textposition="top center",
            textfont=dict(size=11),
            name=pt,
        ))

    apply_theme(fig_quad, "Pitch Quality : CSW% vs Whiff%")
    fig_quad.update_xaxes(title="CSW%", range=[0, 55])
    fig_quad.update_yaxes(title="Whiff%", range=[0, 60])
    fig_quad.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig_quad, use_container_width=True)

st.markdown("---")

# ── Section 4: Full effectiveness table ───────────────────────────────────────
st.markdown("### Full effectiveness table")

display_eff = eff.copy()
numeric_cols = ["usage_pct", "csw_pct", "whiff_pct", "cs_pct", "rv_per_100", "xwoba_against"]
for c in numeric_cols:
    if c in display_eff.columns:
        display_eff[c] = pd.to_numeric(display_eff[c], errors="coerce").round(
            3 if c in ["rv_per_100","xwoba_against"] else 1
        )

rename = {
    "pitch_type": "Pitch",
    "n": "Pitches",
    "usage_pct": "Usage%",
    "csw_pct": "CSW%",
    "whiff_pct": "Whiff%",
    "cs_pct": "K-strike%",
    "rv_per_100": "RV/100",
    "xwoba_against": "xwOBA",
}
display_eff = display_eff[[c for c in rename if c in display_eff.columns]].rename(columns=rename)

# Colour-code RV/100
def rv_style(v):
    try:
        f = float(v)
        if f < -0.5: return "background-color: #d4edda; color: #155724;"
        if f < 0:    return "background-color: #fff3cd; color: #856404;"
        return "background-color: #f8d7da; color: #721c24;"
    except:
        return ""

st.dataframe(display_eff, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Section 5: xwOBA trend over season ───────────────────────────────────────
st.markdown("### xwOBA trend over the season")
st.caption("Is the pitcher getting better or worse as the season progresses?")

if "game_date" in df.columns and "estimated_woba_using_speedangle" in df.columns:
    trend = (
        df.groupby("game_date")["estimated_woba_using_speedangle"]
        .mean().reset_index()
        .sort_values("game_date")
    )
    trend.columns = ["game_date", "xwoba"]
    trend["rolling_5"] = trend["xwoba"].rolling(5, min_periods=1).mean()

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=trend["game_date"], y=trend["xwoba"],
        mode="markers", marker=dict(color=NAVY, size=5, opacity=0.4),
        name="Per outing", showlegend=True,
    ))
    fig_trend.add_trace(go.Scatter(
        x=trend["game_date"], y=trend["rolling_5"],
        mode="lines", line=dict(color=RED, width=2.5),
        name="5-start rolling avg",
    ))
    # Reference band
    fig_trend.add_hrect(y0=0.240, y1=0.290,
                        fillcolor="rgba(46,204,113,0.1)",
                        line_width=0, annotation_text="Elite zone",
                        annotation_position="top left")
    fig_trend.add_hrect(y0=0.320, y1=0.400,
                        fillcolor="rgba(231,76,60,0.08)",
                        line_width=0, annotation_text="Concern zone",
                        annotation_position="top left")
    apply_theme(fig_trend, "xwOBA Against _ Season Trend")
    fig_trend.update_yaxes(title="xwOBA against", range=[0.150, 0.500])
    st.plotly_chart(fig_trend, use_container_width=True)
else:
    st.info("Season trend requires game_date and estimated_woba_using_speedangle columns.")

# ── Coach's Insight ──────────────────────────────────────────────────────────
best_str  = f"**{best_name}** is the most valuable pitch ({fmt(best_rv, '{:+.2f}')} RV/100)" if best_name != "—" else ""
worst_str = f"**{worst_name}** is costing runs ({fmt(worst_rv, '{:+.2f}')} RV/100). Reduce usage" if worst_name != "—" else ""

insight = (
    f"{pitcher_name} generates a {fmt(overall_csw,'{:.1f}')}% CSW rate with "
    f"{fmt(overall_whiff,'{:.1f}')}% whiff rate. "
    f"{best_str}. {worst_str}."
)
action = (
    f"Increase {best_name} usage in two-strike counts. "
    f"Reduce {worst_name} usage against left-handed batters where possible."
    if best_name != "—" and worst_name != "—"
    else "Analyse two-strike pitch selection in the next pitching session."
)

coaches_insight(insight, action)