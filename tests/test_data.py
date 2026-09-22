"""
tests/test_data.py — Data cleaning and API contract tests for Curatr.
Owner: Vivek
Run with: pytest tests/test_data.py -v
"""

import os
import sys

import pandas as pd
import pytest

# Make project root importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tmdb_client import sanitize_error, _normalize_details, search_titles


# ===========================================================================
# Section A: clean_titles.csv invariants
#   These tests are skipped if the file does not yet exist (before first run
#   of prepare_data.py). Run `python prepare_data.py` first to generate it.
# ===========================================================================

CLEAN_CSV = os.path.join(os.path.dirname(__file__), "..", "data", "clean_titles.csv")
EXPECTED_HEADER = [
    "media_type", "tmdb_id", "title", "release_year",
    "rating", "vote_count", "genres", "original_language",
]

skip_if_no_csv = pytest.mark.skipif(
    not os.path.exists(CLEAN_CSV),
    reason="data/clean_titles.csv not found — run `python prepare_data.py` first"
)


@skip_if_no_csv
def test_csv_exact_header():
    """The CSV must have exactly the eight required contract columns."""
    df = pd.read_csv(CLEAN_CSV, nrows=0)
    assert list(df.columns) == EXPECTED_HEADER, (
        f"Header mismatch.\nExpected: {EXPECTED_HEADER}\nGot:      {list(df.columns)}"
    )


@skip_if_no_csv
def test_csv_no_index_column():
    """The CSV must not contain an unnamed index column."""
    df = pd.read_csv(CLEAN_CSV, nrows=0)
    unnamed = [c for c in df.columns if c.startswith("Unnamed")]
    assert unnamed == [], f"Found unexpected index column(s): {unnamed}"


@skip_if_no_csv
def test_csv_composite_key_uniqueness():
    """No (media_type, tmdb_id) pair may appear more than once."""
    df = pd.read_csv(CLEAN_CSV, usecols=["media_type", "tmdb_id"])
    dup_count = df.duplicated(subset=["media_type", "tmdb_id"]).sum()
    assert dup_count == 0, f"Found {dup_count} duplicate composite key(s)."


@skip_if_no_csv
def test_csv_release_year_bounds():
    """All release_year values must be within the 2014–2023 reference window."""
    df = pd.read_csv(CLEAN_CSV, usecols=["release_year"])
    out_of_range = df[~df["release_year"].between(2014, 2023)]
    assert len(out_of_range) == 0, (
        f"{len(out_of_range)} row(s) have release_year outside [2014, 2023]."
    )


@skip_if_no_csv
def test_csv_rating_bounds():
    """All rating values must be between 0.0 and 10.0 (inclusive)."""
    df = pd.read_csv(CLEAN_CSV, usecols=["rating"])
    out_of_range = df[~df["rating"].between(0.0, 10.0)]
    assert len(out_of_range) == 0, (
        f"{len(out_of_range)} row(s) have rating outside [0.0, 10.0]."
    )


@skip_if_no_csv
def test_csv_vote_count_positive():
    """All vote_count values must be > 0 (unrated titles excluded from reference data)."""
    df = pd.read_csv(CLEAN_CSV, usecols=["vote_count"])
    zero_votes = df[df["vote_count"] <= 0]
    assert len(zero_votes) == 0, (
        f"{len(zero_votes)} row(s) have vote_count <= 0."
    )


@skip_if_no_csv
def test_csv_genre_formatting():
    """
    Genres must be non-empty, pipe-delimited, alphabetically sorted,
    with no leading/trailing spaces around each tag.
    """
    df = pd.read_csv(CLEAN_CSV, usecols=["genres"])
    for _, row in df.iterrows():
        genres = row["genres"]
        assert isinstance(genres, str) and genres.strip(), "Empty genre found."
        tags = genres.split("|")
        for tag in tags:
            assert tag == tag.strip(), f"Genre tag has extra whitespace: {tag!r}"
        assert tags == sorted(set(tags)), (
            f"Genres not sorted/deduplicated: {genres!r}"
        )


@skip_if_no_csv
def test_csv_media_type_values():
    """media_type column must only contain 'movie' or 'tv'."""
    df = pd.read_csv(CLEAN_CSV, usecols=["media_type"])
    invalid = df[~df["media_type"].isin(["movie", "tv"])]
    assert len(invalid) == 0, f"Invalid media_type values found: {invalid['media_type'].unique()}"


# ===========================================================================
# Section B: tmdb_client — search_titles contract tests (no live network)
# ===========================================================================

def test_search_titles_empty_query_returns_empty_structure():
    """Empty query must return the contract empty dict without a network call."""
    result = search_titles("", "movie")
    assert result == {"page": 1, "total_pages": 0, "results": []}


