"""
Diamond IQ — Page 5: Pitch Sequencing
Answers: "Is he setting up his pitches correctly within at-bats?"
Output: Markov transition matrix, strike-count tunneling patterns, 
        first-pitch tendencies, two-strike pitch selection
Based on: Session 7 lecture — Simulation & Prediction (Markov chains)
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
    require_pitcher, load_statcast, pitch_transition_matrix, pitch_color,
)
from config.settings import SEASON

inject_css()

if not require_pitcher(st.session_state):
    st.stop()

pitcher_name = st.session_state["selected_pitcher_name"]

page_header(
    "Pitch Sequencing",
    f"{pitcher_name} · Markov transition matrices · Within-at-bat patterns",
    "🔄",
)

metric_glossary_expander(["CSW%", "Whiff%"])

df = load_statcast(st.session_state)
if df is None:
    st.stop()

if "pitch_type" not in df.columns:
    st.error("Pitch type data required for sequencing analysis.")
    st.stop()

st.markdown(pitch_legend_strip(df["pitch_type"].unique().tolist()), unsafe_allow_html=True)

# Construct "count" column from balls/strikes if not already present.
df = df.copy()
if "count" not in df.columns and {"balls", "strikes"}.issubset(df.columns):
    df["count"] = (
        df["balls"].astype("Int64").astype(str) + "-" +
        df["strikes"].astype("Int64").astype(str)
    )

# ── Section 1: Transition matrix ──────────────────────────────────────────────
st.markdown("### Pitch transition matrix (Markov chains)")
st.caption(
    "Each cell shows the probability of the **column pitch** following the **row pitch**. "
    "Rows sum to 100%. "
    "A predictable pitcher throws the same pitch repeatedly — exploitable. "
    "An unpredictable pitcher has even distributions across a row."
)

trans = pitch_transition_matrix(df)

if not trans.empty:
    z_vals = trans.values * 100  # convert to %

    # Adaptive text colour — dark cells get light text, light cells get dark text
    text_colors = []
    for row in z_vals:
        row_max = max(z_vals.max().max(), 1)
        text_colors.append([
            "#F1F5F9" if v < (row_max * 0.6) else "#0F172A"
            for v in row
        ])

    fig_mx = go.Figure(go.Heatmap(
        z=z_vals,
        x=trans.columns.tolist(),
        y=trans.index.tolist(),
        colorscale=[
            [0.0,  "#13151A"],   # page background — empty/zero cells invisible
            [0.15, "#1a2744"],   # very low probability — dark navy
            [0.40, "#1D6FA4"],   # moderate — mid blue
            [0.70, "#F0B429"],   # high — gold
            [1.0,  "#FBBF24"],   # maximum — bright amber
        ],
        text=[[f"{v:.1f}%" for v in row] for row in z_vals],
        texttemplate="%{text}",
        textfont=dict(size=11, color="#F1F5F9"),
        showscale=True,
        colorbar=dict(
            title=dict(text="Probability (%)", font=dict(color="#94A3B8", size=10)),
            tickfont=dict(color="#94A3B8", size=9),
            bgcolor="#1E2130",
            bordercolor="#2E3550",
            borderwidth=1,
        ),
        zmin=0,
    ))

    apply_theme(fig_mx, "Pitch Transition Probabilities")
    fig_mx.update_xaxes(title="Next pitch thrown", side="top",
                        tickfont=dict(color="#94A3B8", size=11))
    fig_mx.update_yaxes(title="Current pitch",
                        tickfont=dict(color="#94A3B8", size=11))
    fig_mx.update_layout(
        height=max(320, 65 * len(trans)),
        plot_bgcolor="#13151A",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_mx, use_container_width=True)

    # Predictability score: entropy
    entropy_scores = []
    for idx, row in trans.iterrows():
        probs = row.values[row.values > 0]
        if len(probs) > 0:
            h = -np.sum(probs * np.log2(probs + 1e-10))
            max_h = np.log2(len(probs))
            entropy_scores.append({
                "pitch": idx,
                "entropy": h,
                "predictability": (1 - h / max_h) * 100 if max_h > 0 else 0
            })

    if entropy_scores:
        ent_df = pd.DataFrame(entropy_scores).sort_values("predictability", ascending=False)
        st.markdown("#### Pitch predictability index")
        st.caption(
            "High predictability = batters can anticipate what comes next. "
            "MLB pitchers aim for <30% predictability on their primary pitch."
        )
        col_p1, col_p2 = st.columns([1.2, 1])
        with col_p1:
            fig_ent = go.Figure()
            colors_ent = [RED if v >= 60 else AMBER if v >= 40 else GREEN
                          for v in ent_df["predictability"]]
            fig_ent.add_trace(go.Bar(
                x=ent_df["pitch"],
                y=ent_df["predictability"].round(1),
                marker_color=colors_ent,
                text=ent_df["predictability"].round(1).astype(str) + "%",
                textposition="outside",
            ))
            fig_ent.add_hline(y=40, line_dash="dash", line_color=NAVY,
                              annotation_text="Target < 40%")
            apply_theme(fig_ent, "Pitch Predictability by Type")
            fig_ent.update_yaxes(title="Predictability %", range=[0, 100])
            st.plotly_chart(fig_ent, use_container_width=True)
        with col_p2:
            st.markdown("**What this means:**")
            most_pred = ent_df.iloc[0]
            least_pred = ent_df.iloc[-1]
            st.markdown(f"""
            - **Most predictable:** {most_pred['pitch']} 
              ({most_pred['predictability']:.0f}% — batters can anticipate this pitch)
            - **Most varied:** {least_pred['pitch']} 
              ({least_pred['predictability']:.0f}% — keeps batters off-balance)
            
            *Aim to increase variety after your primary pitch setup.*
            """)
else:
    st.info(
        "Transition matrix requires at-bat number and pitch sequence data. "
        "Ensure Statcast data includes at_bat_number and pitch_number columns."
    )

st.markdown("---")

# ── Section 2: First-pitch tendencies ────────────────────────────────────────
st.markdown("### First-pitch tendencies")
st.caption(
    "First-pitch strike rate drives the entire at-bat outcome. "
    "Elite pitchers throw first-pitch strikes 65%+ of the time."
)

if "pitch_number" in df.columns:
    first_pitches = df[df["pitch_number"] == 1]

    col_fp1, col_fp2 = st.columns(2)

    with col_fp1:
        fps_rate = first_pitches.get("is_called_strike", pd.Series()).mean()
        if "is_csw" in first_pitches.columns:
            fps_csw = first_pitches["is_csw"].mean() * 100
        else:
            fps_csw = np.nan

        fp_by_type = first_pitches["pitch_type"].value_counts(normalize=True) * 100
        if not fp_by_type.empty:
            fig_fp = go.Figure(go.Pie(
                labels=fp_by_type.index.tolist(),
                values=fp_by_type.values.round(1),
                hole=0.40,
                marker_colors=[pitch_color(pt) for pt in fp_by_type.index],
                textinfo="label+percent",
                textfont_size=11,
            ))
            apply_theme(fig_fp, "First Pitch Selection Mix")
            st.plotly_chart(fig_fp, use_container_width=True)

    with col_fp2:
        if "is_csw" in first_pitches.columns:
            fp_rate = first_pitches["is_csw"].mean() * 100
            st.markdown(f"""
            <div style="background:{SURFACE};border-radius:10px;padding:20px;
                        border-left:4px solid {'#2ECC71' if fp_rate >= 55 else '#F39C12' if fp_rate >= 45 else '#E74C3C'};">
                <div style="font-size:0.75rem;color:{MUTED};text-transform:uppercase;
                            letter-spacing:0.07em;margin-bottom:6px;">First-pitch strike rate</div>
                <div style="font-size:2.4rem;font-weight:700;color:{NAVY};">{fp_rate:.1f}%</div>
                <div style="font-size:0.85rem;color:{MUTED};margin-top:6px;">
                    {'✅ Elite — above 55%' if fp_rate >= 55 else
                     '⚠️ Target 55%+ for count advantage' if fp_rate >= 45 else
                     '❌ Below average — giving batters early count advantages'}
                </div>
                <div style="font-size:0.8rem;color:{MUTED};margin-top:12px;">
                    MLB average: ~60% first-pitch strike rate.
                </div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("Pitch number data required for first-pitch analysis. Available in full Statcast feed.")

