# ⚾ Diamond IQ — Pitcher Intelligence Suite

A Statcast-powered pitching analytics platform built for **MLB pitching coaches**. Diamond IQ turns pitch-by-pitch tracking data into pre-game and in-game decisions: who to start, how hard to push them, and exactly how to attack tonight's lineup.

**Live demo:** [](https://diamondiq.streamlit.app/)

---

## Who is this for?

The MLB pitching coach — not a general manager, not a scout, not medical staff. One stakeholder, one job: deciding what a pitcher throws tonight and whether he stays in the game.

## What does it do?

Eight connected modules, each answering a specific question a coach faces before or during a start:

| Module | Question answered |
|---|---|
| Pitcher Scorecard | Where does he rank against the league right now? |
| Arsenal Profile | Is his mechanics where it should be? |
| Zone Intelligence | Is he hitting his spots? |
| Pitch Effectiveness | Which pitches are actually working? |
| Pitch Sequencing | Is he predictable, or setting hitters up? |
| Workload & Fatigue | Should he start, and when do we pull him? |
| Stuff Grade Model | How good is each pitch on a scout's 20-80 scale? |
| Game Planning Engine | How do we attack tonight's entire lineup? Includes a Monte Carlo at-bat simulator and a full 9-batter scouting report. |

## How does that help?

Every page ends with a plain-English recommendation, not just a chart. The Workload page gives a start/pull verdict. The Game Planning Engine generates a pitch-by-pitch script for every batter in the lineup before first pitch.

---

## Quick start (local)

```bash
git clone <your-repo-url>
cd DiamonIQ

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

streamlit run Home.py
```

The app downloads its season data automatically from Baseball Savant on first load (10-90 seconds depending on how much you click around). No manual setup script is required — `Home.py` bootstraps the roster on first run, and each pitcher's pitch-level data downloads the first time they're selected.

Optional: pre-warm the cache before launching, so the very first click is instant:

```bash
python scripts/01_download_base_data.py
python scripts/02_validate_setup.py
streamlit run Home.py
```

## Project structure

```
DiamonIQ/
├── Home.py                     Entry point — pitcher selector, who/what/how
├── pages/                      8 analytical modules + in-app documentation
├── src/
│   ├── components.py           Shared design system, charts, analytics functions
│   └── data_io/
│       ├── loaders.py          Baseball Savant + Statcast data access
│       └── cache.py            Parquet caching
├── config/
│   ├── settings.py             Season, thresholds, league benchmarks
│   └── theme.py                Legacy Plotly template registration
├── scripts/                    Optional pre-warm / validation scripts
├── data/raw/                   Cached Parquet files (gitignored, auto-created)
└── docs/
    └── user_manual.md          Full methodology, glossary, contribution statement
```

## Data sources

| Source | Content | Access |
|---|---|---|
| MLB Statcast | Pitch-level tracking — velocity, spin, movement, location, outcome | `pybaseball.statcast_pitcher()` |
| Baseball Savant | Season leaderboards — xwOBA, exit velocity, barrel rate | Direct CSV endpoint |

Season: 2024. Cache format: Apache Parquet. See `docs/user_manual.md` for full metric definitions and methodology.

## Tech stack

Streamlit · pandas · NumPy · Plotly · scikit-learn · SciPy · pybaseball

## License & academic context

Built for MIS41420 Sports & Performance Analytics, UCD Michael Smurfit Graduate Business School. See `docs/user_manual.md` for the group contribution statement.