def test_search_titles_blank_whitespace_query():
    """Whitespace-only query must also return empty structure."""
    result = search_titles("   ", "tv")
    assert result == {"page": 1, "total_pages": 0, "results": []}


def test_search_titles_invalid_media_type_raises():
    """Non-'movie'/'tv' media_type must raise ValueError before any network call."""
    with pytest.raises(ValueError, match="Invalid media_type"):
        search_titles("Inception", "anime")


# ===========================================================================
# Section C: _normalize_details — contract shape and field correctness
# ===========================================================================

MOCK_MOVIE_DETAILS = {
    "id":                550,
    "title":             "Fight Club",
    "release_date":      "1999-10-15",
    "vote_average":      8.433,
    "vote_count":        27000,
    "genres":            [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}],
    "original_language": "en",
}

MOCK_TV_DETAILS = {
    "id":                1396,
    "name":              "Breaking Bad",
    "first_air_date":    "2008-01-20",
    "vote_average":      9.5,
    "vote_count":        14000,
    "genres":            [{"id": 80, "name": "Crime"}, {"id": 18, "name": "Drama"}],
    "original_language": "en",
}


def test_normalize_details_movie_keys():
    """Normalized movie dict must contain all nine contract keys."""
    result = _normalize_details(MOCK_MOVIE_DETAILS, "movie")
    expected_keys = {
        "media_type", "tmdb_id", "title", "release_year",
        "rating", "vote_count", "genres", "original_language", "fetched_at",
    }
    assert set(result.keys()) == expected_keys


def test_normalize_details_movie_values():
    """Normalized movie values must match expected contract values."""
    result = _normalize_details(MOCK_MOVIE_DETAILS, "movie")
    assert result["media_type"]   == "movie"
    assert result["tmdb_id"]      == 550
    assert result["title"]        == "Fight Club"
    assert result["release_year"] == 1999
    assert result["rating"]       == round(8.433, 4)
    assert result["vote_count"]   == 27000
    assert result["genres"]       == "Drama|Thriller"   # sorted alphabetically
    assert result["original_language"] == "en"
    assert result["fetched_at"].endswith("Z")


def test_normalize_details_tv_uses_name_and_first_air_date():
    """TV details must use 'name' for title and 'first_air_date' for year."""
    result = _normalize_details(MOCK_TV_DETAILS, "tv")
    assert result["media_type"]   == "tv"
    assert result["title"]        == "Breaking Bad"
    assert result["release_year"] == 2008
    assert result["genres"]       == "Crime|Drama"


def test_normalize_details_genres_sorted_and_deduplicated():
    """Genres must be alphabetically sorted and deduplicated."""
    raw = {**MOCK_MOVIE_DETAILS, "genres": [
        {"id": 53, "name": "Thriller"},
        {"id": 18, "name": "Drama"},
        {"id": 18, "name": "Drama"},   # duplicate
    ]}
    result = _normalize_details(raw, "movie")
    assert result["genres"] == "Drama|Thriller"


def test_normalize_details_zero_vote_count_preserved():
    """
    vote_count == 0 must be retained (not filtered) so Lochan's score_title()
    can flag the title as 'unrated'.
    """
    raw = {**MOCK_MOVIE_DETAILS, "vote_count": 0, "vote_average": 0.0}
    result = _normalize_details(raw, "movie")
    assert result["vote_count"] == 0


def test_normalize_details_missing_release_date_returns_none():
    """Missing/blank release_date must produce release_year == None (no crash)."""
    raw = {**MOCK_MOVIE_DETAILS, "release_date": ""}
    result = _normalize_details(raw, "movie")
    assert result["release_year"] is None


def test_normalize_details_fetched_at_is_utc_iso():
    """fetched_at must be a UTC ISO 8601 string ending with 'Z'."""
    result = _normalize_details(MOCK_MOVIE_DETAILS, "movie")
    assert isinstance(result["fetched_at"], str)
    assert result["fetched_at"].endswith("Z")


# ===========================================================================
# Section D: sanitize_error — token masking
# ===========================================================================

def test_sanitize_error_masks_bearer_token():
    """Bearer tokens must be redacted from error messages."""
    leaky = "Error: Authorization: Bearer eyJsecretToken123ABC"
    masked = sanitize_error(leaky)
    assert "eyJsecretToken123ABC" not in masked
    assert "[MASKED]" in masked


def test_sanitize_error_leaves_non_secret_text():
    """Non-secret text must not be altered by sanitize_error."""
    msg = "Connection refused: host unreachable"
    assert sanitize_error(msg) == msg


def test_sanitize_error_multiple_tokens():
    """All Bearer token occurrences in a string must be masked."""
    leaky = "Bearer token1abc and Bearer token2xyz"
    masked = sanitize_error(leaky)
    assert "token1abc" not in masked
    assert "token2xyz" not in masked
