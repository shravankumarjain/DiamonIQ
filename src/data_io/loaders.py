"""
pybaseball wrappers + direct Baseball Savant CSV fetchers with Parquet caching.

FanGraphs (pitching_stats / batting_stats) blocks automated requests with 403.
All data is sourced from Baseball Savant (baseballsavant.mlb.com) which is
public, reliable, and returns MLBAM player IDs natively.

Data strategy
-------------
Phase 1 (scripts/01_download_base_data.py — run once):
  - Savant pitcher leaderboard  -> savant_pitching_{year}.parquet
  - Savant batter leaderboard   -> savant_batting_{year}.parquet
  - Pitcher roster (with MLBAM IDs)

Phase 2 (triggered at runtime when a user selects a pitcher):
  - statcast_pitcher per MLBAM ID -> pitcher_{id}_{year}.parquet
"""
from __future__ import annotations

import time
from io import StringIO
from pathlib import Path  # noqa: F401

import pandas as pd
import requests
import pybaseball as pyb

from config.settings import SEASON, SEASON_START, SEASON_END, RAW_DIR  # noqa: F401
from src.data_io.cache import cache_exists, load_parquet, save_parquet

pyb.cache.enable()

# ---------------------------------------------------------------------------
# Shared HTTP helper
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://baseballsavant.mlb.com/",
}


def _fetch_savant_csv(url: str, retries: int = 3, delay: float = 2.0) -> pd.DataFrame:
    """GET a CSV from Baseball Savant with retry logic."""
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=60)
            resp.raise_for_status()
            df = pd.read_csv(StringIO(resp.text))
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(delay * attempt)
    raise RuntimeError(
        f"Failed to fetch Baseball Savant CSV after {retries} attempts.\n"
        f"URL: {url}\nLast error: {last_exc}"
    )


# ---------------------------------------------------------------------------
# Pitcher leaderboard
# ---------------------------------------------------------------------------

_SAVANT_PITCHER_EXPECTED = (
    "https://baseballsavant.mlb.com/expected_statistics"
    "?type=pitcher&year={year}&position=&team=&min=1&csv=true"
)

_SAVANT_PITCHER_STANDARD = (
    "https://baseballsavant.mlb.com/leaderboard/custom"
    "?year={year}&type=pitcher&filter=&min=1"
    "&selections=p_era%2Cp_k_percent%2Cp_bb_percent%2Cp_whip"
    "%2Cp_game%2Cp_starting_p%2Cp_ip%2Cp_win%2Cp_loss"
    "%2Cp_save%2Cp_strikeout%2Cp_walk%2Cp_home_run%2Cp_earned_run"
    "&chart=false&x=p_k_percent&y=p_era&r=no&chartType=beeswarm&csv=true"
)


def get_savant_pitching(season: int = SEASON, force: bool = False) -> pd.DataFrame:
    """Pitcher stats from Baseball Savant expected-statistics + leaderboard endpoints."""
    path = RAW_DIR / f"savant_pitching_{season}.parquet"
    if cache_exists(path) and not force:
        return load_parquet(path)

    expected = _fetch_savant_csv(_SAVANT_PITCHER_EXPECTED.format(year=season))
    expected = _normalise_savant_names(expected)
    expected = expected.rename(columns={"player_id": "mlbam_id"})

    try:
        standard = _fetch_savant_csv(_SAVANT_PITCHER_STANDARD.format(year=season))
        standard = _normalise_savant_names(standard)
        standard = standard.rename(columns={
            "player_id":   "mlbam_id",
            "p_era":       "ERA",
            "p_k_percent": "K_pct",
            "p_bb_percent":"BB_pct",
            "p_whip":      "WHIP",
            "p_game":      "G",
            "p_starting_p":"GS",
            "p_ip":        "IP",
            "p_win":       "W",
            "p_loss":      "L",
            "p_save":      "SV",
            "p_strikeout": "SO",
            "p_walk":      "BB",
            "p_home_run":  "HR",
            "p_earned_run":"ER",
        })
        merge_cols = [c for c in standard.columns
                      if c not in expected.columns or c in ("mlbam_id", "player_name")]
        df = expected.merge(
            standard[merge_cols], on="mlbam_id", how="left", suffixes=("", "_std")
        )
    except Exception:
        df = expected

    df["mlbam_id"] = pd.to_numeric(df["mlbam_id"], errors="coerce")
    df = df.dropna(subset=["mlbam_id"])
    df["mlbam_id"] = df["mlbam_id"].astype(int)
    df = df.sort_values("player_name").reset_index(drop=True)

    save_parquet(df, path)
    return df


