"""
Diamond IQ — Page 6: Pitching Readiness Report  v3.0
Decision-first workload & fatigue analysis. All Plotly colors use rgba().
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.components import (
    metric_glossary_expander,
    inject_css, page_header, coaches_insight, apply_theme,
    section_header, stat_row, rgba,
    BG_CARD, BG_CARD2, BORDER, NAVY, GOLD, BLUE_ACC, GREEN, RED, AMBER,
    TEXT_PRI, TEXT_SEC, TEXT_MUT,
    require_pitcher, load_statcast,
    calculate_acwr, velocity_decay, release_point_drift,
)
from config.settings import SEASON

inject_css()

if not require_pitcher(st.session_state):
    st.stop()

pitcher_name = st.session_state["selected_pitcher_name"]

page_header(
    "Pitching Readiness Report",
    f"{pitcher_name} · Workload · Fatigue signals · Start recommendation",
    "🩺",
)

metric_glossary_expander(["ACWR", "EV"])

df = load_statcast(st.session_state)
if df is None:
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("**ACWR settings**")
    acute_w   = st.slider("Acute window (days)", 3, 14, 7,
                           help="Short-term load window. Standard = 7 days.")
    chronic_w = st.slider("Chronic window (days)", 14, 42, 28,
                           help="Long-term fitness baseline. Standard = 28 days.")
    st.caption("Safe zone: 0.8–1.3 (Gabbett 2016)")

# ── Compute signals ────────────────────────────────────────────────────────────
acwr_df     = calculate_acwr(df, acute_window=acute_w, chronic_window=chronic_w)
vd          = velocity_decay(df)
rd          = release_point_drift(df)

latest_acwr = acwr_df["acwr"].iloc[-1]      if not acwr_df.empty else float("nan")
latest_zone = acwr_df["acwr_zone"].iloc[-1] if not acwr_df.empty else "unknown"

velo_flag   = vd.get("flag", False)
drift_flag  = rd.get("flag", False)
acwr_flag   = latest_zone in ["caution","danger"]
flags       = sum([velo_flag, drift_flag, acwr_flag])

if latest_zone == "danger" or flags >= 2:
    readiness, read_col, read_bg = "HIGH RISK",    RED,      "danger"
    read_rec = "Limit to 75 pitches. Have long reliever ready by inning 4."
elif flags == 1 or latest_zone == "caution":
    readiness, read_col, read_bg = "MONITOR",      AMBER,    "caution"
    read_rec = "90-pitch limit. Pull if velocity drops >2 mph from first inning."
elif latest_zone == "underload":
    readiness, read_col, read_bg = "UNDERLOADED",  BLUE_ACC, "under"
    read_rec = "Pitcher may be under-prepared. Consider extended outing to build fitness."
else:
    readiness, read_col, read_bg = "READY TO START", GREEN,  "safe"
    read_rec = "All signals green. Standard pitch count management. Monitor after inning 6."

# ── Section 1: Readiness verdict ──────────────────────────────────────────────
section_header("PITCHING READINESS")

c_left, c_right = st.columns([1, 2.4])
icon = {"safe":"🟢","caution":"🟡","danger":"🔴","under":"🔵"}.get(read_bg,"⚪")

with c_left:
    st.markdown(
        f'<div class="tl-card {read_bg}" style="padding:28px 20px;">'
        f'<div style="font-size:2.8rem;margin-bottom:8px;">{icon}</div>'
        f'<div style="font-size:0.88rem;font-weight:700;color:{read_col};letter-spacing:0.06em;">{readiness}</div>'
        f'<div style="font-size:0.75rem;color:{TEXT_SEC};margin-top:6px;">'
        f'{flags} active signal{"s" if flags!=1 else ""}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

with c_right:
    st.markdown(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {read_col};'
        f'border-radius:8px;padding:16px 18px;height:100%;">'
        f'<div style="font-size:0.68rem;font-weight:700;color:{NAVY};text-transform:uppercase;'
        f'letter-spacing:0.09em;margin-bottom:8px;">Coach recommendation</div>'
        f'<div style="font-size:1.0rem;color:{TEXT_PRI};line-height:1.6;">{read_rec}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

_acwr_str = f"{latest_acwr:.2f}" if latest_acwr == latest_acwr else "—"
_slope    = vd.get("slope", 0)
_dx       = rd.get("drift_x", 0)
_dz       = rd.get("drift_z", 0)

stat_row([
    {"value": _acwr_str, "label": f"ACWR ({acute_w}d / {chronic_w}d)",
     "delta": f"{'⚠ ' if acwr_flag else '✓ '}{latest_zone.upper()}  ·  Safe: 0.80–1.30",
     "status": "bad" if acwr_flag else "good"},
    {"value": f"{abs(_slope):.2f} mph/inn", "label": "Velocity decay slope",
     "delta": "⚠ Fatigue detected" if velo_flag else "✓ Normal profile",
     "status": "bad" if velo_flag else "good"},
    {"value": f'H {_dx:.1f}"  V {_dz:.1f}"', "label": "Release point drift",
     "delta": "⚠ Mechanical change" if drift_flag else "✓ Consistent",
     "status": "bad" if drift_flag else "good"},
])

st.markdown("---")

# ── Section 2: Inning-by-inning velocity ──────────────────────────────────────
section_header("INNING-BY-INNING VELOCITY PROFILE")
st.caption(
    "The most actionable in-game fatigue signal. "
    "Coloured bars show velocity relative to first-inning peak. "
    "Drop below the red threshold = pull recommendation."
)

if vd and "by_inning" in vd and not vd["by_inning"].empty:
    by_inn = vd["by_inning"]
    slope  = vd.get("slope", 0)
    pval   = vd.get("pval", 1)
    peak   = by_inn["avg_velo"].iloc[0] if len(by_inn) > 0 else 92.0
    t_pull = peak - 2.0
    t_warn = peak - 1.0

    bar_colors = [RED if v < t_pull else AMBER if v < t_warn else GREEN
                  for v in by_inn["avg_velo"]]

    fig_v = go.Figure()
    fig_v.add_trace(go.Bar(
        x=by_inn["inning"], y=by_inn["avg_velo"].round(1),
        marker_color=bar_colors, marker_line_width=0,
        text=by_inn["avg_velo"].round(1), textposition="outside",
        textfont=dict(color=TEXT_SEC, size=10), width=0.6, name="Avg velocity",
    ))

    # Safe zone band
    fig_v.add_hrect(y0=t_pull, y1=by_inn["avg_velo"].max() + 3,
                    fillcolor=rgba(GREEN, 0.05), line_width=0)
    # Threshold lines — use rgba() not hex+alpha
    fig_v.add_hline(y=t_warn, line_dash="dash", line_color=AMBER, line_width=1.5,
                    annotation_text=f"Watch ({t_warn:.1f} mph)",
                    annotation_font=dict(color=AMBER, size=9))
    fig_v.add_hline(y=t_pull, line_dash="dash", line_color=RED, line_width=1.5,
                    annotation_text=f"Pull threshold ({t_pull:.1f} mph)",
                    annotation_font=dict(color=RED, size=9))
    fig_v.add_hline(y=peak, line_dash="dot", line_color=GREEN, line_width=1,
                    annotation_text=f"Peak ({peak:.1f} mph)",
                    annotation_font=dict(color=GREEN, size=9))

    if len(by_inn) >= 3:
        x_line = np.linspace(by_inn["inning"].min(), by_inn["inning"].max(), 50)
        y_line = by_inn["avg_velo"].mean() + slope * (x_line - by_inn["inning"].mean())
        fig_v.add_trace(go.Scatter(
            x=x_line, y=y_line, mode="lines",
            line=dict(color=RED if velo_flag else NAVY, width=2, dash="dot"),
            name=f"Trend ({slope:+.2f} mph/inn, p={pval:.2f})",
        ))

    apply_theme(fig_v, "")
    fig_v.update_xaxes(title="Inning", dtick=1)
    fig_v.update_yaxes(title="Avg velocity (mph)",
                       range=[max(80, by_inn["avg_velo"].min()-3),
                              by_inn["avg_velo"].max()+3])
    fig_v.update_layout(height=340, showlegend=True)
    st.plotly_chart(fig_v, use_container_width=True)

    if velo_flag:
        drop = abs(slope) * max(by_inn["inning"])
        st.markdown(
            f'<div style="background:#1c0a0a;border:1px solid {rgba(RED,0.4)};border-radius:8px;'
            f'padding:12px 16px;font-size:0.88rem;color:{TEXT_PRI};">'
            f'⚠️ <b>Fatigue detected:</b> Velocity trending {abs(slope):.2f} mph lower each inning '
            f'(approx {drop:.1f} mph total loss by inning {int(by_inn["inning"].max())}). '
            f'p-value = {pval:.3f}.</div>',
            unsafe_allow_html=True,
        )
else:
    st.info("Velocity decay requires release_speed and inning columns in Statcast data.")

st.markdown("---")

# ── Section 3: ACWR timeline ──────────────────────────────────────────────────
section_header("WORKLOAD HISTORY — ACWR TIMELINE")
st.caption(
    "Acute:Chronic Workload Ratio (Gabbett 2016). Safe zone 0.80–1.30. "
    "Dots are colour-coded by zone. Bar height = daily pitch count."
)

if not acwr_df.empty:
    zone_map = {"optimal": GREEN, "underload": BLUE_ACC, "caution": AMBER,
                "danger": RED, "unknown": TEXT_SEC}
    dot_colors = [zone_map.get(z, TEXT_SEC) for z in acwr_df["acwr_zone"]]

    fig_a = make_subplots(specs=[[{"secondary_y": True}]])
    fig_a.add_trace(go.Bar(
        x=acwr_df["game_date"], y=acwr_df["pitches"], name="Pitch count",
        marker_color=rgba(NAVY, 0.12), marker_line_width=0,
    ), secondary_y=True)
    fig_a.add_trace(go.Scatter(
        x=acwr_df["game_date"], y=acwr_df["acwr"].round(3),
        mode="lines", line=dict(color=rgba(NAVY, 0.4), width=1.5), showlegend=False,
    ), secondary_y=False)
    fig_a.add_trace(go.Scatter(
        x=acwr_df["game_date"], y=acwr_df["acwr"].round(3), mode="markers",
        marker=dict(color=dot_colors, size=8, line=dict(color="white", width=1.5)),
        name="ACWR (colour = zone)",
        customdata=acwr_df[["acwr_zone","pitches"]].values,
        hovertemplate="Date: %{x}<br>ACWR: %{y:.3f}<br>Zone: %{customdata[0]}<br>Pitches: %{customdata[1]}<extra></extra>",
    ), secondary_y=False)

    # Safe zone — rgba() not hex+alpha
    fig_a.add_hrect(y0=0.8,  y1=1.3, fillcolor=rgba(GREEN, 0.05), line_width=0,
                    annotation_text="Safe zone", annotation_position="top left",
                    annotation_font=dict(color=GREEN, size=9))
    fig_a.add_hrect(y0=1.3,  y1=3.0, fillcolor=rgba(RED, 0.04), line_width=0,
                    annotation_text="Elevated risk", annotation_position="top right",
                    annotation_font=dict(color=RED, size=9))

    apply_theme(fig_a, "")
    max_acwr = acwr_df["acwr"].dropna().max() if not acwr_df["acwr"].dropna().empty else 2.0
    fig_a.update_yaxes(title_text="ACWR ratio", range=[0, min(3.0, max_acwr*1.3+0.3)],
                       secondary_y=False)
    fig_a.update_yaxes(title_text="Pitch count", secondary_y=True,
                       range=[0, acwr_df["pitches"].max() * 4], showgrid=False)
    fig_a.update_layout(height=320, showlegend=True)
    st.plotly_chart(fig_a, use_container_width=True)

    recent = acwr_df.tail(8).copy()
    recent["game_date"]    = recent["game_date"].astype(str)
    recent["acwr"]         = recent["acwr"].round(3)
    recent["Status"]       = recent["acwr_zone"].str.upper()
    recent["acute_load"]   = recent["acute_load"].round(1)
    recent["chronic_load"] = recent["chronic_load"].round(1)
    show = recent[["game_date","pitches","acute_load","chronic_load","acwr","Status"]].rename(
        columns={"game_date":"Date","pitches":"Pitches",
                 "acute_load":"Acute","chronic_load":"Chronic"})
    st.dataframe(show, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Section 4: Release point health ──────────────────────────────────────────
section_header("RELEASE POINT HEALTH")
st.caption(
    "Release point consistency is the most sensitive mechanical health proxy in Statcast. "
    "Drift >1 inch from personal baseline precedes velocity loss by 1–2 starts."
)

if rd and "by_game" in rd and not rd["by_game"].empty:
    bg2    = rd["by_game"]
    bx     = rd.get("baseline_x", 0)
    bz     = rd.get("baseline_z", 0)
    dx     = rd.get("drift_x", 0)
    dz     = rd.get("drift_z", 0)
    flag   = rd.get("flag", False)
    f_col  = RED if flag else GREEN
    f_txt  = "⚠️ Drift detected" if flag else "✅ Consistent"

    col1, col2 = st.columns([1.8, 1])
    with col1:
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatter(
            x=bg2["game_date"], y=bg2["release_pos_x"].round(3),
            mode="lines+markers", line=dict(color=BLUE_ACC, width=2),
            marker=dict(size=5), name="Horizontal (x)",
        ))
        fig_r.add_trace(go.Scatter(
            x=bg2["game_date"], y=bg2["release_pos_z"].round(3),
            mode="lines+markers", line=dict(color=GOLD, width=2),
            marker=dict(size=5), name="Vertical (z)",
        ))
        fig_r.add_hline(y=bx, line_dash="dot", line_color=rgba(BLUE_ACC, 0.4), line_width=1)
        fig_r.add_hline(y=bz, line_dash="dot", line_color=rgba(GOLD, 0.4),     line_width=1)
        apply_theme(fig_r, "")
        fig_r.update_yaxes(title="Position (ft)")
        fig_r.update_layout(height=280)
        st.plotly_chart(fig_r, use_container_width=True)

    with col2:
        dx_col = RED if dx > 1.0 else GREEN
        dz_col = RED if dz > 1.0 else GREEN
        st.markdown(
            f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-left:3px solid {f_col};'
            f'border-radius:8px;padding:20px;">'
            f'<div style="font-size:0.70rem;font-weight:700;color:{NAVY};text-transform:uppercase;'
            f'letter-spacing:0.08em;margin-bottom:10px;">Mechanical status</div>'
            f'<div style="font-size:1.1rem;font-weight:700;color:{f_col};margin-bottom:14px;">{f_txt}</div>'
            f'<div style="font-size:0.88rem;color:{TEXT_PRI};margin-bottom:6px;">'
            f'Horizontal drift: <b style="color:{dx_col};">{dx:.2f}"</b></div>'
            f'<div style="font-size:0.88rem;color:{TEXT_PRI};margin-bottom:14px;">'
            f'Vertical drift: <b style="color:{dz_col};">{dz:.2f}"</b></div>'
            f'<div style="font-size:0.75rem;color:{TEXT_SEC};line-height:1.5;">'
            f'Last 5 starts vs season average.<br>Threshold: &gt;1 inch = flag.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
else:
    st.info("Release point data requires release_pos_x and release_pos_z columns.")

st.markdown("---")

# ── Section 5: Season velocity trend ─────────────────────────────────────────
section_header("SEASON VELOCITY TREND — CUMULATIVE FATIGUE")
st.caption("Weekly average velocity vs season peak. Drops >1.5 mph from peak signal cumulative arm fatigue.")

if "game_date" in df.columns and "release_speed" in df.columns:
    df2 = df.copy()
    df2["week"] = pd.to_datetime(df2["game_date"]).dt.to_period("W").dt.start_time
    weekly = df2.groupby("week")["release_speed"].mean().reset_index()
    weekly.columns = ["week","avg_velo"]
    season_peak = weekly["avg_velo"].max()
    weekly["delta"] = weekly["avg_velo"] - season_peak

    fig_sv = go.Figure()
    bar_c  = [RED if v < -1.5 else AMBER if v < -0.5 else GREEN for v in weekly["delta"]]
    fig_sv.add_trace(go.Bar(
        x=weekly["week"], y=weekly["delta"].round(2),
        marker_color=bar_c, marker_line_width=0,
        name="Δ from season peak",
        hovertemplate="Week: %{x}<br>Δ from peak: %{y:.1f} mph<extra></extra>",
    ))
    fig_sv.add_hline(y=0,    line_color=rgba(GREEN, 0.6), line_dash="dot", line_width=1)
    fig_sv.add_hline(y=-1.5, line_color=RED,              line_dash="dash", line_width=1,
                     annotation_text="Concern threshold (−1.5 mph)",
                     annotation_font=dict(color=RED, size=9))
    apply_theme(fig_sv, "")
    fig_sv.update_xaxes(title="")
    fig_sv.update_yaxes(title="Velocity Δ from season peak (mph)")
    fig_sv.update_layout(height=260, showlegend=False)
    st.plotly_chart(fig_sv, use_container_width=True)

    recent_4 = weekly.tail(4)["avg_velo"].mean()
    early_4  = weekly.head(4)["avg_velo"].mean()
    diff     = recent_4 - early_4
    stat_row([
        {"value": f"{season_peak:.1f}", "label": "Season peak velo (mph)", "status": "good"},
        {"value": f"{recent_4:.1f}",    "label": "Last 4 weeks avg",
         "delta": f"{'▲' if diff >= 0 else '▼'} {abs(diff):.1f} vs early season",
         "status": "good" if diff >= -0.5 else "warn" if diff >= -1.5 else "bad"},
        {"value": f"{diff:+.1f}",       "label": "Season velocity change",
         "status": "good" if diff >= -0.5 else "warn" if diff >= -1.5 else "bad"},
    ])

st.markdown("---")

# ── Coach's Insight ────────────────────────────────────────────────────────────
# Build natural sentences without em-dashes or semicolons
_acwr_sentence = (
    f"Current ACWR is {_acwr_str} ({latest_zone}), above the safe zone of 0.80–1.30."
    if acwr_flag
    else f"Current ACWR is {_acwr_str} ({latest_zone}), within the safe zone."
)
_velo_sentence = (
    f"Velocity is declining {abs(vd.get("slope", 0)):.2f} mph per inning, a statistically significant fatigue signal."
    if velo_flag
    else "Velocity profile across innings is within normal range."
)
_drift_sentence = (
    f"Release point has shifted {rd.get('drift_x', 0):.1f} inches horizontally from the season baseline. Schedule a mechanics review."
    if drift_flag
    else "Release point is consistent with the season baseline."
)

coaches_insight(
    f"<strong>{pitcher_name}</strong> is rated <strong>{readiness}</strong> for this start. "
    f"{_acwr_sentence} {_velo_sentence} {_drift_sentence}",
    read_rec,
)