# Diamond IQ — User Manual
## MIS41420 Sports & Performance Analytics
### Pitching Intelligence Suite — Season 2024

---

## 1. Purpose

Diamond IQ is a Statcast-powered pitching analytics platform built for **MLB Pitching Coaches and Performance Directors**. 

The tool processes pitch-by-pitch tracking data to answer the specific questions a coach asks before, during, and after a game:

- *Where does my pitcher rank in the league right now?*
- *Is his stuff where it should be mechanically?*
- *Is he showing signs of fatigue — should I pull him?*
- *How do we attack tomorrow's opposing lineup?*

Every analytical page ends with a **Coach's Insight panel** — a plain-English, actionable recommendation that a non-analyst coach can read and act on immediately.

---

## 2. System Requirements

| Requirement | Minimum |
|-------------|---------|
| Python | 3.10+ |
| RAM | 4 GB |
| Disk | 2 GB (for cached Parquet files) |
| Internet | Required for first-time data download |

**Dependencies** (install via `pip install -r requirements.txt`):
```
streamlit
pandas
numpy
plotly
pybaseball
scikit-learn
scipy
pyarrow
requests
```

---

## 3. Installation & First Run

```bash
# 1. Clone or unzip the project
cd DiamonIQ

# 2. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Download base data (first time only — ~2-4 minutes)
python scripts/01_download_base_data.py

# 5. Launch the app
streamlit run Home.py
```

The app will open at `http://localhost:8501`.

---

## 4. File Structure

```
DiamonIQ/
├── Home.py                          # Entry point — pitcher selector
├── pages/
│   ├── 1_Pitcher_Scorecard.py       # Percentile radar vs MLB
│   ├── 2_Arsenal_Profile.py         # Movement, spin, release point
│   ├── 3_Zone_Intelligence.py       # Location heatmaps
│   ├── 4_Pitch_Effectiveness.py     # Run Value, CSW%, xwOBA
│   ├── 5_Pitch_Sequencing.py        # Markov matrices
│   ├── 6_Workload_and_Fatigue.py    # ACWR, velocity decay
│   ├── 7_Stuff_Grade_Model.py       # ML 20-80 grade
│   ├── 8_Game_Planning_Engine.py    # Prescriptive matchup tool
│   └── 9_Documentation.py          # In-app user manual
├── src/
│   ├── components.py                # Shared UI, metrics, analytics functions
│   └── data_io/
│       ├── loaders.py               # Baseball Savant + Statcast data access
│       └── cache.py                 # Parquet caching helpers
├── config/
│   ├── settings.py                  # SEASON, paths
│   └── theme.py                     # Plotly theme registration
├── scripts/
│   └── 01_download_base_data.py     # One-time base data download
├── data/
│   └── raw/                         # Auto-created — cached Parquet files
└── docs/
    └── user_manual.md               # This file
```

---

## 5. How to Use — Step by Step

### Step 1: Select a pitcher
Use the **sidebar dropdown** on any page to select a pitcher. The sidebar shows on every page.

- The dropdown contains all MLB pitchers with ≥ 10 batters faced in the 2024 season.
- Selecting a pitcher for the first time triggers a Statcast download (30–90 seconds).
- A progress spinner displays while data loads. All subsequent page navigations are instant.

### Step 2: Review the Scorecard (Page 1)
- See 6 KPI cards with colour-coded status (green/amber/red).
- The percentile radar compares the pitcher to all MLB starters on velocity, CSW%, whiff%, xwOBA, spin rate, and K%.
- Strengths and development areas are listed below the radar.

### Step 3: Check Arsenal Profile (Page 2)
- The movement scatter shows horizontal break vs induced vertical break for each pitch.
- Use the pitch type multiselect to isolate specific pitches.
- Release point drift is measured automatically — a red flag appears if drift exceeds 1 inch.

### Step 4: Zone Intelligence (Page 3)
- Use the sidebar filters to change pitch type, batter handedness, and outcome type.
- The heatmap shows where pitches are being located — dark red = high concentration.
- Zone% by count reveals where command breaks down.

### Step 5: Pitch Effectiveness (Page 4)
- The Run Value chart (bar chart) shows each pitch's value in runs saved/surrendered.
- The CSW% vs Whiff% quadrant chart plots all pitches by quality.
- The xwOBA trend shows whether contact quality is improving or degrading over the season.

### Step 6: Pitch Sequencing (Page 5)
- The Markov transition matrix shows the probability of each follow-up pitch.
- Dark cells = heavily used transitions (potentially predictable).
- The predictability index scores each pitch from 0–100%.
- Two-strike pitch selection shows what is actually thrown vs what generates the most whiffs.