# ---------------------------------------------------------------------------
# Batter leaderboard
# ---------------------------------------------------------------------------

_SAVANT_BATTER_EXPECTED = (
    "https://baseballsavant.mlb.com/expected_statistics"
    "?type=batter&year={year}&position=&team=&min=50&csv=true"
)


def get_savant_batting(season: int = SEASON, force: bool = False) -> pd.DataFrame:
    """Batter stats from Baseball Savant expected statistics endpoint."""
    path = RAW_DIR / f"savant_batting_{season}.parquet"
    if cache_exists(path) and not force:
        return load_parquet(path)

    df = _fetch_savant_csv(_SAVANT_BATTER_EXPECTED.format(year=season))
    df = _normalise_savant_names(df)
    df = df.rename(columns={"player_id": "mlbam_id"})
    df["mlbam_id"] = pd.to_numeric(df["mlbam_id"], errors="coerce")
    df = df.dropna(subset=["mlbam_id"])
    df["mlbam_id"] = df["mlbam_id"].astype(int)
    df = df.sort_values("player_name").reset_index(drop=True)

    save_parquet(df, path)
    return df


# ---------------------------------------------------------------------------
# Pitcher roster (the sidebar dropdown source)
# ---------------------------------------------------------------------------

def build_pitcher_roster(season: int = SEASON, force: bool = False) -> pd.DataFrame:
    """
    Clean pitcher roster for the sidebar dropdown.
    Guaranteed output columns: player_name, mlbam_id
    Optional: pa, xwOBA, AvgEV, Barrel_pct, HardHit_pct, woba, ERA, K_pct, BB_pct, WHIP, IP, GS
    """
    path = RAW_DIR / f"pitcher_roster_{season}.parquet"
    if cache_exists(path) and not force:
        return load_parquet(path)

    df = get_savant_pitching(season)
    if df.empty:
        raise RuntimeError(
            "Savant pitcher data is empty. "
            "Run scripts/01_download_base_data.py first."
        )

    rename_map = {}
    for candidate in ("estimated_woba_using_speedangle", "xwoba", "est_woba"):
        if candidate in df.columns and candidate != "xwOBA":
            rename_map[candidate] = "xwOBA"
            break
    if "exit_velocity_avg" in df.columns:
        rename_map["exit_velocity_avg"] = "AvgEV"
    if "barrel_batted_rate" in df.columns:
        rename_map["barrel_batted_rate"] = "Barrel_pct"
    if "hard_hit_percent" in df.columns:
        rename_map["hard_hit_percent"] = "HardHit_pct"
    if rename_map:
        df = df.rename(columns=rename_map)

    preferred = [
        "player_name", "mlbam_id", "pa", "xwOBA", "woba",
        "AvgEV", "Barrel_pct", "HardHit_pct",
        "ERA", "K_pct", "BB_pct", "WHIP", "IP", "GS",
    ]
    roster = df[[c for c in preferred if c in df.columns]].copy()

    if "pa" in roster.columns:
        roster["pa"] = pd.to_numeric(roster["pa"], errors="coerce").fillna(0)
        roster = roster[roster["pa"] >= 10]
    elif "IP" in roster.columns:
        roster["IP"] = pd.to_numeric(roster["IP"], errors="coerce").fillna(0)
        roster = roster[roster["IP"] >= 1]

    roster = roster.dropna(subset=["player_name", "mlbam_id"])
    roster["mlbam_id"] = roster["mlbam_id"].astype(int)
    roster = roster.sort_values("player_name").reset_index(drop=True)

    save_parquet(roster, path)
    return roster


