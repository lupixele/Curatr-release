# Curatr

### Movie & TV Rating Analysis · Team rei-nexus

**Ratan · Lochan · Vivek · Nagendra**
DAE Capstone · Second-year Data Science

Curatr analyzes movie and TV show ratings across 2014–2023 using two complementary scores — a global weighted score and a genre-adjusted score — to surface trends and fair comparisons across genres.

## Setup

```bash
git clone https://github.com/lupixele/curatr-release.git
cd curatr-release
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Data

Download from Kaggle (free account) and place in `data/raw/`:
- [Full TMDb Movies Dataset](https://www.kaggle.com/datasets/asaniczka/tmdb-movies-dataset-2023-930k-movies) → `TMDB_movie_dataset_v11.csv`
- [Full TMDb TV Shows Dataset](https://www.kaggle.com/datasets/asaniczka/full-tmdb-tv-shows-dataset-2023-150k-shows) → `TMDB_tv_dataset_v3.csv`

## Run

```bash
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
