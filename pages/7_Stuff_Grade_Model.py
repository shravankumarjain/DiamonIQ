"""
Diamond IQ — Page 7: Stuff Grade Model
Answers: "How good is each pitch compared to MLB average?"
Output: Logistic regression whiff probability → 20-80 scout grade per pitch type,
        feature importance, comparison to MLB benchmarks
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
    NAVY, GOLD, GREEN, RED, AMBER, SURFACE, MUTED,
    require_pitcher, load_statcast, stuff_grade, pitch_color,
)
from config.settings import SEASON

inject_css()

if not require_pitcher(st.session_state):
    st.stop()

pitcher_name = st.session_state["selected_pitcher_name"]

page_header(
    "Stuff Grade Model",
    f"{pitcher_name} · ML pitch quality scoring · 20-80 scout scale · vs MLB baseline",
    "🤖",
)

metric_glossary_expander(["Whiff%", "EV"])

df = load_statcast(st.session_state)
if df is None:
    st.stop()

# ── Compute stuff grades ──────────────────────────────────────────────────────
with st.spinner("Running stuff grade model…"):
    grades = stuff_grade(df)

# ── Methodology expander ──────────────────────────────────────────────────────
with st.expander("📖 Model methodology"):
    st.markdown("""
    **How the Stuff Grade Model works:**

    1. **Features:** For each pitch type, we use physical pitch characteristics:
       `release_speed`, `release_spin_rate`, `pfx_x` (horizontal break), 
       `pfx_z` (vertical break), and `release_extension`.
    
    2. **Target:** Binary outcome — `is_whiff` (1 = swing & miss, 0 = other result).
    
    3. **Model:** Logistic Regression with StandardScaler normalisation, trained 
       separately per pitch type on the pitcher's own Statcast data.
    
    4. **Grade conversion:** Raw whiff probability is mapped to the MLB 20-80 
       scout scale, where **50 = MLB average** (≈24% whiff probability), 
       **60** = above average, **70** = plus, **80** = elite.
    
    5. **Limitation:** Grades are computed on the pitcher's own data (self-referential). 
       A true Stuff+ model requires comparison to all MLB pitchers — this is a 
       simplified academic implementation. The methodology matches the approach 
       used by Trackman/Hawkeye-based tools.
    """)

if grades.empty:
    st.warning(
        "Stuff grade model requires at least 20 pitches per type with "
        "release_speed, release_spin_rate, pfx_x, pfx_z, and is_whiff columns. "
        "Check that Statcast data loaded correctly."
    )
    st.stop()

st.markdown(pitch_legend_strip(grades["pitch_type"].tolist()), unsafe_allow_html=True)

# ── Section 1: Grade overview cards ──────────────────────────────────────────
st.markdown("### Pitch grades — 20-80 scale")
st.caption(
    "**20-80 scout scale:** 20 = poor, 40 = below avg, 50 = MLB avg, "
    "60 = above avg, 70 = plus, 80 = elite."
)

def grade_status(g):
    if g >= 60: return "good"
    if g >= 50: return "neutral"
    if g >= 40: return "warn"
    return "bad"

def grade_label(g):
    if g >= 70: return "Plus-Plus"
    if g >= 60: return "Plus"
    if g >= 55: return "Above Average"
    if g >= 45: return "Average"
    if g >= 40: return "Below Average"
    return "Poor"

cards = []
for _, row in grades.iterrows():
    cards.append({
        "label": row["pitch_type"],
        "value": f"{row['stuff_grade']:.0f} / 80",
        "sub": f"{grade_label(row['stuff_grade'])} · {row['whiff_prob']*100:.1f}% whiff prob",
        "status": grade_status(row["stuff_grade"]),
    })

if cards:
    # Show up to 5 cards per row
    for i in range(0, len(cards), 5):
        metric_row(cards[i:i+5])

st.markdown("---")

# ── Section 2: Visual grade bars ──────────────────────────────────────────────
st.markdown("### Visual grade comparison")

col_grade1, col_grade2 = st.columns([1.4, 1])

with col_grade1:
    fig_grade = go.Figure()

    grade_colors = [
        GREEN if g >= 60 else AMBER if g >= 50 else RED if g < 40 else NAVY
        for g in grades["stuff_grade"]
    ]

    fig_grade.add_trace(go.Bar(
        y=grades["pitch_type"],
        x=grades["stuff_grade"].round(1),
        orientation="h",
        marker_color=grade_colors,
        text=grades["stuff_grade"].round(1).astype(str) + " / 80",
        textposition="outside",
    ))

    # Reference lines on 20-80 scale
    for val, lbl in [(50, "MLB avg"), (60, "Plus"), (70, "Plus+")]:
        fig_grade.add_vline(x=val, line_dash="dash",
                            line_color="#CBD5E0", line_width=1.5,
                            annotation_text=lbl, annotation_position="top",
                            annotation_font=dict(size=9))

    apply_theme(fig_grade, "Stuff Grade by Pitch Type (20-80 Scale)")
    fig_grade.update_xaxes(title="Stuff grade", range=[0, 85])
    fig_grade.update_yaxes(title="")
    fig_grade.update_layout(height=max(250, 60 * len(grades)))
    st.plotly_chart(fig_grade, use_container_width=True)

with col_grade2:
    # Gauge chart for overall stuff (weighted average)
    total_pitches = grades["n"].sum()
    weighted_grade = (grades["stuff_grade"] * grades["n"]).sum() / total_pitches if total_pitches > 0 else 50

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=round(weighted_grade, 1),
        delta={"reference": 50, "valueformat": ".1f",
               "increasing": {"color": GREEN}, "decreasing": {"color": RED}},
        title={"text": "Overall Stuff Grade<br><span style='font-size:0.75em;color:gray'>Weighted by usage</span>"},
        gauge={
            "axis": {"range": [20, 80], "tickwidth": 1},
            "bar": {"color": NAVY, "thickness": 0.25},
            "steps": [
                {"range": [20, 40], "color": "#f8d7da"},
                {"range": [40, 50], "color": "#fff3cd"},
                {"range": [50, 60], "color": "#d4edda"},
                {"range": [60, 80], "color": "#cce5ff"},
            ],
            "threshold": {
                "line": {"color": GOLD, "width": 4},
                "thickness": 0.75,
                "value": 50,
            },
        },
    ))
    fig_gauge.update_layout(height=280, margin=dict(l=20, r=20, t=80, b=20))
    st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown(f"""
    <div style="text-align:center;font-size:1.0rem;font-weight:600;color:{NAVY};margin-top:-8px;">
        {grade_label(weighted_grade)}
    </div>
    <div style="text-align:center;font-size:0.8rem;color:{MUTED};">
        vs MLB average (50)
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ── Section 3: Feature contribution table ────────────────────────────────────
st.markdown("### Pitch characteristics by grade")
st.caption(
    "Higher velocity, higher spin rate, and more movement contribute to better grades. "
    "Use this to identify which physical attributes to prioritise in conditioning."
)