### Step 7: Workload & Fatigue (Page 6)
- Adjust the ACWR windows in the sidebar (default: 7-day acute / 28-day chronic).
- The traffic light gives an immediate green/amber/red recommendation.
- Velocity decay regression shows whether velocity is dropping significantly within starts.
- Release point drift tracks mechanical consistency over the last 5 starts.

### Step 8: Stuff Grade Model (Page 7)
- Grades are on the 20-80 scout scale (50 = MLB average).
- The gauge shows an overall weighted stuff grade.
- The feature table shows which physical attributes (velocity, spin, movement) drive the grade.

### Step 9: Game Planning (Page 8)
- Select an opposing batter from the sidebar dropdown.
- The threat level (HIGH/MEDIUM/LOW) is determined by their xwOBA.
- A prescriptive pitch sequence script is generated: what to throw first, what to use as a putaway, what to avoid.
- The quick-reference table provides a count-by-count guide for in-game use.

---

## 6. Configurable Settings

| Setting | Where | Default | Effect |
|---------|-------|---------|--------|
| Season year | `config/settings.py` → `SEASON` | 2024 | Load a different MLB season |
| Acute ACWR window | Page 6 sidebar slider | 7 days | Sensitivity to short-term workload spikes |
| Chronic ACWR window | Page 6 sidebar slider | 28 days | Long-term fitness baseline length |
| Pitch type filter | Page 2, 3 sidebars | All | Isolate specific pitch types |
| Batter handedness | Page 3, 8 sidebars | All / R | Filter analysis to LHB or RHB matchups |
| Minimum PA threshold | `src/data_io/loaders.py` → `pa >= 10` | 10 | Filter out position players from roster |

---

## 7. Interpreting Outputs

### Green / Amber / Red KPI cards
- **Green:** Above MLB average threshold for this metric.
- **Amber:** Within acceptable range but approaching a flag threshold.
- **Red:** Below average or flagged — requires attention or action.

### Coach's Insight panel
Each page ends with a navy highlighted box containing:
- A 1-2 sentence summary of what the data means.
- A specific recommended action (prefixed with ▶).

These are designed to be read by a pitching coach without analytical background and to drive immediate decisions.

### Percentile ranks
Displayed as `Xth pct` badges throughout. 50th pct = MLB average. 
80th+ pct = elite. Below 30th pct = development priority.

---

## 8. Troubleshooting

| Problem | Solution |
|---------|----------|
| Roster shows 0 rows | Run `python scripts/01_download_base_data.py` |
| 403 error on FanGraphs | Already resolved — all data now uses Baseball Savant endpoints |
| Pitcher not in dropdown | Pitcher had fewer than 10 BF in 2024; lower the threshold in loaders.py |
| Charts not rendering | Ensure plotly ≥ 5.18 is installed |
| Statcast download fails | Check internet connection; retry — Baseball Savant occasionally rate-limits |
| Memory error | Reduce season scope or increase available RAM |

---

## 9. Data Sources & Citations

- **MLB Statcast** — Baseball Savant (baseballsavant.mlb.com). Pitch-level tracking data including velocity, spin rate, movement, location, and outcome.
- **pybaseball** — Healey, J. (2020). pybaseball: A Python package for baseball data analysis. GitHub: jldbc/pybaseball.
- **ACWR methodology** — Gabbett, T.J. (2016). The training-injury prevention paradox. *British Journal of Sports Medicine*, 50(5), 273–280.
- **Run Value** — Baseball Savant delta_run_exp metric, based on RE24 (Run Expectancy 24 base-out states).
- **CSW%** — Baseball Savant. Industry-standard pitch quality metric.
- **Stuff Grade methodology** — Adapted from Trackman/Hawkeye-based Stuff+ models used in MLB front offices.

---

## 10. Group Member Contribution Statement

| Member | Contribution |
|--------|-------------|
| [Member 1 — Name] | Phase 1: Project architecture, data pipeline, Baseball Savant integration, caching system, Home.py |
| [Member 2 — Name] | Phase 2: Pages 1–3 (Scorecard, Arsenal Profile, Zone Intelligence), shared components.py |
| [Member 3 — Name] | Phase 2: Pages 4–5 (Pitch Effectiveness, Sequencing), Markov chain implementation |
| [Member 4 — Name] | Phase 2: Pages 6–7 (Workload & Fatigue, Stuff Grade), ACWR and logistic regression models |
| [Member 5 — Name] | Phase 2: Page 8 (Game Planning Engine), Page 9 (Documentation), user manual |

*All members contributed to overall system design, testing, and documentation review.*

---

*Diamond IQ v1.0 · MIS41420 Sports & Performance Analytics · University College Dublin*  
*Data: MLB Statcast 2024 season via Baseball Savant*
