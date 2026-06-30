"""
Diamond IQ — Page 3: Zone Intelligence
Answers: "Is he hitting his spots? Where is he leaking pitches?"
Output: Strike zone KDE heatmaps by pitch type / count / handedness + worst zone flags
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.components import (
    metric_glossary_expander, pitch_legend_strip,
    inject_css, page_header, metric_row, coaches_insight, apply_theme,
    add_strike_zone, NAVY, GOLD, GREEN, RED, AMBER, SURFACE, MUTED,
    require_pitcher, load_statcast, pitch_color, PITCH_COLORS,
)
from config.settings import SEASON

inject_css()

if not require_pitcher(st.session_state):
    st.stop()

pitcher_name = st.session_state["selected_pitcher_name"]

page_header(
    "Zone Intelligence",
    f"{pitcher_name} · Location heatmaps by pitch type, count & handedness",
    "📍",
)

metric_glossary_expander(["CSW%", "Whiff%"])

df = load_statcast(st.session_state)
if df is None:
    st.stop()

# Check we have location data
if "plate_x" not in df.columns or "plate_z" not in df.columns:
    st.error("Pitch location data (plate_x / plate_z) not available in Statcast data.")
    st.stop()

df_loc = df.dropna(subset=["plate_x", "plate_z"]).copy()

# Construct "count" column from balls/strikes if Statcast didn't provide it directly.
# Statcast natively returns separate `balls` and `strikes` integer columns, never a
# combined "count" string — this builds it so downstream count-based analysis works.
if "count" not in df_loc.columns and {"balls", "strikes"}.issubset(df_loc.columns):
    df_loc["count"] = (
        df_loc["balls"].astype("Int64").astype(str) + "-" +
        df_loc["strikes"].astype("Int64").astype(str)
    )

pitch_types = sorted(df_loc["pitch_type"].unique().tolist())
counts_avail = sorted(df_loc["count"].unique().tolist()) if "count" in df_loc.columns else []
hands_avail  = sorted(df_loc["stand"].unique().tolist()) if "stand" in df_loc.columns else ["All"]

st.markdown(pitch_legend_strip(pitch_types), unsafe_allow_html=True)

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("**Zone filters**")
    zone_pitch = st.selectbox(
        "Pitch type",
        options=["All"] + pitch_types,
        help="Filter heatmap to a specific pitch.",
    )
    zone_hand = st.selectbox(
        "Batter handedness",
        options=["All"] + [h for h in hands_avail if h in ["L", "R"]],
        help="vs Left-handed or Right-handed batters.",
    )
    zone_outcome = st.selectbox(
        "Outcome filter",
        options=["All pitches", "Swings only", "Whiffs only",
                 "Called strikes only", "Balls only", "Hits only"],
    )

# Apply filters
df_filt = df_loc.copy()
if zone_pitch != "All":
    df_filt = df_filt[df_filt["pitch_type"] == zone_pitch]
if zone_hand != "All":
    df_filt = df_filt[df_filt["stand"] == zone_hand]

outcome_map = {
    "Swings only":         "is_swing",
    "Whiffs only":         "is_whiff",
    "Called strikes only": "is_called_strike",
    "Balls only":          "is_ball",
}
if zone_outcome in outcome_map:
    col = outcome_map[zone_outcome]
    if col in df_filt.columns:
        df_filt = df_filt[df_filt[col] == True]
elif zone_outcome == "Hits only" and "events" in df_filt.columns:
    df_filt = df_filt[df_filt["events"].isin(
        ["single","double","triple","home_run","field_error"])]

# ── Section 1: Summary cards ──────────────────────────────────────────────────
st.markdown("### Location summary")

in_zone = df_filt["in_zone"].sum() if "in_zone" in df_filt.columns else 0
total_f = len(df_filt)
zone_pct = in_zone / total_f * 100 if total_f > 0 else 0

avg_x = df_filt["plate_x"].mean()
avg_z = df_filt["plate_z"].mean()

# Chase rate (out-of-zone swings / out-of-zone pitches)
if "in_zone" in df_filt.columns and "is_swing" in df_filt.columns:
    ooz = df_filt[df_filt["in_zone"] == False]
    chase_pct = ooz["is_swing"].mean() * 100 if len(ooz) > 0 else 0.0
else:
    chase_pct = 0.0

# Zone whiff rate
if "in_zone" in df_filt.columns and "is_whiff" in df_filt.columns:
    in_z = df_filt[df_filt["in_zone"] == True]
    zone_whiff = in_z["is_swing"].mean() * 100 if "is_swing" in in_z.columns and len(in_z) > 0 else 0
else:
    zone_whiff = 0.0

cards = [
    {"label": "Zone%",
     "value": f"{zone_pct:.1f}%",
     "sub": "Pitches in strike zone",
     "status": "good" if zone_pct >= 45 else "warn" if zone_pct >= 38 else "bad"},
    {"label": "Chase rate",
     "value": f"{chase_pct:.1f}%",
     "sub": "O-zone swings / O-zone pitches",
     "status": "good" if chase_pct >= 30 else "warn" if chase_pct >= 24 else "bad"},
    {"label": "Zone whiff%",
     "value": f"{zone_whiff:.1f}%",
     "sub": "Whiffs on in-zone pitches",
     "status": "good" if zone_whiff >= 22 else "warn" if zone_whiff >= 15 else "bad"},
    {"label": "Pitches shown",
     "value": f"{total_f:,}",
     "sub": f"Avg x:{avg_x:.2f} z:{avg_z:.2f}",
     "status": "neutral"},
]
metric_row(cards)

st.markdown("---")

# ── Section 2: KDE heatmap ────────────────────────────────────────────────────
st.markdown("### Pitch location heatmap")

def build_kde_heatmap(data: pd.DataFrame, title: str) -> go.Figure:
    """Build a 2D KDE density heatmap of pitch locations."""
    if len(data) < 10:
        return None

    x_vals = data["plate_x"].clip(-2.5, 2.5)
    z_vals = data["plate_z"].clip(0.5, 5.0)

    # 2D histogram as KDE proxy
    fig = go.Figure()

    fig.add_trace(go.Histogram2dContour(
        x=x_vals, y=z_vals,
        colorscale=[
            [0.0,  "rgba(255,255,255,0)"],
            [0.15, "rgba(11,61,145,0.15)"],
            [0.5,  "rgba(11,61,145,0.55)"],
            [0.75, "rgba(232,185,35,0.75)"],
            [1.0,  "rgba(231,76,60,0.95)"],
        ],
        contours=dict(coloring="heatmap"),
        showscale=True,
        colorbar=dict(title="Density", tickfont=dict(size=9)),
        ncontours=20,
        line=dict(width=0),
    ))

    # Add individual pitch dots (sample)
    sample = data.sample(min(300, len(data)), random_state=42)
    fig.add_trace(go.Scatter(
        x=sample["plate_x"], y=sample["plate_z"],
        mode="markers",
        marker=dict(size=3, color="rgba(0,0,0,0.2)"),
        showlegend=False,
    ))

    # Strike zone box
    fig.add_shape(type="rect",
                  x0=-0.83, x1=0.83, y0=1.5, y1=3.5,
                  line=dict(color=NAVY, width=2),
                  fillcolor="rgba(0,0,0,0)")

    # Zone quadrant labels
    for xi, xl in [(-0.42, "In"), (0.42, "Out")]:
        for zi, zl in [(2.0, "Low"), (3.0, "High")]:
            fig.add_annotation(x=xi, y=zi, text=zl[0],
                               font=dict(size=8, color="rgba(0,0,0,0.3)"),
                               showarrow=False)

    # Home plate triangle
    fig.add_shape(type="path",
                  path="M -0.83 0.2 L 0.83 0.2 L 0.5 0.5 L 0 0.65 L -0.5 0.5 Z",
                  line_color="#718096", fillcolor="#E2E8F0", line_width=1)

    apply_theme(fig, title)
    fig.update_xaxes(title="Plate X (ft from centre, catcher's view)",
                     range=[-2.5, 2.5], zeroline=False)
    fig.update_yaxes(title="Plate Z (ft from ground)",
                     range=[0.2, 5.0], zeroline=False)
    fig.update_layout(height=420)
    return fig

# Main heatmap
heatmap_title = (
    f"{'All pitches' if zone_pitch == 'All' else zone_pitch} : "
    f"vs {'all batters' if zone_hand == 'All' else ('LHB' if zone_hand == 'L' else 'RHB')} — "
    f"{zone_outcome}"
)

fig_heat = build_kde_heatmap(df_filt, heatmap_title)
if fig_heat:
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.info("Not enough data for heatmap with current filters. Adjust filters above.")

st.markdown("---")

# ── Section 3: By-count breakdown ────────────────────────────────────────────
st.markdown("### Zone% by count")
st.caption(
    "Zone% drops in pitcher's counts signal poor command under pressure. "
    "High zone% in 3-ball counts means the pitcher is forced into the zone."
)

if "count" in df_loc.columns and "in_zone" in df_loc.columns:
    count_stats = (
        df_loc.groupby("count")
        .agg(
            total=("in_zone", "count"),
            in_zone_n=("in_zone", "sum"),
        )
        .reset_index()
    )
    count_stats["zone_pct"] = count_stats["in_zone_n"] / count_stats["total"] * 100
    count_stats = count_stats[count_stats["total"] >= 10].sort_values("count")

    if not count_stats.empty:
        fig_count = go.Figure()
        colors_count = [
            GREEN if v >= 50 else AMBER if v >= 40 else RED
            for v in count_stats["zone_pct"]
        ]
        fig_count.add_trace(go.Bar(
            x=count_stats["count"],
            y=count_stats["zone_pct"].round(1),
            marker_color=colors_count,
            text=count_stats["zone_pct"].round(1).astype(str) + "%",
            textposition="outside",
        ))
        fig_count.add_hline(y=45, line_dash="dash",
                            line_color=NAVY, annotation_text="MLB target (45%)")
        apply_theme(fig_count, "Zone% by Ball-Strike Count")
        fig_count.update_yaxes(title="Zone%", range=[0, 80])
        fig_count.update_xaxes(title="Count (balls-strikes)")
        st.plotly_chart(fig_count, use_container_width=True)
    else:
        st.info("Insufficient data per count for this analysis.")
else:
    st.info("Count data not available.")

st.markdown("---")

# ── Section 4: Side-by-side vs LHB / RHB ─────────────────────────────────────
if "stand" in df_loc.columns:
    st.markdown("### Location split: vs LHB vs RHB")

    col_lhb, col_rhb = st.columns(2)

    for col_widget, hand_label, hand_code in [
        (col_lhb, "vs Left-handed batters", "L"),
        (col_rhb, "vs Right-handed batters", "R"),
    ]:
        with col_widget:
            sub = df_loc[df_loc["stand"] == hand_code]
            if zone_pitch != "All":
                sub = sub[sub["pitch_type"] == zone_pitch]

            fig_h = build_kde_heatmap(sub, f"{hand_label} (n={len(sub):,})")
            if fig_h:
                fig_h.update_layout(height=360)
                st.plotly_chart(fig_h, use_container_width=True)
            else:
                st.info(f"Insufficient data for {hand_label}.")

st.markdown("---")

# ── Coach's Insight ──────────────────────────────────────────────────────────
worst_count_str = ""
if "count" in df_loc.columns and "in_zone" in df_loc.columns:
    count_stats2 = (
        df_loc.groupby("count")
        .agg(in_zone_pct=("in_zone", "mean"))
        .reset_index()
    )
    count_stats2["in_zone_pct"] *= 100
    worst_idx = count_stats2["in_zone_pct"].idxmin()
    worst_count = count_stats2.loc[worst_idx, "count"]
    worst_pct   = count_stats2.loc[worst_idx, "in_zone_pct"]
    worst_count_str = (
        f"Command breaks down most in the <strong>{worst_count}</strong> count "
        f"({worst_pct:.1f}% zone rate). "
    )

insight = (
    f"Overall zone rate is <strong>{zone_pct:.1f}%</strong> "
    f"with a <strong>{chase_pct:.1f}%</strong> chase rate induced. "
    f"{worst_count_str}"
    f"{'Chase rate above 30% means location is elite batters are chasing out of the zone.' if chase_pct >= 30 else 'Improving chase rate is the primary command focus for the upcoming start.'}"
)
action = (
    f"Prioritise zone% in {worst_count_str.split('count')[0].replace('Command breaks down most in the','').strip() if worst_count_str else 'two-strike'} counts during side sessions. "
    f"Review release point on 'leaking' pitches."
)

coaches_insight(insight, action)