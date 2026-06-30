"""
Diamond IQ — Page 2: Arsenal Profile
Answers: "Is his stuff where it should be mechanically?"
Output: Movement profile scatter, spin efficiency, release point consistency, velocity trends
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
    require_pitcher, load_statcast, PITCH_COLORS,
    pitch_color, release_point_drift,
)
from config.settings import SEASON

inject_css()

if not require_pitcher(st.session_state):
    st.stop()

pitcher_name = st.session_state["selected_pitcher_name"]

page_header(
    "Arsenal Profile",
    f"{pitcher_name} · Velocity · Movement · Spin · Release consistency",
    "🎯",
)

metric_glossary_expander(["EV"])

df = load_statcast(st.session_state)
if df is None:
    st.stop()

pitch_types = sorted(df["pitch_type"].unique().tolist()) if "pitch_type" in df.columns else []

if not pitch_types:
    st.info("No pitch type data available.")
    st.stop()

st.markdown(pitch_legend_strip(pitch_types), unsafe_allow_html=True)

# ── Sidebar controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("**Arsenal filters**")
    selected_pitches = st.multiselect(
        "Show pitch types",
        options=pitch_types,
        default=pitch_types,
        help="Filter the movement chart to specific pitch types.",
    )

df_sel = df[df["pitch_type"].isin(selected_pitches)] if selected_pitches else df

# ── Section 1: Arsenal summary cards ─────────────────────────────────────────
st.markdown("### Velocity & spin summary")

cards = []
for pt in pitch_types[:5]:  # show top 5 by usage
    grp = df[df["pitch_type"] == pt]
    velo = grp["release_speed"].mean() if "release_speed" in grp.columns else np.nan
    spin = grp["release_spin_rate"].mean() if "release_spin_rate" in grp.columns else np.nan
    n    = len(grp)
    usage = n / len(df) * 100
    cards.append({
        "label": pt,
        "value": f"{velo:.1f} mph" if not pd.isna(velo) else "—",
        "sub": f"{spin:.0f} rpm · {usage:.0f}% usage" if not pd.isna(spin) else f"{usage:.0f}% usage",
        "status": "good" if not pd.isna(velo) and velo >= 93 else "neutral",
    })

if cards:
    metric_row(cards)

st.markdown("---")

# ── Section 2: Movement profile (pfx_x vs pfx_z) ─────────────────────────────
st.markdown("### Movement profile")
st.caption("Horizontal break (HB) vs induced vertical break (IVB) in inches. "
           "Ellipses represent 1-SD confidence regions per pitch type.")

col_mv, col_info = st.columns([1.6, 1])

with col_mv:
    fig_mv = go.Figure()

    for pt in selected_pitches:
        grp = df_sel[df_sel["pitch_type"] == pt]
        if grp.empty or "hb_in" not in grp.columns:
            continue

        hb  = grp["hb_in"].dropna()
        ivb = grp["ivb_in"].dropna() if "ivb_in" in grp.columns else pd.Series()
        if len(hb) < 5 or len(ivb) < 5:
            continue

        color = pitch_color(pt)

        # Scatter (sample to avoid overplotting)
        sample = grp.sample(min(200, len(grp)), random_state=42)
        fig_mv.add_trace(go.Scatter(
            x=sample["hb_in"], y=sample["ivb_in"] if "ivb_in" in sample.columns else sample["hb_in"],
            mode="markers",
            marker=dict(color=color, size=4, opacity=0.35),
            name=pt,
            legendgroup=pt,
            showlegend=True,
        ))

        # Centroid
        fig_mv.add_trace(go.Scatter(
            x=[hb.mean()], y=[ivb.mean()],
            mode="markers+text",
            marker=dict(color=color, size=12, symbol="circle",
                        line=dict(color="white", width=2)),
            text=[pt], textposition="top center",
            textfont=dict(size=11, color=color),
            legendgroup=pt,
            showlegend=False,
        ))

        # 1-SD ellipse
        try:
            theta = np.linspace(0, 2*np.pi, 60)
            std_x = hb.std(); std_y = ivb.std()
            ell_x = hb.mean() + std_x * np.cos(theta)
            ell_y = ivb.mean() + std_y * np.sin(theta)
            fig_mv.add_trace(go.Scatter(
                x=ell_x, y=ell_y,
                mode="lines",
                line=dict(color=color, width=1.5, dash="dot"),
                fill="toself", fillcolor=color.replace(")", ",0.06)").replace("rgb","rgba")
                              if "rgb" in color else color,
                legendgroup=pt, showlegend=False,
            ))
        except Exception:
            pass

    # Crosshairs
    fig_mv.add_hline(y=0, line_color="#CBD5E0", line_width=1)
    fig_mv.add_vline(x=0, line_color="#CBD5E0", line_width=1)

    apply_theme(fig_mv, "Pitch Movement Profile (RHB perspective)")
    fig_mv.update_xaxes(title="Horizontal break (in)", range=[-25, 25])
    fig_mv.update_yaxes(title="Induced vertical break (in)", range=[-20, 25])
    fig_mv.update_layout(height=450)
    st.plotly_chart(fig_mv, use_container_width=True)

with col_info:
    st.markdown("#### Movement averages")

    move_rows = []
    for pt in pitch_types:
        grp = df[df["pitch_type"] == pt]
        hb  = grp["hb_in"].mean()  if "hb_in"  in grp.columns else np.nan
        ivb = grp["ivb_in"].mean() if "ivb_in" in grp.columns else np.nan
        move_rows.append({"Pitch": pt,
                          "HB (in)": round(hb, 1) if not pd.isna(hb) else "—",
                          "IVB (in)": round(ivb, 1) if not pd.isna(ivb) else "—"})
    if move_rows:
        st.dataframe(pd.DataFrame(move_rows), use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("""
    **Reading this chart:**
    - **Right of 0** = arm-side run (cutter/sinker)
    - **Left of 0** = glove-side break (slider/curveball)
    - **Above 0** = positive IVB (rises vs gravity)
    - **Below 0** = drops below gravity baseline
    
    *Ellipses show 1 standard deviation — tighter = more consistent mechanics.*
    """)

st.markdown("---")

# ── Section 3: Spin Rate by Pitch Type ───────────────────────────────────────
st.markdown("### Spin rate distribution")
col_s1, col_s2 = st.columns(2)

with col_s1:
    if "release_spin_rate" in df.columns and "pitch_type" in df.columns:
        fig_spin = go.Figure()
        for pt in selected_pitches:
            grp = df[df["pitch_type"] == pt]["release_spin_rate"].dropna()
            if len(grp) < 10:
                continue
            fig_spin.add_trace(go.Box(
                y=grp, name=pt,
                marker_color=pitch_color(pt),
                boxpoints="outliers",
                line_width=1.5,
            ))
        apply_theme(fig_spin, "Spin Rate Distribution by Pitch")
        fig_spin.update_yaxes(title="Spin rate (rpm)")
        st.plotly_chart(fig_spin, use_container_width=True)
    else:
        st.info("Spin rate data not available.")

with col_s2:
    # Velocity over the season (rolling avg)
    if "game_date" in df.columns and "release_speed" in df.columns:
        daily_velo = (
            df.groupby("game_date")["release_speed"]
            .mean().reset_index()
            .sort_values("game_date")
        )
        daily_velo["rolling_7"] = daily_velo["release_speed"].rolling(7, min_periods=1).mean()

        fig_velo = go.Figure()
        fig_velo.add_trace(go.Scatter(
            x=daily_velo["game_date"], y=daily_velo["release_speed"],
            mode="markers", marker=dict(color=NAVY, size=5, opacity=0.4),
            name="Daily avg", showlegend=True,
        ))
        fig_velo.add_trace(go.Scatter(
            x=daily_velo["game_date"], y=daily_velo["rolling_7"],
            mode="lines", line=dict(color=GOLD, width=2.5),
            name="7-game rolling avg",
        ))
        apply_theme(fig_velo, "Velocity Trend : Season")
        fig_velo.update_yaxes(title="Avg velocity (mph)")
        st.plotly_chart(fig_velo, use_container_width=True)
    else:
        st.info("Date-stamped velocity data not available.")

st.markdown("---")

# ── Section 4: Release Point Consistency ──────────────────────────────────────
st.markdown("### Release point consistency")
st.caption(
    "A tight cluster signals repeatable mechanics. "
    "Drift > 1 inch from season baseline is a mechanical health flag "
    "(used by MLB teams for injury prevention monitoring)."
)

col_rp1, col_rp2 = st.columns([1.5, 1])

with col_rp1:
    if "release_pos_x" in df.columns and "release_pos_z" in df.columns:
        sample_rp = df_sel.sample(min(500, len(df_sel)), random_state=42)

        fig_rp = go.Figure()
        for pt in selected_pitches:
            grp = sample_rp[sample_rp["pitch_type"] == pt]
            if grp.empty:
                continue
            fig_rp.add_trace(go.Scatter(
                x=grp["release_pos_x"], y=grp["release_pos_z"],
                mode="markers",
                marker=dict(color=pitch_color(pt), size=5, opacity=0.5),
                name=pt,
            ))

        apply_theme(fig_rp, "Release Point Scatter (ft)")
        fig_rp.update_xaxes(title="Horizontal position (ft, negative = arm side)")
        fig_rp.update_yaxes(title="Vertical height (ft)")
        fig_rp.update_layout(height=380)
        st.plotly_chart(fig_rp, use_container_width=True)
    else:
        st.info("Release position data not available.")

with col_rp2:
    drift = release_point_drift(df)
    if drift:
        drift_x = drift.get("drift_x", 0)
        drift_z = drift.get("drift_z", 0)
        flag    = drift.get("flag", False)

        status_color = RED if flag else GREEN
        status_text  = "⚠️ Drift Detected" if flag else "✅ Consistent"

        st.markdown(f"""
        <div style="background:{SURFACE};border-radius:10px;padding:18px;
                    border-left:4px solid {status_color};">
            <div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase;
                        letter-spacing:0.07em;margin-bottom:8px;">Release point drift</div>
            <div style="font-size:1.4rem;font-weight:700;color:{status_color};
                        margin-bottom:10px;">{status_text}</div>
            <div style="font-size:0.88rem;margin-bottom:6px;">
                <b>Horizontal drift:</b> {drift_x:.2f} in
                {'&nbsp;⚠️' if drift_x > 1.0 else '&nbsp;✅'}
            </div>
            <div style="font-size:0.88rem;">
                <b>Vertical drift:</b> {drift_z:.2f} in
                {'&nbsp;⚠️' if drift_z > 1.0 else '&nbsp;✅'}
            </div>
            <div style="font-size:0.78rem;color:{MUTED};margin-top:12px;">
                Measured over last 5 starts vs season baseline.
                Threshold: &gt;1 inch = mechanical flag.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Release position data not available for drift analysis.")

# ── Coach's Insight ──────────────────────────────────────────────────────────
drift = release_point_drift(df)
flag_str = (
    f"Release point has drifted {drift.get('drift_x',0):.1f} in horizontally "
    f"and {drift.get('drift_z',0):.1f} in vertically from the season baseline  "
    f"review video for mechanical changes."
    if drift.get("flag")
    else "Release point is consistent with season baseline mechanics are stable."
)

# Find best and worst movement pitch
best_mv_pt = None
if "ivb_in" in df.columns:
    ivb_by_pt = df.groupby("pitch_type")["ivb_in"].mean().abs()
    if not ivb_by_pt.empty:
        best_mv_pt = ivb_by_pt.idxmax()

insight = (
    f"{pitcher_name}'s arsenal shows {'good' if not drift.get('flag') else 'some'} mechanical consistency. "
    f"{flag_str} "
    f"{'The ' + best_mv_pt + ' shows the most movement separation. Prioritise this pitch in tunneling sequences.' if best_mv_pt else ''}"
)
action = (
    "Check high-speed video from last 2 starts for mechanical drift."
    if drift.get("flag")
    else f"Mechanics are healthy. Focus on {pitch_types[0] if pitch_types else 'primary pitch'} command this start."
)

coaches_insight(insight, action)