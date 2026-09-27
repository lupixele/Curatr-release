# Curatr — PPT Prompt Context
> Full implementation context for generating a review presentation and adding the TMDb image feature.
> GitHub: https://github.com/lupixele/Curatr-release

---

## 1. Project Identity

| Field | Value |
|---|---|
| **Project Name** | Curatr |
| **Tagline** | Movie & TV Rating Analysis |
| **Team** | rei-nexus — Ratan (UI/Integration), Lochan (Maths/Scoring), Vivek (Data/API), Nagendra (Trends/Testing) |
| **Context** | DAE Capstone · Second-year Data Science · Aditya University |
| **Dataset window** | 2014–2023 (movies + TV) |
| **Source** | TMDb (The Movie Database) via Kaggle static dumps + live REST API |

---

## 2. Problem & Motivation (Abstract / Existing System)

**Problem:** Raw IMDb/TMDb ratings are biased — a film with 10 ratings averaging 9.0 ranks above a film with 50,000 ratings averaging 8.2. Popular opinion is drowned out by niche noise. Genre comparisons are unfair (Horror is structurally rated lower than Drama). There is no single open tool that normalises these effects for students and casual analysts.

**Existing systems & their limitations:**
- IMDb/TMDb public rankings: simple arithmetic mean, no vote-count normalization.
- Letterboxd: qualitative; no statistical scoring or trend charting.
- Academic papers: scoring formulas exist but are locked behind paywalls, no interactive UI.
- Manual Excel analysis: no live search, no genre decomposition, no trend visualization.

---

## 3. Proposed System

Curatr applies **Bayesian shrinkage scoring** to 930K+ movies and 150K+ TV shows, exposes two normalized scores per title, visualizes genre-level trends over a 10-year window (2014–2023), and allows live lookup of any title via the TMDb API — all within a single Streamlit dashboard.

**Two scores produced per title:**

### Global Score (Weighted Rating — WR)
```
WR = (v / (v + m)) × R  +  (m / (v + m)) × C
```
- `R` = title's raw TMDb vote_average
- `v` = title's vote_count
- `m` = 25th-percentile vote_count for the media type (minimum votes threshold)
- `C` = global mean rating for the media type

**Behaviour:** When `v = 0` → score = `C`. When `v = m` → score = midpoint of R and C. When `v >> m` → score ≈ R. This shrinks low-confidence titles toward the population average.

### Genre Score (Genre-Adjusted Rating)
```
GS = C  +  (v / (v + m)) × (R − G)
```
- `G` = genre baseline (mean rating of all titles in that genre; falls back to `C` if genre has < 30 titles)

**Behaviour:** Compares a title against its genre's average rather than the global mean. A Horror film scoring above its genre is correctly rewarded even if its raw rating is lower than a Drama.

---

## 4. Dataset Description

| Dataset | Source | Rows | Period |
|---|---|---|---|
| TMDb Movies | Kaggle — asaniczka (v11) | ~930K movies | 1900s–2023 |
| TMDb TV Shows | Kaggle — asaniczka (v3) | ~150K shows | 1950s–2024 |
| **Used window** | Filtered in prepare_data.py | 2014–2023, vote_count > 0, adult=False | 10 years |

**Limitations noted:**
- TV dataset snapshot from April 2024 — no 2024/2025 TV coverage.
- 2023 movie count is lower (~7,485 vs ~10K other years) — data lag.

**Contract schema** (8 columns after cleaning):
```
media_type | tmdb_id | title | release_year | rating | vote_count | genres | original_language
```

Genres stored as pipe-separated sorted strings: `Action|Adventure|Drama`

---

## 5. Requirements

**Functional:**
- Load and clean static TMDb CSV datasets
- Compute global baselines (C, m) and genre baselines per media type
- Score every title with global_score and genre_score
- Aggregate genre-year trend data (mean score, title count, YoY delta, comparison_status)
- Provide live search + detail fetch via TMDb REST API
- Render results in a Streamlit multi-tab dashboard

**Non-functional:**
- No hardcoded API keys — token from `.env` / environment variable `TMDB_TOKEN`
- All data files in `data/` — never committed raw CSVs to git (`.gitignore`)
- Tests must pass before any merge

**Dependencies (`requirements.txt`):**
```
pandas>=2.0
streamlit>=1.30
matplotlib>=3.7
requests>=2.28
python-dotenv>=1.0
```

**Python version:** 3.14.7  
**Platform:** Windows 11 (dev), any OS (portable)

---

## 6. Methodology (Pipeline)