disp = grades.copy()
rename_g = {
    "pitch_type": "Pitch",
    "n": "Pitches",
    "stuff_grade": "Stuff Grade",
    "whiff_prob": "Whiff Prob",
    "avg_velo": "Avg Velo (mph)",
    "avg_spin": "Avg Spin (rpm)",
}
disp = disp[[c for c in rename_g if c in disp.columns]].rename(columns=rename_g)
if "Whiff Prob" in disp.columns:
    disp["Whiff Prob"] = (disp["Whiff Prob"] * 100).round(1).astype(str) + "%"
if "Stuff Grade" in disp.columns:
    disp["Stuff Grade"] = disp["Stuff Grade"].round(1)
if "Avg Spin (rpm)" in disp.columns:
    disp["Avg Spin (rpm)"] = disp["Avg Spin (rpm)"].round(0)

st.dataframe(disp, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Section 4: Whiff rate bar chart per pitch type ────────────────────────────
st.markdown("### Whiff rate by pitch type")
st.caption(
    "Percentage of swings that result in a miss, broken down by pitch type. "
    "MLB average ≈ 25%. Elite pitches generate 30%+ whiff rates."
)

if "is_whiff" in df.columns and "is_swing" in df.columns and "pitch_type" in df.columns:
    whiff_by_type = []
    for pt, grp in df.groupby("pitch_type"):
        swings = grp["is_swing"].sum() if "is_swing" in grp.columns else 0
        whiffs = grp["is_whiff"].sum() if "is_whiff" in grp.columns else 0
        n      = len(grp)
        if swings > 5:
            whiff_by_type.append({
                "pitch_type": pt,
                "whiff_pct":  round(whiffs / swings * 100, 1),
                "n": n,
                "swings": int(swings),
            })

    if whiff_by_type:
        wdf = pd.DataFrame(whiff_by_type).sort_values("whiff_pct", ascending=False)
        fig_whiff_bar = go.Figure()
        bar_colors = [
            GREEN if v >= 30 else AMBER if v >= 22 else RED
            for v in wdf["whiff_pct"]
        ]
        fig_whiff_bar.add_trace(go.Bar(
            x=wdf["pitch_type"],
            y=wdf["whiff_pct"],
            marker_color=bar_colors,
            text=wdf["whiff_pct"].astype(str) + "%",
            textposition="outside",
            customdata=wdf[["swings","n"]].values,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Whiff%%: %{y:.1f}%%<br>"
                "Swings: %{customdata[0]}<br>"
                "Total pitches: %{customdata[1]}<extra></extra>"
            ),
        ))
        fig_whiff_bar.add_hline(
            y=25, line_dash="dash", line_color=NAVY,
            annotation_text="MLB avg (25%)",
            annotation_position="top right",
        )
        apply_theme(fig_whiff_bar, "Whiff Rate by Pitch Type (swings & misses ÷ swings)")
        fig_whiff_bar.update_yaxes(title="Whiff %", range=[0, max(70, wdf["whiff_pct"].max() + 10)])
        fig_whiff_bar.update_xaxes(title="Pitch type")
        st.plotly_chart(fig_whiff_bar, use_container_width=True)

        # Summary table below the chart
        st.dataframe(
            wdf.rename(columns={"pitch_type":"Pitch","whiff_pct":"Whiff%",
                                  "n":"Total Pitches","swings":"Swings"}),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("Insufficient swing data to compute whiff rates per pitch type.")

# ── Coach's Insight ──────────────────────────────────────────────────────────
best_grade_row  = grades.iloc[0]
worst_grade_row = grades.iloc[-1]

bg = best_grade_row
wg = worst_grade_row

insight = (
    f"Stuff grade model rates {pitcher_name}'s overall arsenal at "
    f"<strong>{weighted_grade:.1f} / 80</strong> "
    f"({grade_label(weighted_grade)}, {'above' if weighted_grade > 50 else 'below'} MLB average). "
    f"The <strong>{bg['pitch_type']}</strong> grades highest at "
    f"<strong>{bg['stuff_grade']:.0f}</strong> ({bg['whiff_prob']*100:.1f}% whiff probability). "
    f"The <strong>{wg['pitch_type']}</strong> grades lowest at "
    f"<strong>{wg["stuff_grade"]:.0f}</strong>. This pitch needs mechanical attention."
)
action = (
    f"Priority area for {wg['pitch_type']}: "
    f"{'Increase spin rate' if wg.get('avg_spin', 0) < 2200 else 'Improve movement profile'} "
    f"to push grade above 50. "
    f"Lead with the {bg['pitch_type']} in pressure situations."
)

coaches_insight(insight, action)