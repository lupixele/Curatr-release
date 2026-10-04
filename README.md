# Curatr

### Movie & Series Trends Analysis · Team rei-nexus

**Ratan · Lochan · Vivek · Nagendra**
DAE Capstone · Second-year Data Science

Curatr analyzes movie and TV show ratings across 2014–2023 using two complementary scores — a global weighted score and a genre-adjusted score — to surface trends and fair comparisons across genres.

## Setup

```powershell
git clone https://github.com/lupixele/curatr-release.git
cd curatr-release
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Data

Download from Kaggle (free account) and place in `data/raw/`:
- [Full TMDb Movies Dataset](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies) → `TMDB_movie_dataset_v11.csv`
- [Full TMDb TV Shows Dataset](https://www.kaggle.com/datasets/asaniczka/full-tmdb-tv-shows-dataset-2023-150k-shows) → `TMDB_tv_dataset_v3.csv`

## Run

```powershell
python prepare_data.py          # Clean raw CSVs
python scoring.py               # Compute baselines and scores
python trends.py                # Build genre-year trend data
streamlit run app.py            # Launch dashboard
```

## Environment

Create a `.env` file (never commit this):
```
TMDB_TOKEN=your_tmdb_bearer_token_here
```

## Team

| Member | Role | Owned Files |
|---|---|---|
| Ratan | UI & Integration | `app.py`, `requirements.txt`, `README.md` |
| Lochan | Maths & Scoring | `scoring.py`, `tests/test_scoring.py` |
| Vivek | Data & API | `prepare_data.py`, `tmdb_client.py`, `tests/test_data.py` |
| Nagendra | Trends & Testing | `trends.py`, `tests/test_trends.py` |

Development docs, guides, and research: [Curatr-dev](https://github.com/lupixele/Curatr-dev)

## Rating threshold and charts

The shrinkage threshold `m` is the 75th percentile of vote counts for each
media type: 9 for movies and 10 for TV in the stored 2014–2023 snapshot.
The former 25th-percentile rule gave `m = 1` because many titles have one vote.
The new rule reduces their influence without changing either score formula.
It is a conservative robustness choice, not an empirically optimized threshold.
The minimum-votes ranking filter controls eligibility separately.

Run `scoring.py` and then `trends.py` together after changing the threshold:
the app uses `baselines.json` for live search, `scored_titles.csv` for rankings,
and `genre_year.csv` for trends. All three must describe the same scoring policy.

In Overview, enable **Show dataset charts** to choose a genre count bar chart,
media share pie chart, rating/score histogram, genre rating box plot,
vote/rating scatter plot, or genre-year heatmap. These summarize the full
reference snapshot independently of the ranking year/minimum-votes filters.
The existing single-genre line chart remains in Trends.
