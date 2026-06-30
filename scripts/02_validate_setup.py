"""
Validates that Phase 1 setup completed correctly.
Run:  python scripts/02_validate_setup.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config.settings import RAW_DIR, SEASON


def check(label: str, condition: bool, detail: str = "") -> bool:
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}]  {label}"
    if detail and not condition:
        msg += f"\n           -> {detail}"
    print(msg)
    return condition


def main():
    print()
    print("Diamond IQ - Setup validation")
    print("-" * 45)

    results = []

    expected_files = [
        f"savant_pitching_{SEASON}.parquet",
        f"savant_batting_{SEASON}.parquet",
        f"pitcher_roster_{SEASON}.parquet",
    ]
    for fname in expected_files:
        path = RAW_DIR / fname
        results.append(check(
            fname,
            path.exists() and path.stat().st_size > 512,
            f"File missing or empty at {path}. Run scripts/01_download_base_data.py"
        ))

    try:
        import pandas as pd
        roster_path = RAW_DIR / f"pitcher_roster_{SEASON}.parquet"
        if roster_path.exists():
            roster = pd.read_parquet(roster_path)
            results.append(check(
                "Pitcher roster has MLBAM IDs",
                "mlbam_id" in roster.columns and roster["mlbam_id"].notna().sum() > 200,
                f"Only {roster.get('mlbam_id', pd.Series()).notna().sum()} valid MLBAM IDs found."
            ))
            results.append(check(
                "Pitcher roster size (>300 pitchers)",
                len(roster) > 300,
                f"Roster has {len(roster)} rows. Expected >300."
            ))
    except Exception as e:
        results.append(check("Roster parquet readable", False, str(e)))

    try:
        import plotly, streamlit, pybaseball, sklearn  # noqa: F401
        results.append(check("Core packages importable", True))
    except ImportError as e:
        results.append(check("Core packages importable", False, str(e)))

    print("-" * 45)
    passed = sum(results)
    total  = len(results)
    print(f"  {passed}/{total} checks passed")
    if passed == total:
        print("  All good. Run:  streamlit run Home.py")
    else:
        print("  Fix the FAIL items above before proceeding.")
    print()


if __name__ == "__main__":
    main()