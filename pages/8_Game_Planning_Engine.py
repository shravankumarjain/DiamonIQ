"""
Diamond IQ — Page 8: Game Planning Engine
Answers: "How do we attack tomorrow's lineup?"
Output: Batter vulnerability analysis + prescriptive pitch sequence + Monte Carlo simulation
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.components import (
    metric_glossary_expander,
    pitch_legend_strip,
    inject_css,
    page_header,
    coaches_insight,
    apply_theme,
    metric_row,
    rgba,
    BG_CARD,
    BG_CARD2,
    BORDER,
    NAVY,
    GOLD,
    BLUE_ACC,
    GREEN,
    RED,
    AMBER,
    TEXT_PRI,
    TEXT_SEC,
    TEXT_MUT,
    pitch_color,
    pitch_effectiveness,
)
from config.settings import SEASON

inject_css()

# ── Guard ─────────────────────────────────────────────────────────────────────
pitcher_name = st.session_state.get("selected_pitcher_name")
pitcher_mlbam = st.session_state.get("selected_pitcher_mlbam", 0)

if not pitcher_name or pitcher_mlbam == 0:
    st.warning("⚾ Select a pitcher in the sidebar first.")
    st.stop()

page_header(
    "Game Planning Engine",
    f"Prescriptive batter matchup recommendations for {pitcher_name}",
    "🎯",
)

metric_glossary_expander(["CSW%", "Whiff%", "RV/100", "xwOBA", "EV", "Barrel%", "BF"])

# ── Load pitcher Statcast ──────────────────────────────────────────────────────
cache_key = f"sc_{pitcher_mlbam}"
df_pitcher = st.session_state.get(cache_key)
if df_pitcher is None:
    from src.data_io.loaders import get_pitcher_statcast

    with st.spinner(f"Loading {pitcher_name} Statcast data…"):
        try:
            df_pitcher = get_pitcher_statcast(pitcher_mlbam, SEASON)
            st.session_state[cache_key] = df_pitcher
        except Exception as e:
            st.error(f"Could not load pitcher data: {e}")
            st.stop()


# ── Load batter leaderboard ────────────────────────────────────────────────────
@st.cache_data(show_spinner=False, ttl=3600)
def load_batters():
    try:
        from src.data_io.loaders import get_savant_batting

        df = get_savant_batting(SEASON)
        for c in [
            "estimated_woba_using_speedangle",
            "xwoba",
            "est_woba",
            "xwoba_using_speedangle",
        ]:
            if c in df.columns:
                df = df.rename(columns={c: "xwOBA"})
                break
        return df
    except Exception:
        return pd.DataFrame()


batter_df = load_batters()


# ── Robust xwOBA extractor ─────────────────────────────────────────────────────
def get_xwoba(row):
    for col in ["xwOBA", "xwoba", "estimated_woba_using_speedangle", "est_woba"]:
        v = row.get(col) if hasattr(row, "get") else None
        if v is None and hasattr(row, "index") and col in row.index:
            v = row[col]
        try:
            f = float(v)
            if f == f:
                return f
        except (TypeError, ValueError):
            pass
    return 0.300


# ── Robust column value extractor ─────────────────────────────────────────────
def _col_val(row, *candidates):
    for c in candidates:
        v = row.get(c) if hasattr(row, "get") else None
        if v is None and hasattr(row, "index") and c in row.index:
            v = row[c]
        try:
            f = float(v)
            if f == f:
                return f
        except (TypeError, ValueError):
            pass
    return None


def bfmt(v, fmt="{:.3f}"):
    try:
        return fmt.format(float(v))
    except (TypeError, ValueError):
        return "—"


# ── Reusable Monte Carlo at-bat simulation ────────────────────────────────────
def simulate_at_bats(eff_df, xwoba_b_val, pitch_weights=None, n_sim=1000, seed=42):
    """
    Run a Monte Carlo simulation of n_sim at-bats for one pitcher against one
    batter's contact profile (xwOBA). Returns (outcomes dict, avg_run_value).

    eff_df        : pitch_effectiveness() output for this pitcher
    xwoba_b_val   : batter's expected weighted on-base average
    pitch_weights : optional dict {pitch_type: usage_weight}; defaults to
                    each pitch's real season usage_pct from eff_df
    """
    if eff_df.empty:
        return {"strikeout": 0, "walk": 0, "contact_out": 0, "hit": 0}, 0.0

    if pitch_weights is None:
        pitch_weights = {
            row["pitch_type"]: float(row["usage_pct"]) for _, row in eff_df.iterrows()
        }

    total_w = sum(pitch_weights.values())
    if total_w <= 0:
        n_pitches = len(pitch_weights) or 1
        norm_weights = {pt: 1.0 / n_pitches for pt in pitch_weights}
    else:
        norm_weights = {pt: w / total_w for pt, w in pitch_weights.items()}

    pitch_probs = {}
    for _, row in eff_df.iterrows():
        pt = row["pitch_type"]
        if pt not in norm_weights:
            continue
        csw_p = float(row.get("csw_pct", 28.0)) / 100
        whiff_p = float(row.get("whiff_pct", 25.0)) / 100
        rv_raw = row.get("rv_per_100", 0.0)
        rv = float(rv_raw) if not pd.isna(rv_raw) else 0.0

        whiff_p_clamped = min(whiff_p, csw_p)
        called_p = max(csw_p - whiff_p_clamped, 0.0)
        ball_p = 0.35
        contact_p = max(1.0 - whiff_p_clamped - called_p - ball_p, 0.05)

        pitch_probs[pt] = {
            "whiff_p": whiff_p_clamped,
            "called_p": called_p,
            "ball_p": ball_p,
            "contact_p": contact_p,
            "rv": rv,
        }

    pt_list = list(norm_weights.keys())
    w_list = [norm_weights[p] for p in pt_list]
    if w_list:
        w_sum = sum(w_list)
        w_list = (
            [w / w_sum for w in w_list]
            if w_sum > 0
            else [1.0 / len(w_list)] * len(w_list)
        )

    rng = np.random.default_rng(seed)
    outcomes = {"strikeout": 0, "walk": 0, "contact_out": 0, "hit": 0}
    total_rv = 0.0

    for _ in range(n_sim):
        strikes = balls = 0
        at_bat_done = False
        for _ in range(12):
            if not pt_list:
                break
            chosen_pt = rng.choice(pt_list, p=w_list)
            pp = pitch_probs.get(
                chosen_pt,
                {
                    "whiff_p": 0.25,
                    "called_p": 0.10,
                    "ball_p": 0.35,
                    "contact_p": 0.30,
                    "rv": 0.0,
                },
            )
            roll = rng.random()
            total_rv += pp["rv"] / 100

            if roll < pp["whiff_p"]:
                strikes += 1
                if strikes >= 3:
                    outcomes["strikeout"] += 1
                    at_bat_done = True
                    break
            elif roll < pp["whiff_p"] + pp["called_p"]:
                strikes += 1
                if strikes >= 3:
                    outcomes["strikeout"] += 1
                    at_bat_done = True
                    break
            elif roll < pp["whiff_p"] + pp["called_p"] + pp["ball_p"]:
                balls += 1
                if balls >= 4:
                    outcomes["walk"] += 1
                    at_bat_done = True
                    break
            else:
                if rng.random() < xwoba_b_val * 0.7:
                    outcomes["hit"] += 1
                else:
                    outcomes["contact_out"] += 1
                at_bat_done = True
                break

        if not at_bat_done:
            if rng.random() < xwoba_b_val * 0.7:
                outcomes["hit"] += 1
            else:
                outcomes["contact_out"] += 1

    avg_rv = total_rv / n_sim
    return outcomes, avg_rv


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("---")
    st.markdown("**Game planning controls**")

    if not batter_df.empty and "player_name" in batter_df.columns:
        batter_names = sorted(batter_df["player_name"].dropna().unique().tolist())
        default_b = next(
            (
                b
                for b in [
                    "Freddie Freeman",
                    "Juan Soto",
                    "Mookie Betts",
                    "Austin Riley",
                    "Jose Ramirez",
                    "Rafael Devers",
                ]
                if b in batter_names
            ),
            batter_names[0] if batter_names else "",
        )
        selected_batter = st.selectbox(
            "Select opposing batter",
            options=batter_names,
            index=batter_names.index(default_b) if default_b in batter_names else 0,
            key="gp_batter_select",
        )
        batter_hand = st.selectbox(
            "Batter handedness",
            options=["R", "L", "S"],
            key="gp_hand_select",
        )
        st.caption("R = Right-handed · L = Left-handed · S = Switch")

        st.markdown("---")
        st.markdown("**Upcoming Games's lineup**")
        st.caption(
            "Look up the opposing team's announced batting order and select all 9 "
            "starters below. There is no default lineup. Each game has a different "
            "opponent, so this list must be built fresh before every start."
        )
        lineup_batters = st.multiselect(
            "Select upcoming game's 9 starters",
            options=batter_names,
            default=[],
            max_selections=9,
            key="gp_lineup_select",
            placeholder="Search and add batters one at a time...",
        )
        if lineup_batters:
            st.caption(f"{len(lineup_batters)} / 9 batters selected.")
    else:
        selected_batter = None
        batter_hand = "R"
        lineup_batters = []
        st.warning(
            "Batter data not loaded.\n\nRun:\n```\npython scripts/01_download_base_data.py\n```"
        )

# ── Pitcher effectiveness ──────────────────────────────────────────────────────
eff = pitch_effectiveness(df_pitcher)

if not eff.empty:
    st.markdown(pitch_legend_strip(eff["pitch_type"].tolist()), unsafe_allow_html=True)

best_csw_pt = None
best_whiff_pt = None
worst_rv_pt = None

if not eff.empty:
    if "csw_pct" in eff.columns:
        v = eff.dropna(subset=["csw_pct"])
        if not v.empty:
            best_csw_pt = v.nlargest(1, "csw_pct").iloc[0]["pitch_type"]
    if "whiff_pct" in eff.columns:
        v = eff.dropna(subset=["whiff_pct"])
        if not v.empty:
            best_whiff_pt = v.nlargest(1, "whiff_pct").iloc[0]["pitch_type"]
    if "rv_per_100" in eff.columns:
        v = eff.dropna(subset=["rv_per_100"])
        if not v.empty:
            worst_rv_pt = v.nlargest(1, "rv_per_100").iloc[0]["pitch_type"]

# ── Section 1: Matchup overview ────────────────────────────────────────────────
st.markdown("### Matchup overview")
col_p, col_b = st.columns(2)

with col_p:
    st.markdown(f"**{pitcher_name} — Arsenal strengths**")
    if not eff.empty and "rv_per_100" in eff.columns:
        best_pitches = eff.dropna(subset=["rv_per_100"]).nsmallest(3, "rv_per_100")
        for _, row in best_pitches.iterrows():
            rv = row["rv_per_100"]
            csw = row.get("csw_pct", 0)
            whf = row.get("whiff_pct", 0)
            c = GREEN if rv < -0.5 else AMBER
            st.markdown(
                f'<div style="background:{BG_CARD2};border-radius:8px;padding:12px 14px;'
                f'border-left:3px solid {c};margin-bottom:8px;">'
                f'<div style="font-size:0.88rem;font-weight:700;color:{TEXT_PRI};margin-bottom:3px;">'
                f"{row['pitch_type']}</div>"
                f'<div style="font-size:0.80rem;color:{TEXT_SEC};">'
                f"{rv:+.2f} RV/100&nbsp;&nbsp;·&nbsp;&nbsp;{csw:.1f}% CSW&nbsp;&nbsp;·&nbsp;&nbsp;{whf:.1f}% whiff"
                f"</div></div>",
                unsafe_allow_html=True,
            )
    else:
        st.info("Load Statcast data to see arsenal strengths.")

with col_b:
    if selected_batter and not batter_df.empty:
        brow_df = batter_df[batter_df["player_name"] == selected_batter]
        if not brow_df.empty:
            brow = brow_df.iloc[0]
            xwoba_b = get_xwoba(brow)
            ev_b = _col_val(brow, "AvgEV", "exit_velocity_avg", "avg_hit_speed")
            barrel_b = _col_val(brow, "Barrel_pct", "barrel_batted_rate", "brl_percent")
            hh_b = _col_val(brow, "HardHit_pct", "hard_hit_percent", "hard_hit_pct")
            pa_b = _col_val(brow, "pa", "PA", "plate_appearances")

            st.markdown(f"**{selected_batter} — Season stats**")
            for stat, val, tip in [
                ("xwOBA", bfmt(xwoba_b), "Expected weighted OBA"),
                ("Avg Exit Velo", bfmt(ev_b, "{:.1f} mph"), "Higher = harder contact"),
                ("Barrel%", bfmt(barrel_b, "{:.1f}%"), "% barreled balls"),
                ("Hard-hit%", bfmt(hh_b, "{:.1f}%"), "% balls hit 95+ mph"),
                ("Plate appear.", bfmt(pa_b, "{:.0f}"), "Sample size"),
            ]:
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;'
                    f'padding:6px 0;border-bottom:1px solid {BORDER};font-size:0.85rem;">'
                    f'<span style="color:{TEXT_SEC};" title="{tip}">{stat}</span>'
                    f'<span style="color:{TEXT_PRI};font-weight:600;">{val}</span></div>',
                    unsafe_allow_html=True,
                )

            threat = (
                "HIGH" if xwoba_b >= 0.360 else "MEDIUM" if xwoba_b >= 0.310 else "LOW"
            )
            threat_col = (
                RED if threat == "HIGH" else AMBER if threat == "MEDIUM" else GREEN
            )
            st.markdown(
                f'<div style="background:{rgba(threat_col, 0.10)};border-radius:8px;padding:10px;'
                f'text-align:center;margin-top:10px;border:1px solid {rgba(threat_col, 0.3)};">'
                f'<b style="color:{threat_col};">Threat level: {threat}</b></div>',
                unsafe_allow_html=True,
            )
    else:
        st.info("Select an opposing batter in the sidebar.")

st.markdown("---")

# ── Section 2: Zone vulnerability heatmaps ────────────────────────────────────
st.markdown("### Zone vulnerability analysis")
st.caption(
    "How this pitcher has fared in each zone against batters of the selected handedness. "
    "Green = pitcher wins. Red = batter damage zone."
)

if "plate_x" in df_pitcher.columns and "plate_z" in df_pitcher.columns:
    df_hand = df_pitcher.copy()
    if "stand" in df_pitcher.columns and batter_hand in ["L", "R"]:
        sub = df_pitcher[df_pitcher["stand"] == batter_hand]
        df_hand = sub if len(sub) >= 20 else df_pitcher

    col_z1, col_z2 = st.columns(2)

    def zone_grid(data, outcome_col, title, invert=False):
        if outcome_col not in data.columns:
            return None
        valid = data.dropna(subset=["plate_x", "plate_z", outcome_col]).copy()
        if len(valid) < 20:
            return None
        valid["xb"] = pd.cut(
            valid["plate_x"].clip(-0.83, 0.83),
            bins=[-0.83, -0.277, 0.277, 0.83],
            labels=["In", "Mid", "Out"],
        )
        valid["zb"] = pd.cut(
            valid["plate_z"].clip(1.5, 3.5),
            bins=[1.5, 2.167, 2.833, 3.5],
            labels=["Low", "Mid", "High"],
        )
        valid = valid.dropna(subset=["xb", "zb"])
        grid = (
            valid.groupby(["zb", "xb"])[outcome_col]
            .agg(["mean", "count"])
            .reset_index()
        )
        grid.columns = ["zb", "xb", "rate", "n"]
        grid["rate"] = (grid["rate"] * 100).round(1)
        pivot = grid.pivot(index="zb", columns="xb", values="rate").fillna(0)
        try:
            pivot = pivot.reindex(
                index=["High", "Mid", "Low"], columns=["In", "Mid", "Out"]
            )
        except Exception:
            pass
        if pivot.empty:
            return None
        cscale = (
            [
                [0, "rgba(231,76,60,0.9)"],
                [0.5, "rgba(243,156,18,0.6)"],
                [1, "rgba(46,204,113,0.9)"],
            ]
            if invert
            else [
                [0, "rgba(46,204,113,0.9)"],
                [0.5, "rgba(243,156,18,0.6)"],
                [1, "rgba(231,76,60,0.9)"],
            ]
        )
        fig = go.Figure(
            go.Heatmap(
                z=pivot.values,
                x=pivot.columns.tolist(),
                y=pivot.index.tolist(),
                colorscale=cscale,
                text=[[f"{v:.1f}%" for v in row] for row in pivot.values],
                texttemplate="%{text}",
                textfont=dict(size=13, color="#F1F5F9"),
                showscale=False,
            )
        )
        fig.add_shape(
            type="rect",
            x0=-0.5,
            x1=2.5,
            y0=-0.5,
            y1=2.5,
            line=dict(color=GOLD, width=2),
            fillcolor="rgba(0,0,0,0)",
        )
        apply_theme(fig, title)
        fig.update_xaxes(title="Zone (catcher's view)")
        fig.update_yaxes(title="Height")
        fig.update_layout(height=300, margin=dict(l=40, r=20, t=50, b=40))
        return fig

    with col_z1:
        fig_w = zone_grid(df_hand, "is_whiff", f"Whiff% by zone — vs {batter_hand}HB")
        if fig_w:
            st.plotly_chart(fig_w, use_container_width=True)
            st.caption("Green = high whiff zone. Red = contact zone.")
        else:
            st.info("Need more pitches for zone whiff analysis.")

    with col_z2:
        if "in_zone" in df_hand.columns and "is_swing" in df_hand.columns:
            ooz = df_hand[df_hand["in_zone"] == False]
            fig_c = zone_grid(
                ooz, "is_swing", f"Chase% out-of-zone — vs {batter_hand}HB", invert=True
            )
            if fig_c:
                st.plotly_chart(fig_c, use_container_width=True)
                st.caption("Green = batter chasing. Red = batter taking the ball.")
            else:
                st.info("Need more out-of-zone pitches for chase analysis.")
        else:
            st.info("in_zone / is_swing data not available.")
else:
    st.info("Plate location data not available.")

st.markdown("---")

# ── Section 3: Prescriptive game plan script ──────────────────────────────────
st.markdown("### ⚾ Prescriptive game plan script")

# Pre-define variables so later sections can always reference them safely
lead_pitch = best_csw_pt or "primary strike-getter"
putaway = best_whiff_pt or best_csw_pt or "best whiff pitch"
avoid_pitch = worst_rv_pt or "high-contact pitch"
outcomes = {"strikeout": 0, "walk": 0, "contact_out": 0, "hit": 0}
n_sim = 1000
xw_val = 0.300
threat = "LOW"

if selected_batter and not batter_df.empty:
    brow_df = batter_df[batter_df["player_name"] == selected_batter]
    if brow_df.empty:
        st.warning(f"No data found for {selected_batter}.")
        st.stop()

    brow = brow_df.iloc[0]
    xw_val = get_xwoba(brow)
    threat = "HIGH" if xw_val >= 0.360 else "MEDIUM" if xw_val >= 0.310 else "LOW"
    thr_col = RED if threat == "HIGH" else AMBER if threat == "MEDIUM" else GREEN

    if batter_hand == "R":
        first_zone = "Attack the inner half to jam the right-handed batter."
        putaway_zone = "Target the down-and-away zone against RHB for maximum chase."
    elif batter_hand == "L":
        first_zone = "Use the outer third to set up off-speed away against LHB."
        putaway_zone = (
            "Bury the breaking ball below the zone or elevate the fastball against LHB."
        )
    else:
        first_zone = "Work both halves. Switch hitter — adjust approach each at-bat."
        putaway_zone = "Default to breaking ball below zone in two-strike counts."

    if threat == "HIGH":
        threat_note = "Never fall behind 2-0 or 3-1. Throw strikes early and attack with the best whiff pitch in hitter-friendly counts."
    elif threat == "MEDIUM":
        threat_note = "Mix speeds and work in-to-out to keep this batter off balance throughout the at-bat."
    else:
        threat_note = (
            "Attack early in counts and be aggressive. Do not nibble at the edges."
        )

    avoid_note = (
        f'Limit the <b style="color:{RED};">{avoid_pitch}</b>, the highest Run Value cost pitch. '
        if worst_rv_pt
        else "Avoid becoming predictable. Vary the pitch mix throughout each at-bat."
    )

    st.markdown(
        f'<div style="background:{rgba(NAVY, 0.8)};border-radius:12px;padding:24px;'
        f'border:1px solid {rgba(GOLD, 0.3)};margin-bottom:12px;">'
        f'<div style="font-size:0.68rem;font-weight:700;color:{GOLD};text-transform:uppercase;'
        f'letter-spacing:0.12em;margin-bottom:8px;">⚾ PRESCRIPTIVE GAME PLAN</div>'
        f'<div style="font-size:1.05rem;font-weight:700;color:{TEXT_PRI};margin-bottom:4px;">'
        f"{pitcher_name} vs {selected_batter} ({batter_hand}HB)</div>"
        f'<div style="font-size:0.84rem;color:{thr_col};font-weight:700;">'
        f"Threat level: {threat}&nbsp;&nbsp;|&nbsp;&nbsp;xwOBA: {xw_val:.3f}</div>"
        f"</div>",
        unsafe_allow_html=True,
    )

    for border_col, label_col, section_label, body in [
        (
            NAVY,
            NAVY,
            "FIRST PITCH APPROACH",
            f'Lead with <b style="color:{GOLD};">{lead_pitch}</b>, your highest CSW% pitch. '
            f"{first_zone} Establishing a first-pitch strike significantly improves at-bat outcomes.",
        ),
        (
            GREEN,
            GREEN,
            "PUTAWAY PITCH (2 STRIKES)",
            f'Use <b style="color:{GOLD};">{putaway}</b>, the highest swing-and-miss rate pitch in two-strike counts. '
            f"{putaway_zone}",
        ),
        (
            RED,
            RED,
            "PITCH TO AVOID",
            f"{avoid_note} Avoid elevated fastballs against high-threat hitters with strong exit velocity numbers.",
        ),
        (
            GOLD,
            GOLD,
            "TUNNELING STRATEGY",
            f'Throw <b style="color:{GOLD};">{lead_pitch}</b> and <b style="color:{GOLD};">{putaway}</b> '
            f"from the same release point so they look identical out of the hand before separating near the plate. "
            f"{threat_note}",
        ),
    ]:
        st.markdown(
            f'<div style="background:{BG_CARD2};border-radius:8px;padding:16px;'
            f'border-left:4px solid {border_col};margin-bottom:8px;">'
            f'<div style="font-size:0.68rem;font-weight:700;color:{label_col};'
            f'text-transform:uppercase;letter-spacing:0.09em;margin-bottom:6px;">{section_label}</div>'
            f'<div style="font-size:0.90rem;color:{TEXT_PRI};line-height:1.6;">{body}</div>'
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### At-bat sequence reference")
    st.dataframe(
        pd.DataFrame(
            {
                "Count": [
                    "0-0",
                    "0-1 or 1-1",
                    "0-2 or 1-2",
                    "2-2 or 3-2",
                    "3-0 or 3-1",
                ],
                "Recommended pitch": [
                    lead_pitch,
                    f"{lead_pitch} or change speed",
                    putaway,
                    putaway,
                    "Fastball for strike",
                ],
                "Intent": [
                    "Take count lead",
                    "Set up putaway pitch via tunneling",
                    "Strikeout attempt",
                    "Execute — no walks",
                    "Get strike — protect zone",
                ],
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info(
        "Select an opposing batter in the sidebar to generate the prescriptive game plan.",
        icon="🎯",
    )

st.markdown("---")

# ── Section 4: At-bat outcome simulator ───────────────────────────────────────
st.markdown("### At-bat outcome simulator")
st.caption(
    "Monte Carlo simulation of 1,000 at-bats using this pitcher's actual pitch mix "
    "and effectiveness data against the selected batter's contact profile. "
    "Adjust the sliders to model alternative pitch mix strategies."
)

if selected_batter and not eff.empty and not batter_df.empty:
    # Sliders for top-4 pitches by usage
    top_pitches = eff.head(4)
    sim_cols = st.columns(len(top_pitches))
    pitch_weights = {}
    for i, (_, row) in enumerate(top_pitches.iterrows()):
        pt = row["pitch_type"]
        with sim_cols[i]:
            pitch_weights[pt] = st.slider(
                f"{pt} %",
                min_value=0,
                max_value=80,
                value=int(float(row["usage_pct"])),
                step=5,
                key=f"sim_{pt}",
            )

    if sum(pitch_weights.values()) <= 0:
        st.warning(
            "All pitch usage sliders are at 0%. Using equal weighting for the simulation."
        )

    xwoba_b_val = get_xwoba(
        batter_df[batter_df["player_name"] == selected_batter].iloc[0]
    )
    outcomes, avg_rv = simulate_at_bats(
        eff, xwoba_b_val, pitch_weights=pitch_weights, n_sim=n_sim
    )

    # Result cards
    result_cols = st.columns(4)
    for col_w, (label, key, colour) in zip(
        result_cols,
        [
            ("Strikeout", "strikeout", GREEN),
            ("Contact out", "contact_out", BLUE_ACC),
            ("Walk", "walk", AMBER),
            ("Hit allowed", "hit", RED),
        ],
    ):
        count = outcomes[key]
        pct = count / n_sim * 100
        with col_w:
            st.markdown(
                f'<div style="background:{BG_CARD};border:1px solid {BORDER};'
                f"border-top:3px solid {colour};border-radius:8px;"
                f'padding:14px;text-align:center;">'
                f'<div style="font-size:0.68rem;color:{TEXT_MUT};text-transform:uppercase;'
                f'letter-spacing:0.08em;margin-bottom:4px;">{label}</div>'
                f'<div style="font-size:1.8rem;font-weight:700;color:{colour};">{pct:.0f}%</div>'
                f'<div style="font-size:0.74rem;color:{TEXT_SEC};">{count} / {n_sim} at-bats</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

    avg_rv_color = (
        GREEN if avg_rv < 0 else RED
    )  # pre-computed — no nested f-string quotes
    st.markdown(
        f'<div style="background:{BG_CARD};border:1px solid {BORDER};border-radius:8px;'
        f'padding:12px 18px;margin-top:10px;font-size:0.85rem;color:{TEXT_SEC};">'
        f"Simulated avg run value per at-bat: "
        f'<b style="color:{avg_rv_color};">{avg_rv:+.3f}</b>'
        f"&nbsp;&nbsp;|&nbsp;&nbsp;Adjust the sliders above to model different pitch mix strategies."
        f"</div>",
        unsafe_allow_html=True,
    )
else:
    st.info("Select an opposing batter and load Statcast data to run the simulation.")

st.markdown("---")

# ── Section 5: Upcoming Game's lineup scouting report ───────────────────────────────
st.markdown("### Upcoming Game's lineup scouting report")
st.caption(
    f"{pitcher_name} is starting upcoming against a known, fixed lineup of 9 batters. "
    "This report runs the prescriptive game plan and outcome simulation for every "
    "batter at once, so the full attack plan is ready before first pitch. "
    "Build the lineup in the sidebar."
)

if lineup_batters and not eff.empty and not batter_df.empty:
    lineup_rows = []
    for b_name in lineup_batters:
        b_row_df = batter_df[batter_df["player_name"] == b_name]
        if b_row_df.empty:
            continue
        b_row = b_row_df.iloc[0]
        b_xw = get_xwoba(b_row)
        b_threat = "HIGH" if b_xw >= 0.360 else "MEDIUM" if b_xw >= 0.310 else "LOW"

        b_outcomes, b_avg_rv = simulate_at_bats(
            eff, b_xw, n_sim=500, seed=hash(b_name) % (2**31)
        )
        b_so_pct = b_outcomes["strikeout"] / 500 * 100
        b_hit_pct = b_outcomes["hit"] / 500 * 100
        b_walk_pct = b_outcomes["walk"] / 500 * 100

        lineup_rows.append(
            {
                "Batter": b_name,
                "xwOBA": round(b_xw, 3),
                "Threat": b_threat,
                "Lead with": lead_pitch,
                "Putaway": putaway,
                "Sim K%": round(b_so_pct, 0),
                "Sim Hit%": round(b_hit_pct, 0),
                "Sim BB%": round(b_walk_pct, 0),
                "Avg RV": round(b_avg_rv, 3),
            }
        )

    if lineup_rows:
        lineup_df = pd.DataFrame(lineup_rows)

        n_entered = len(lineup_rows)
        if n_entered < 9:
            st.warning(
                f"{n_entered} of 9 batters entered. This report is based on a "
                f"partial lineup — add the remaining {9 - n_entered} starter(s) "
                f"in the sidebar for the complete pre-game scouting report."
            )

        # Summary cards across the full lineup
        avg_k = lineup_df["Sim K%"].mean()
        avg_hit = lineup_df["Sim Hit%"].mean()
        n_high = (lineup_df["Threat"] == "HIGH").sum()
        toughest = lineup_df.loc[lineup_df["xwOBA"].idxmax(), "Batter"]

        sum_cols = st.columns(4)
        for col_w, (label, value, colour) in zip(
            sum_cols,
            [
                ("Lineup avg K%", f"{avg_k:.0f}%", GREEN),
                ("Lineup avg hit%", f"{avg_hit:.0f}%", BLUE_ACC),
                ("HIGH-threat batters", str(n_high), RED),
                ("Toughest matchup", toughest, AMBER),
            ],
        ):
            with col_w:
                st.markdown(
                    f'<div style="background:{BG_CARD};border:1px solid {BORDER};'
                    f"border-top:3px solid {colour};border-radius:8px;"
                    f'padding:12px;text-align:center;">'
                    f'<div style="font-size:0.66rem;color:{TEXT_MUT};text-transform:uppercase;'
                    f'letter-spacing:0.07em;margin-bottom:4px;">{label}</div>'
                    f'<div style="font-size:1.15rem;font-weight:700;color:{colour};">{value}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

        st.markdown("<br>", unsafe_allow_html=True)

        # Order by threat: HIGH first, so the coach sees the hardest outs up top
        threat_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        lineup_df["_sort"] = lineup_df["Threat"].map(threat_order)
        lineup_df = (
            lineup_df.sort_values("_sort").drop(columns="_sort").reset_index(drop=True)
        )
        lineup_df.insert(0, "Order", range(1, len(lineup_df) + 1))

        st.dataframe(
            lineup_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "xwOBA": st.column_config.NumberColumn(format="%.3f"),
                "Sim K%": st.column_config.NumberColumn(format="%d%%"),
                "Sim Hit%": st.column_config.NumberColumn(format="%d%%"),
                "Sim BB%": st.column_config.NumberColumn(format="%d%%"),
                "Avg RV": st.column_config.NumberColumn(format="%+.3f"),
            },
        )

        st.caption(
            "Lead with / Putaway columns reflect the pitcher's own best pitches "
            f"({lead_pitch} and {putaway}) since this is a fixed pre-game game plan, "
            "not a per-batter adjustment. Sim columns are 500-at-bat Monte Carlo "
            "projections per batter using each batter's individual xwOBA."
        )
    else:
        st.info("No batter data found for the selected lineup names.")
else:
    st.info(
        "No lineup entered yet. Look up game's opponent and add their announced "
        "batting order in the sidebar under **Games's lineup**. Scroll Down The Left Panel The report builds "
        "automatically as soon as at least one batter is selected, and is most useful "
        "once all 9 starters are entered."
    )

st.markdown("---")

# ── Section 5: Lineup threat leaderboard ─────────────────────────────────────
st.markdown("### Lineup threat assessment")
st.caption(
    "Rank the opposing lineup by threat level. Prioritise game-plan time on HIGH-threat matchups."
)

if not batter_df.empty and "player_name" in batter_df.columns:
    with st.expander("View full batter leaderboard"):
        xwoba_col = next(
            (
                c
                for c in [
                    "xwOBA",
                    "xwoba",
                    "estimated_woba_using_speedangle",
                    "est_woba",
                ]
                if c in batter_df.columns
            ),
            None,
        )
        if xwoba_col:
            ldb = batter_df.copy()
            ldb[xwoba_col] = pd.to_numeric(ldb[xwoba_col], errors="coerce")
            ldb = ldb.dropna(subset=[xwoba_col]).sort_values(xwoba_col, ascending=False)
            ldb["Threat"] = ldb[xwoba_col].apply(
                lambda x: "HIGH" if x >= 0.360 else "MEDIUM" if x >= 0.310 else "LOW"
            )
            show_cols = ["player_name", xwoba_col, "Threat"]
            extra_cols = [
                c
                for c in ["AvgEV", "Barrel_pct", "HardHit_pct", "pa"]
                if c in ldb.columns
            ]
            st.dataframe(
                ldb[show_cols + extra_cols]
                .head(60)
                .rename(columns={"player_name": "Batter", xwoba_col: "xwOBA"}),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.dataframe(
                batter_df[[c for c in batter_df.columns if c != "mlbam_id"][:8]].head(
                    30
                ),
                use_container_width=True,
                hide_index=True,
            )
else:
    st.info(
        "Batter data not loaded. Run `python scripts/01_download_base_data.py` first."
    )

# ── Coach's Insight ────────────────────────────────────────────────────────────
so_pct = outcomes.get("strikeout", 0) / n_sim * 100

if selected_batter and not batter_df.empty:
    thr_display = "HIGH" if xw_val >= 0.360 else "MEDIUM" if xw_val >= 0.310 else "LOW"
    insight = (
        f"Game plan for {pitcher_name} vs <strong>{selected_batter}</strong> "
        f"({thr_display} threat, xwOBA {xw_val:.3f}): "
        f"Lead with <strong>{lead_pitch}</strong> to establish count advantage. "
        f"Use <strong>{putaway}</strong> in two-strike counts. "
        + (
            f"The simulation projects a {so_pct:.0f}% strikeout rate with the current pitch mix."
            if so_pct > 0
            else ""
        )
    )
    action = (
        f"Review this sequence with {pitcher_name} before the game. "
        f"Use the sliders in the simulator to model adjusted pitch mix strategies."
    )
else:
    insight = f"Game Planning Engine loaded for {pitcher_name}."
    action = "Select an opposing batter in the sidebar to generate a prescriptive sequence script."

coaches_insight(insight, action)
