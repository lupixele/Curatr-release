# Curatr — PPT Context
GitHub: https://github.com/lupixele/Curatr-release

---

## Project Identity

| Field | Value |
|---|---|
| Name | Curatr |
| Tagline | Movie and TV Rating Analysis |
| Team | rei-nexus |
| Context | DAE Capstone, Second-year Data Science, Aditya University |
| Dataset window | 2014–2023 (movies + TV shows) |
| Data source | TMDb via Kaggle static dumps + live TMDb REST API |

---

## Problem and Motivation

Raw TMDb/IMDb ratings are unreliable for comparison. A title with 10 ratings averaging 9.0 outranks one with 50,000 ratings averaging 8.2. Genre comparisons are also unfair: Horror is structurally rated lower than Drama, so direct comparison across genres is meaningless.

Existing tools and their gaps:

| Tool | Limitation |
|---|---|
| IMDb / TMDb public rankings | Simple arithmetic mean, no vote-count normalization |
| Letterboxd | Qualitative only, no statistical scoring or trend charts |
| Academic scoring models | Formulas exist but no interactive accessible implementation |
| Manual Excel analysis | No live search, no genre decomposition, no visualization |

No open tool brings fair scoring, genre context, and trend analysis together in one place.

---

## Proposed System

Curatr applies Bayesian shrinkage scoring to 930K+ movies and 150K+ TV shows, producing two normalized scores per title, visualizing genre-level trends across 2014–2023, and enabling live lookup of any title via the TMDb API — all in a single Streamlit dashboard.

---

## Dataset

| Dataset | Source | Scale |
|---|---|---|
| TMDb Movies | Kaggle, asaniczka v11 | ~930K entries |
| TMDb TV Shows | Kaggle, asaniczka v3 | ~150K entries |

Filtered to: 2014–2023, vote_count > 0, adult = False.
Known limits: 2023 movie count is lower (~7,485 vs ~10K) due to data lag; TV snapshot from April 2024.

Schema after cleaning (8 columns):
  media_type | tmdb_id | title | release_year | rating | vote_count | genres | original_language

Genres stored as pipe-separated sorted strings, e.g. Action|Adventure|Drama

---

## Requirements

Functional:
- Clean and normalize raw TMDb CSV datasets
- Compute Bayesian baselines (global + per-genre) for movies and TV separately
- Score every title with two normalized scores
- Aggregate genre-year trend data with year-over-year delta
- Live title search and detail fetch via TMDb REST API
- Render everything in an interactive Streamlit dashboard

Non-functional:
- API token loaded from environment only, never hardcoded
- Raw CSVs never committed (too large); processed data files version-controlled
- All tests must pass before any merge

Stack: pandas>=2.0, streamlit>=1.30, matplotlib>=3.7, requests>=2.28, python-dotenv>=1.0

---

## Scoring Methodology

Two scores are computed per title.

### Global Score (Weighted Rating)

  WR = (v / (v + m)) * R  +  (m / (v + m)) * C

Variables:
  R = title raw TMDb vote average
  v = title vote count
  m = 25th-percentile vote count for the media type
  C = global mean rating for the media type

Behaviour: v=0 gives score=C. v much larger than m gives score near R. Low-confidence titles shrink toward the population mean.

### Genre Score (Genre-Adjusted Rating)

  GS = C  +  (v / (v + m)) * (R - G)

Variables:
  G = genre baseline mean (falls back to C if genre has fewer than 30 titles)

Behaviour: Compares a title against its own genre average. A Horror film above its genre peers is rewarded even if its raw score is lower than a Drama.

---

## Pipeline

  Raw Kaggle CSVs
        |
  prepare_data.py  -->  data/clean_titles.csv
        |
  scoring.py       -->  data/baselines.json + data/scored_titles.csv
        |
  trends.py        -->  data/genre_year.csv
        |
  tmdb_client.py   -->  live TMDb API (search + detail)
        |
  app.py           -->  Streamlit dashboard (4 tabs)

What each stage does:
- prepare_data.py: cleans genres, unifies movie/TV schema, filters year window, drops invalid rows
- scoring.py: computes C and m, per-genre baselines with fallback for small genres, scores all titles
- trends.py: explodes genre column, builds full 10-year grid, computes YoY delta and comparison_status
- tmdb_client.py: wraps TMDb REST API for search and detail; sanitizes errors so token never leaks
- app.py: loads all data artifacts and renders the 4-tab Streamlit dashboard

---

## Dashboard

Streamlit, wide layout, sidebar + 4 tabs:

| Tab | What it does |
|---|---|
| Overview | Browse scored titles filtered by media type and year |
| Trends | Select any genre, see line chart of score + title count across 2014–2023 |
| Search | Live TMDb search with both Bayesian scores on each result card |
| Detail | Fetch any title by TMDb ID — full metadata, genre, and both scores |

Sidebar controls: media type toggle (movie / TV), year selector (2014–2023).

---

## Output Files

| File | Description |
|---|---|
| data/clean_titles.csv | ~400-500K rows, unified schema, filtered window |
| data/baselines.json | Movie and TV baselines with C, m, and per-genre means |
| data/scored_titles.csv | clean_titles plus global_score, genre_score, score_status |
| data/genre_year.csv | Per (media_type, genre, year): mean scores, title count, YoY delta, comparison_status |

---

## Tests

13 tests, all passing (pytest tests/ -v, Python 3.14.7):

| File | What it covers |
|---|---|
| test_scoring.py | WR formula, GS formula, baseline separation, status rules |
| test_data.py | CSV schema contract, genre normalization, TMDb normalize functions, blank search guard |
| test_trends.py | Genre explosion, full 10-year grid, YoY delta, comparison_status values |

---

## Pending Feature: Poster Images in Search

TMDb search results include a poster_path field (e.g. /abc123.jpg). Images are served from a public CDN with no auth needed:

  https://image.tmdb.org/t/p/w185/abc123.jpg

Changes needed:
1. tmdb_client.py: add poster_path to the returned dict in both normalize_result() and normalize_detail()
2. app.py Tab 3 (Search): render st.image("https://image.tmdb.org/t/p/w185" + poster_path, width=120) for each result

No new dependencies. st.image() accepts URLs directly.

---

## PPT Slide Outline

| Slide | Title | Key Content |
|---|---|---|
| 1 | Abstract | Problem, approach (Bayesian scoring), scale (1M+ titles), output (Streamlit dashboard) |
| 2 | Introduction | Rating bias problem, why it matters, Curatr as the solution |
| 3 | Existing System and Limitations | Table: IMDb, Letterboxd, academic papers, Excel — each with their specific gap |
| 4 | Proposed System | Pipeline flow diagram + two formula boxes for WR and GS |
| 5 | Dataset Description | Sources table, row counts, 8-column schema, known data limitations |
| 6 | Requirements | Functional list, non-functional list, dependency table |
| 7 | Methodology | Pipeline diagram, one-line per stage, formula variable tables |
| 8 | Frontend Dashboard | Tab breakdown table, sidebar controls, layout description |
| 9 | Expected Outputs | 4-file output table with row counts and descriptions |
| 10 | Project Workflow | Phases: data collection, scoring, trends, integration, testing, deployment |
| 11 | Conclusion | What was achieved (13/13 tests, full pipeline, live search), future work (poster images, more years) |

Style: use from the provided pdf style