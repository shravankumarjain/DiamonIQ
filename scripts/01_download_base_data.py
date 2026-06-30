"""
Phase 1 base data acquisition.

Run from project root:
    python scripts/01_download_base_data.py

Downloads (all from Baseball Savant):
  1. Pitcher leaderboard stats    -> savant_pitching_{year}.parquet
  2. Batter leaderboard stats     -> savant_batting_{year}.parquet
  3. Pitcher roster (with MLBAM)  -> pitcher_roster_{year}.parquet

Individual pitcher Statcast data is downloaded on demand inside the app.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_io.loaders import (
    get_savant_pitching,
    get_savant_batting,
    build_pitcher_roster,
)
from config.settings import SEASON


def run(label: str, fn):
    print(f"  {label:<50}", end="", flush=True)
    t0 = time.perf_counter()
    try:
        df = fn()
        print(f"OK   {len(df):>6,} rows   {time.perf_counter() - t0:5.1f}s")
        return df
    except Exception as exc:
        print(f"FAILED\n    {exc}")
        return None


def main():
    print()
    print("=" * 65)
    print(f"  Diamond IQ - Base data download ({SEASON} season)")
    print("  Source: Baseball Savant (baseballsavant.mlb.com)")
    print("=" * 65)

    p = run("Pitcher leaderboard (Savant expected stats)", lambda: get_savant_pitching(SEASON))
    b = run("Batter leaderboard  (Savant expected stats)", lambda: get_savant_batting(SEASON))
    r = run("Pitcher roster with MLBAM IDs",              lambda: build_pitcher_roster(SEASON))

    print()
    if all(x is not None for x in [p, b, r]):
        print("  All base data ready. Files written to data/raw/")
        print()
        print("  Next:")
        print("    streamlit run Home.py")
        print()
        print("  Select any pitcher from the sidebar. Their Statcast data")
        print("  downloads automatically on first selection (30-90 sec).")
    else:
        print("  One or more downloads failed. Check errors above.")
        print("  If you see a connection error, check your internet connection.")
        print("  If you see a 403, wait 60 seconds and retry.")
    print()


if __name__ == "__main__":
    main()