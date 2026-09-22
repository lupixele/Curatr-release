# docs/DATA_SOURCES.md — Data Provenance, Checksums & Research Ethics
# Owner: Vivek | Curatr Project

# DATA_SOURCES.md

## Overview

This document records the provenance, integrity checksums, schema definitions,
exclusion rules, and research ethics considerations for all raw data files used
by `prepare_data.py` to produce `data/clean_titles.csv`.

> **Ongoing Kaggle Audit Notice:** A data audit of candidate Kaggle sources is
> currently running. Do **not** assert final row counts, snapshot scrape dates,
> or definitive filenames until the audit is complete.

---

## 1. Raw Data Sources

### Movie Dataset

| Attribute | Value |
|-----------|-------|
| **Filename** | `candidate_movies_raw.csv` *(placeholder filename — pending audit decision)* |
| **Source** | TMDb / Kaggle public dataset |
| **URL** | *(pending audit decision — will be pinned after source confirmation)* |
| **License** | CC BY-NC 4.0 (TMDb attribution required) |
| **TMDb Attribution** | This product uses the TMDb API but is not endorsed or certified by TMDb. |
| **Snapshot Date** | *(pending audit decision — will be recorded after download)* |
| **SHA-256 Checksum** | *(pending — compute after confirmed download, see Section 3)* |

### TV Series Dataset

| Attribute | Value |
|-----------|-------|
| **Filename** | `candidate_tv_raw.csv` *(placeholder filename — pending audit decision)* |
| **Source** | TMDb / Kaggle public dataset |
| **URL** | *(pending audit decision — will be pinned after source confirmation)* |
| **License** | CC BY-NC 4.0 (TMDb attribution required) |
| **Snapshot Date** | *(pending audit decision)* |
| **SHA-256 Checksum** | *(pending — compute after confirmed download, see Section 3)* |

---

## 2. Schema Definitions

### Raw Movie Columns Used

| Column | Type | Description |
|--------|------|-------------|
| `id` | integer | TMDb movie ID → renamed `tmdb_id` |
| `title` | string | Movie title |
| `release_date` | string (ISO 8601) | Release date → year extracted |
| `vote_average` | float | TMDb rating (0.0–10.0) → renamed `rating` |
| `vote_count` | integer | Number of user ratings |
| `genres` | string | Serialized list of genre objects |
| `original_language` | string | ISO 639-1 language code |
| `adult` | boolean | Adult content flag |

### Raw TV Columns Used

| Column | Type | Description |
|--------|------|-------------|
| `id` | integer | TMDb TV ID → renamed `tmdb_id` |
| `name` | string | Series title → renamed `title` |
| `first_air_date` | string (ISO 8601) | Series premiere date → year extracted |
| `vote_average` | float | TMDb rating → renamed `rating` |
| `vote_count` | integer | Number of ratings |
| `genres` | string | Serialized genre list |
| `original_language` | string | ISO 639-1 code |
| `adult` | boolean | Adult content flag |

### Clean Output Schema (`data/clean_titles.csv`)

| Column | Type | Constraints |
|--------|------|-------------|
| `media_type` | string | `'movie'` or `'tv'` (lowercase) |
| `tmdb_id` | integer | Positive integer; unique within `media_type` |
| `title` | string | Non-empty |
| `release_year` | integer | 2014–2023 (reference window) |
| `rating` | float | 0.0–10.0 |
| `vote_count` | integer | > 0 for reference titles |
| `genres` | string | Alphabetically sorted, pipe-delimited (e.g. `Action\|Drama`) |
| `original_language` | string | ISO 639-1 code, or empty string |

> **Composite Primary Key:** `(media_type, tmdb_id)`. TMDb maintains independent
> ID sequences for movies and TV — the same integer ID can appear in both.
> Never use `tmdb_id` alone as a unique identifier.

---

## 3. SHA-256 Checksum Verification

To verify a downloaded raw file matches the original source, compute its checksum
before running `prepare_data.py`.

### PowerShell (Windows)

```powershell
# Compute checksum
Get-FileHash data\raw\candidate_movies_raw.csv -Algorithm SHA256

# Or using sha256sum if available
sha256sum data/raw/candidate_movies_raw.csv
```

### Python (for documentation or scripting)

```python
import hashlib

def sha256_file(path: str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

print(sha256_file("data/raw/candidate_movies_raw.csv"))
```

**Record the output here after each confirmed download.**

---

## 4. Exclusion Rules

`prepare_data.py` tracks and logs all excluded records. The categories are:

| Exclusion Reason | Rule Applied |
|-----------------|-------------|
| `missing_title` | `title` is `NaN`, empty, or whitespace-only |
| `unparseable_or_out_of_range_year` | `release_date`/`first_air_date` cannot be parsed, or year is outside 2014–2023 |
| `unrated_or_zero_votes` | `vote_count <= 0` (title has no ratings) |
| `adult_content` | `adult == True` (explicitly flagged) |
| `missing_genres` | Genre list is empty or entirely unparseable |
| `duplicate_records` | Duplicate `(media_type, tmdb_id)` composite key — first occurrence is kept |

> **No Silent Imputation:** Records are never guessed, patched, or silently dropped.
> All exclusion counts are printed at runtime and should be recorded in PR descriptions.

---

## 5. Research Ethics: Avoiding Historical Bias

### Survivorship Bias

Our dataset is a **single 2026 snapshot** of TMDb, not a continuous longitudinal
survey conducted from 2014 to 2023. This has important implications:

- **Obscure older titles** (especially from 2014–2016) may be absent or
  under-represented because they attracted few votes and were not indexed
  by modern aggregators.
- **Well-regarded older titles** retain high vote counts because engaged
  communities continue rating them.
- **Recent titles** (2022–2023) may have volatile vote counts reflecting
  recency excitement or early-adopter bias.

### Accurate Framing

✅ **Correct:** *"This reflects TMDb ratings recorded at snapshot time (2026),
grouped by title release year."*

❌ **Incorrect:** *"Audiences in 2016 gave movies higher ratings than audiences
in 2023."*

All team reports, viva presentations, and PR descriptions must use the accurate
framing above.

---

## 6. Reproduction Instructions

Any teammate can reproduce `data/clean_titles.csv` from scratch on a clean clone:

```powershell
# 1. Clone and set up environment
git clone <repo-url>
cd Curatr-release
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2. Place raw files in data/raw/
#    (download from URLs listed in Section 1 after audit decision)

# 3. Run the cleaning pipeline
python prepare_data.py

# 4. Verify output
python -c "import pandas as pd; df = pd.read_csv('data/clean_titles.csv'); print(df.shape, list(df.columns))"
```

The output `data/clean_titles.csv` is intentionally excluded from Git
(see `.gitignore`). It must be regenerated locally.

---

*Document maintained by: Vivek | Last updated: 2026-09-22*
*Part of the Curatr project — see `docs/03-data-and-function-contracts.md` for
official team contracts.*