st.markdown("---")

# ── Section 3: Two-strike pitch selection ─────────────────────────────────────
st.markdown("### Two-strike pitch selection")
st.caption(
    "In two-strike counts, elite pitchers put batters away with their best whiff pitch. "
    "Analyse which pitches are thrown — and which are most effective — when ahead 0-2 or 1-2."
)

if "balls" in df.columns and "strikes" in df.columns:
    two_strike = df[df["strikes"] == 2]

    if len(two_strike) >= 20:
        col_2s1, col_2s2 = st.columns(2)

        with col_2s1:
            ts_usage = two_strike["pitch_type"].value_counts(normalize=True) * 100
            fig_2s = go.Figure(go.Bar(
                x=ts_usage.index.tolist(),
                y=ts_usage.values.round(1),
                marker_color=[pitch_color(p) for p in ts_usage.index],
                text=ts_usage.values.round(1).astype(str) + "%",
                textposition="outside",
            ))
            apply_theme(fig_2s, "Two-Strike Pitch Usage")
            fig_2s.update_yaxes(title="Usage %", range=[0, 60])
            st.plotly_chart(fig_2s, use_container_width=True)

        with col_2s2:
            if "is_whiff" in two_strike.columns:
                ts_whiff = (
                    two_strike.groupby("pitch_type")["is_whiff"]
                    .mean()
                    .reset_index()
                    .rename(columns={"is_whiff": "whiff_rate"})
                )
                ts_whiff["whiff_rate"] *= 100
                ts_whiff = ts_whiff.sort_values("whiff_rate", ascending=False)

                fig_tsw = go.Figure(go.Bar(
                    x=ts_whiff["pitch_type"],
                    y=ts_whiff["whiff_rate"].round(1),
                    marker_color=[
                        GREEN if v >= 35 else AMBER if v >= 25 else RED
                        for v in ts_whiff["whiff_rate"]
                    ],
                    text=ts_whiff["whiff_rate"].round(1).astype(str) + "%",
                    textposition="outside",
                ))
                apply_theme(fig_tsw, "Two-Strike Whiff Rate by Pitch")
                fig_tsw.update_yaxes(title="Whiff %", range=[0, 70])
                fig_tsw.add_hline(y=30, line_dash="dash", line_color=NAVY,
                                  annotation_text="Target 30%+")
                st.plotly_chart(fig_tsw, use_container_width=True)

        # Best two-strike recommendation
        if "is_whiff" in two_strike.columns and not ts_whiff.empty:
            best_2s = ts_whiff.iloc[0]["pitch_type"]
            best_2s_whiff = ts_whiff.iloc[0]["whiff_rate"]
            top_used_2s = ts_usage.index[0] if not ts_usage.empty else "—"

            if best_2s != top_used_2s:
                st.markdown(
                    f'<div style="background:#1c1400;border-radius:8px;padding:14px;'
                    f'border-left:4px solid #F59E0B;border:1px solid #F59E0B30;">'
                    f'<span style="color:#F59E0B;font-weight:700;">⚠ Sequencing gap: </span>'
                    f'<span style="color:#CBD5E1;">The <b style="color:#F1F5F9;">{best_2s}</b> generates '
                    f'the most swings and misses in two-strike counts ({best_2s_whiff:.1f}% whiff rate), '
                    f'but the <b style="color:#F1F5F9;">{top_used_2s}</b> is used most often. '
                    f'Increase {best_2s} usage in putaway counts.</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
    else:
        st.info("Insufficient two-strike pitches in dataset.")
elif "strikes" not in df.columns:
    st.info("Ball/strike count data not available in this Statcast dataset.")

st.markdown("---")

# ── Section 4: Count-specific transition patterns ─────────────────────────────
st.markdown("### Optimal follow-up pitch by count")
st.caption(
    "Given the current count, which pitch generates the highest CSW rate as a follow-up? "
    "This translates directly into in-game pitch calling."
)

if "count" in df.columns and "is_csw" in df.columns and "pitch_type" in df.columns:
    # Named aggregation avoids the column-name collision that occurs when
    # .agg(["mean", "count"]) creates a result column literally called "count"
    # while "count" is also one of the groupby keys being restored by reset_index().
    count_pitch_csw = (
        df.groupby(["count", "pitch_type"])["is_csw"]
        .agg(csw_rate="mean", n="count")
        .reset_index()
    )
    count_pitch_csw = count_pitch_csw[count_pitch_csw["n"] >= 10]
    count_pitch_csw["csw_pct"] = count_pitch_csw["csw_rate"] * 100

    # Key counts
    key_counts = ["0-0", "0-1", "0-2", "1-1", "1-2", "2-2", "3-2"]
    key_counts = [c for c in key_counts if c in count_pitch_csw["count"].values]

    for count_val in key_counts[:4]:  # show top 4 counts
        sub = count_pitch_csw[count_pitch_csw["count"] == count_val].sort_values(
            "csw_pct", ascending=False
        )
        if sub.empty:
            continue
        best_pitch = sub.iloc[0]["pitch_type"]
        best_csw   = sub.iloc[0]["csw_pct"]
        st.markdown(
            f"**{count_val} count:** Best pitch → **{best_pitch}** "
            f"({best_csw:.1f}% CSW rate)"
        )
else:
    st.info("Count and CSW data needed for count-specific recommendations.")

# ── Coach's Insight ──────────────────────────────────────────────────────────
if not trans.empty:
    primary = trans.index[0] if len(trans) > 0 else "primary pitch"
    top_follow = trans.loc[primary].idxmax() if primary in trans.index else "off-speed"
    top_prob   = trans.loc[primary].max() * 100 if primary in trans.index else 0
else:
    primary = "primary pitch"
    top_follow = "off-speed"
    top_prob = 0

ts_best = ""
if "is_whiff" in df.columns and "strikes" in df.columns:
    ts_sub = df[df["strikes"] == 2]
    if not ts_sub.empty:
        ts_whiff_sm = ts_sub.groupby("pitch_type")["is_whiff"].mean()
        if not ts_whiff_sm.empty:
            ts_best = ts_whiff_sm.idxmax()

insight = (
    f"After throwing a <strong>{primary}</strong>, {pitcher_name} follows with "
    f"<strong>{top_follow}</strong> {top_prob:.0f}% of the time. "
    f"{'At that rate, advanced scouts can read the pattern. Increasing follow-up variety will keep batters off-balance.' if top_prob >= 50 else 'That level of variation is healthy and keeps batters guessing.'} "
    f"{'In two-strike counts, the ' + ts_best + ' generates the most swings and misses.' if ts_best else ''}"
)
action = (
    f"After the {primary}, rotate between {top_follow} and at least one other pitch type. "
    f"{'Prioritise the ' + ts_best + ' in 0-2 and 1-2 counts.' if ts_best else ''}"
)

coaches_insight(insight, action)