# ---------------------------------------------------------------------------
# Per-pitcher Statcast (downloaded on demand)
# ---------------------------------------------------------------------------

def get_pitcher_statcast(mlbam_id: int, season: int = SEASON, force: bool = False) -> pd.DataFrame:
    """Full pitch-level Statcast data for one pitcher in one season."""
    path = RAW_DIR / f"pitcher_{mlbam_id}_{season}.parquet"
    if cache_exists(path) and not force:
        return load_parquet(path)

    start = f"{season}-03-01"
    end   = f"{season}-11-01"
    df = pyb.statcast_pitcher(start_dt=start, end_dt=end, player_id=mlbam_id)

    if df is None or df.empty:
        raise ValueError(
            f"No Statcast data for MLBAM ID {mlbam_id} in {season}. "
            "Verify the player ID is correct."
        )

    df = _clean_statcast(df)
    save_parquet(df, path)
    return df


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

def _normalise_savant_names(df: pd.DataFrame) -> pd.DataFrame:
    """Handle both 'last_name, first_name' single-column and split first/last formats."""
    df = df.copy()
    combined_candidates = [c for c in df.columns if "last_name" in c.lower()]

    if "first_name" in df.columns and "last_name" in df.columns:
        df["player_name"] = (
            df["first_name"].astype(str).str.strip() + " " +
            df["last_name"].astype(str).str.strip()
        )
    elif combined_candidates:
        raw_col = combined_candidates[0]
        raw     = df[raw_col].astype(str)
        split   = raw.str.split(",", n=1, expand=True)
        if split.shape[1] == 2:
            df["player_name"] = split[1].str.strip() + " " + split[0].str.strip()
        else:
            df["player_name"] = raw.str.strip()
    elif "player_name" not in df.columns:
        df["player_name"] = "Unknown"

    return df


# ---------------------------------------------------------------------------
# Statcast cleaning
# ---------------------------------------------------------------------------

def _clean_statcast(df: pd.DataFrame) -> pd.DataFrame:
    """Minimal cleaning applied once at download time."""
    df = df.copy()

    if "game_date" in df.columns:
        df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce")

    numeric_cols = [
        "release_speed", "release_spin_rate",
        "release_pos_x", "release_pos_z", "release_extension",
        "pfx_x", "pfx_z", "plate_x", "plate_z",
        "launch_speed", "launch_angle",
        "estimated_woba_using_speedangle", "delta_run_exp", "inning",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "pfx_x" in df.columns:
        df["hb_in"]  = df["pfx_x"] * 12
    if "pfx_z" in df.columns:
        df["ivb_in"] = df["pfx_z"] * 12

    if "pitch_type" in df.columns:
        df["pitch_type"] = df["pitch_type"].astype(str).str.upper().str.strip()
        df = df[df["pitch_type"].notna() & (df["pitch_type"] != "NAN")]

    if "description" in df.columns:
        df["is_swing"] = df["description"].isin([
            "swinging_strike", "swinging_strike_blocked",
            "foul", "foul_tip", "hit_into_play",
            "hit_into_play_score", "hit_into_play_no_out",
        ])
        df["is_whiff"] = df["description"].isin([
            "swinging_strike", "swinging_strike_blocked", "foul_tip",
        ])
        df["is_called_strike"] = df["description"] == "called_strike"
        df["is_csw"]  = df["is_whiff"] | df["is_called_strike"]
        df["is_ball"] = df["description"].isin(["ball", "blocked_ball", "pitchout"])
        df["in_zone"] = df.get("zone", pd.Series(dtype=float)).between(1, 9)

    return df