```
[Raw Kaggle CSVs]
      ↓
prepare_data.py         ← Clean genres, unify schema, filter, export clean_titles.csv
      ↓
scoring.py              ← Compute baselines (C, m, per-genre means) → baselines.json
                        ← Score every title → scored_titles.csv
      ↓
trends.py               ← Explode genres, aggregate by (media_type, genre, year)
                        ← Fill 10-year calendar grid, compute YoY delta → genre_year.csv
      ↓
tmdb_client.py          ← Live API: search_titles(), fetch_title()
      ↓
app.py (Streamlit)      ← Load all artifacts, render 4-tab dashboard
```

### Key implementation details per module

**prepare_data.py**
- Reads `data/raw/TMDB_MV.csv` and `data/raw/TMDB_TV.csv`
- Normalizes genres: split on comma → deduplicate → sort → join with `|`
- Adds `media_type` column (`movie` / `tv`)
- Renames TV columns to match movie schema (`name→title`, `first_air_date→release_year`, `vote_average→rating`)
- Filters: `adult=False`, `vote_count > 0`, year ∈ [2014, 2023], no null tmdb_id/title
- Exports: `data/clean_titles.csv`

**scoring.py**
- `compute_media_baselines(sub_df)` → computes C, m, per-genre baselines (fallback to C when count < 30)
- `build_baselines(clean_df)` → splits by media_type, exports `data/baselines.json` (schema_version=1)
- `global_score(rating, vote_count, C, m)` → WR formula
- `genre_score(rating, vote_count, C, m, G)` → GS formula
- `score_title(record, baselines)` → resolves media_type, picks first genre, returns dict with both scores + status (`ok` / `unrated` / `unavailable`)
- Main block: loads clean_titles.csv, loads/builds baselines.json, scores all rows → `data/scored_titles.csv`

**trends.py**
- `build_trends(scored_df)` → explodes genre column, aggregates by (media_type, genre, release_year)
- Constructs full 10-year calendar grid (no missing years), merges aggregations, fills gaps
- Computes YoY delta and `comparison_status` (`improving` / `declining` / `stable` / `new` / `insufficient_data`)
- `plot_genre_trend(trend_df, media_type, genre)` → matplotlib figure (line chart, dual y-axes for score and title count)
- Main block: loads scored_titles.csv → exports `data/genre_year.csv`

**tmdb_client.py**
- `get_token()` → reads `TMDB_TOKEN` from env (raises ValueError if missing)
- `normalize_result(raw, media_type)` → maps search result fields to contract schema (genre_ids only, no names)
- `normalize_detail(raw, media_type)` → maps detail response, extracts full genre names from `genres` list of dicts
- `search_titles(query, media_type, page=1)` → `GET /search/{movie|tv}`, returns list of normalized dicts
- `fetch_title(tmdb_id, media_type)` → `GET /{movie|tv}/{id}`, returns normalized detail dict
- Error handling: `sanitize_error(e)` strips token from error messages before display

**app.py (Streamlit Dashboard)**
- `st.set_page_config(page_title="Curatr", layout="wide")`
- `@st.cache_data load_data()` → loads scored_titles.csv, genre_year.csv, baselines.json
- Sidebar: media_type radio, overview_year selector
- **Tab 1 — Overview:** year-filtered scored titles table for selected media_type/year
- **Tab 2 — Trends:** genre selector → plot_genre_trend() chart
- **Tab 3 — Search:** text input → search_titles() → result cards with score_title() applied
- **Tab 4 — Detail:** tmdb_id input → fetch_title() → full detail + scores

---

## 7. Frontend Dashboard (Screenshots & Layout Description)

Streamlit, `layout="wide"`, 4 tabs:

| Tab | Purpose | Key UI elements |
|---|---|---|
| Overview | Browse scored titles by year & media type | Sidebar filters, sortable dataframe |
| Trends | Genre trajectory 2014–2023 | Matplotlib line chart (dual y-axes: score + count) |
| Search | Live TMDb lookup with scores | Text input, result cards, Bayesian scores displayed |
| Detail | Full title info by TMDb ID | Metadata, genre breakdown, both scores |

---

## 8. Expected Outputs (per pipeline step)

| File | Description |
|---|---|
| `data/clean_titles.csv` | ~400-500K rows, 8 columns, 2014–2023 window |
| `data/baselines.json` | `{movie: {C, m, genres: {...}}, tv: {C, m, genres: {...}}}` |
| `data/scored_titles.csv` | clean_titles + `global_score`, `genre_score`, `score_status` |
| `data/genre_year.csv` | (media_type, genre, year) × (title_count, mean_genre_score, mean_raw_rating, yoy_delta, comparison_status) |

---

## 9. Project Workflow (Parallel 7-Day Roadmap)

