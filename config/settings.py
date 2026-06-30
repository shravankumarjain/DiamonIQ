"""
Global configuration for Diamond IQ: Pitcher Intelligence Suite.
All constants, thresholds, and lookup tables live here.
"""
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR     = PROJECT_ROOT / "data"
RAW_DIR      = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Ensure data directories exist (Streamlit Cloud ships an ephemeral filesystem,
# so this must run on every cold start rather than assuming the folder exists)
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Season
# ---------------------------------------------------------------------------
SEASON       = 2024
SEASON_START = f"{SEASON}-03-28"
SEASON_END   = f"{SEASON}-09-30"

# ---------------------------------------------------------------------------
# Qualifying thresholds
# ---------------------------------------------------------------------------
MIN_IP            = 30       # minimum innings pitched to appear in comparisons
MIN_PITCHES_TYPE  = 50       # minimum pitches of a type to report that pitch
MIN_PA_BATTER     = 100      # minimum PA for batter profiles in game planning

# ---------------------------------------------------------------------------
# Pitch type lookup  (Statcast pitch_type codes → display names)
# ---------------------------------------------------------------------------
PITCH_NAMES: dict[str, str] = {
    "FF": "Four-Seam Fastball",
    "SI": "Sinker",
    "FC": "Cutter",
    "SL": "Slider",
    "ST": "Sweeper",
    "SV": "Slurve",
    "CU": "Curveball",
    "KC": "Knuckle Curve",
    "CH": "Changeup",
    "FS": "Splitter",
    "FO": "Forkball",
    "KN": "Knuckleball",
    "EP": "Eephus",
    "FA": "Fastball (generic)",
}

FASTBALLS  = {"FF", "SI", "FC", "FA"}
BREAKING   = {"SL", "ST", "SV", "CU", "KC"}
OFFSPEED   = {"CH", "FS", "FO", "KN", "EP"}

# ---------------------------------------------------------------------------
# Strike zone dimensions  (feet, from the ground, from catcher's perspective)
# ---------------------------------------------------------------------------
ZONE = {
    "left":   -0.85,
    "right":   0.85,
    "bottom":  1.50,
    "top":     3.50,
}

SHADOW = {
    "left":   -1.25,
    "right":   1.25,
    "bottom":  1.00,
    "top":     4.00,
}

# ---------------------------------------------------------------------------
# Fatigue thresholds
# ---------------------------------------------------------------------------
VELOCITY_DROP_FLAG_MPH   = 1.5
SPIN_DROP_FLAG_PCT       = 3.0
RELEASE_DRIFT_FLAG_INCH  = 3.0
ACWR_DANGER_THRESHOLD    = 1.5
ACWR_OPTIMAL_LOW         = 0.8
ACWR_OPTIMAL_HIGH        = 1.3

# ---------------------------------------------------------------------------
# 2024 MLB League average pitching benchmarks  (for percentile context)
# ---------------------------------------------------------------------------
LEAGUE_AVG_PITCHING: dict[str, float] = {
    "ERA":    4.08,
    "FIP":    4.08,
    "xFIP":   4.10,
    "WHIP":   1.27,
    "K_pct":  22.4,
    "BB_pct":  8.2,
    "HR9":     1.30,
    "CSW_pct": 29.0,
    "SwStr_pct": 11.0,
    "GB_pct":  43.5,
    "Hard_pct": 38.0,
    "vFA":     93.9,
}

# ---------------------------------------------------------------------------
# App identity
# ---------------------------------------------------------------------------
APP_NAME     = "Diamond IQ"
APP_SUBTITLE = "Pitcher Intelligence Suite"
APP_VERSION  = "1.0.0"