| Day | Ratan (UI) | Lochan (Scoring) | Vivek (Data/API) | Nagendra (Trends/Tests) |
|---|---|---|---|---|
| 1 | Setup + Streamlit hello | Bayesian formula study | Kaggle download + schema | Git basics + branch |
| 2 | Sidebar + load CSV | global_score() + test | prepare_data.py | build_trends() scaffold |
| 3 | Tab 1 table render | genre_score() + test | tmdb_client search | plot_genre_trend() |
| 4 | Tab 2 chart embed | build_baselines() | fetch_title() + detail | test_trends.py |
| 5 | Tab 3 search UI | score_title() full | test_data.py | YoY delta + status |
| 6 | Tab 4 detail view | scoring.py main block | end-to-end integration | test_scoring.py assist |
| 7 | Full integration + PR | Review + fix | Review + fix | Final test run + report |

---

## 10. Test Coverage

| File | Test cases | Owner |
|---|---|---|
| `tests/test_scoring.py` | global_score formula, genre_score formula, build_baselines separation, score_title status rules | Lochan |
| `tests/test_data.py` | CSV header contract, no index column, genre delimiter, TMDb normalize functions, blank search guard | Vivek |
| `tests/test_trends.py` | multi-genre explosion, full grid coverage, YoY delta, comparison_status values | Nagendra |

All tests pass: `pytest tests/ -v` → **13 passed, 0 failed** (Python 3.14.7, pytest 9.1.1)

---

## 11. Pending Feature: TMDb Poster Images in Search

**What to add:** When `search_titles()` returns results in the Search tab (Tab 3), display each result's poster image alongside the title card.

**TMDb image API:**
- Base URL: `https://image.tmdb.org/t/p/`
- Poster sizes: `w92`, `w154`, `w185`, `w342`, `w500`, `w780`, `original`
- `poster_path` field: returned in both search results and detail responses (e.g. `/abc123.jpg`)
- Full URL: `https://image.tmdb.org/t/p/w185/abc123.jpg`
- No auth required for image fetches — public CDN

**What needs changing:**

1. **`tmdb_client.py → normalize_result()`** — add `poster_path` to the returned dict:
   ```python
   "poster_path": raw.get("poster_path"),  # e.g. "/abc123.jpg" or None
   ```

2. **`tmdb_client.py → normalize_detail()`** — same, add `poster_path`.

3. **`app.py → Tab 3 (Search)`** — for each result, build the image URL and display with `st.image()`:
   ```python
   TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w185"
   poster = result.get("poster_path")
   if poster:
       st.image(TMDB_IMG_BASE + poster, width=120)
   ```

**No new dependencies** — `st.image()` accepts a URL directly; requests are made by the browser.

---

## 12. PPT Slide Outline

Generate a PowerPoint with this exact slide order and these content points:

| Slide | Title | Key points |
|---|---|---|
| 1 | Abstract | One-para summary: fair Bayesian scoring for 1M+ titles using Kaggle TMDb data, 4-tab Streamlit dashboard, team of 4 |
| 2 | Introduction | Problem: rating bias. Why it matters. Who benefits (students, viewers, critics). Curatr as solution. |
| 3 | Existing System & Limitations | IMDb/TMDb: arithmetic mean. Letterboxd: no stats. No open interactive tool. Table of limitations. |
| 4 | Proposed System | Curatr architecture diagram: pipeline flow (CSV → prepare → score → trends → dashboard). Two formulas shown. |
| 5 | Dataset Description | Kaggle sources, row counts, date window, schema table (8 columns), known limitations (2023 lag, TV snapshot). |
| 6 | Requirements | Functional list (5 items), non-functional list (3 items), dependency table, Python version. |
| 7 | Methodology | Pipeline diagram, per-module bullets (what each file does in 1 line), formula boxes for WR and GS. |
| 8 | Frontend Dashboard | 4 tabs explained, Streamlit screenshot placeholder / layout wireframe, sidebar controls listed. |
| 9 | Expected Outputs | Table of all 4 output files with descriptions and row/column counts. |
| 10 | Project Workflow | 7-day table (4 members × 7 days), highlight Day 7 as integration day. |
| 11 | Conclusion | What was achieved: 13 tests passing, full pipeline, live TMDb search, genre trends. Future work: images feature, deployment, more years. Team member credit. |

**Visual style guidance:**
- Dark background (navy or charcoal), accent color teal/cyan
- Formula slides: render WR and GS formulas in a box with monospace font
- Use the name "Curatr" consistently — no "CURATR" all-caps
- Keep bullets to max 5 per slide
- Team slide: list all 4 names with their roles
