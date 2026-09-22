"""
tmdb_client.py — Live TMDb API client for Curatr.
Owner: Vivek
Consumer: Ratan (app.py)

Provides:
    search_titles(query, media_type, page=1) -> dict
    fetch_title(tmdb_id, media_type)         -> dict

Authentication:
    Reads TMDB_TOKEN from environment variable (never hardcoded).
    Set it in PowerShell before running:
        $env:TMDB_TOKEN = Read-Host "Enter TMDB token" -MaskInput

Contract:
    See docs/members/03-vivek-data-and-api.md and
    docs/03-data-and-function-contracts.md for full schema.
"""

import os
import re
from datetime import datetime, timezone

import requests


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TMDB_BASE = "https://api.themoviedb.org/3"
TIMEOUT   = 10  # seconds

VALID_MEDIA_TYPES = {"movie", "tv"}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_token() -> str:
    """Read TMDB_TOKEN from environment. Raises RuntimeError if missing."""
    token = os.environ.get("TMDB_TOKEN")
    if not token:
        raise RuntimeError(
            "TMDB_TOKEN environment variable is not set. "
            "Set it in PowerShell:\n"
            '    $env:TMDB_TOKEN = Read-Host "Enter TMDB token" -MaskInput'
        )
    return token


def _headers() -> dict:
    """Build Authorization Bearer headers for TMDb v3 API."""
    return {
        "Authorization": f"Bearer {_get_token()}",
        "accept": "application/json",
    }


def sanitize_error(msg: str) -> str:
    """
    Remove any Bearer token values from error message strings so secrets
    are never leaked in exception tracebacks or logs.
    """
    return re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1[MASKED]", str(msg))


def _normalize_details(raw_json: dict, media_type: str) -> dict:
    """
    Normalize a TMDb details JSON payload into the Curatr contract dict.

    Adds 'fetched_at' ISO timestamp (UTC).
    Retains vote_count == 0 so Lochan's score_title() can flag 'unrated'.
    """
    # Title field differs by media type
    if media_type == "movie":
        title    = raw_json.get("title", "")
        raw_date = raw_json.get("release_date", "")
    else:
        title    = raw_json.get("name", "")
        raw_date = raw_json.get("first_air_date", "")

    # Safe year extraction (no string slicing on arbitrary length strings)
    release_year = None
    if raw_date and len(raw_date) >= 4 and raw_date[:4].isdigit():
        release_year = int(raw_date[:4])

    # Genre names — canonical names only available from details endpoint
    genre_names = [
        g["name"].strip()
        for g in raw_json.get("genres", [])
        if isinstance(g, dict) and "name" in g
    ]

    return {
        "media_type":        media_type,
        "tmdb_id":           int(raw_json["id"]),
        "title":             title,
        "release_year":      release_year,
        "rating":            round(float(raw_json.get("vote_average", 0.0)), 4),
        "vote_count":        int(raw_json.get("vote_count", 0)),
        "genres":            "|".join(sorted(set(genre_names))),
        "original_language": raw_json.get("original_language", ""),
        "fetched_at":        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _validate_media_type(media_type: str) -> None:
    if media_type not in VALID_MEDIA_TYPES:
        raise ValueError(
            f"Invalid media_type '{media_type}'. Must be one of: {VALID_MEDIA_TYPES}"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def search_titles(query: str, media_type: str, page: int = 1) -> dict:
    """
    Search TMDb for titles matching the query string.

    Args:
        query:       Search string. If empty/whitespace, returns empty result
                     without a network call.
        media_type:  'movie' or 'tv'.
        page:        Pagination page number (default 1).

    Returns:
        {
            "page":        int,
            "total_pages": int,
            "results":     list[dict]   # raw TMDb result items
        }

    Raises:
        ValueError:      If media_type is invalid.
        RuntimeError:    If TMDB_TOKEN is not set.
        requests.HTTPError: On non-2xx responses (token redacted from message).
    """
    _validate_media_type(media_type)

    # Short-circuit for empty/blank queries — no network call
    if not query or not query.strip():
        return {"page": 1, "total_pages": 0, "results": []}

    url    = f"{TMDB_BASE}/search/{media_type}"
    params = {
        "query":         query.strip(),
        "page":          page,
        "include_adult": "false",
    }

    try:
        resp = requests.get(url, headers=_headers(), params=params, timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise requests.HTTPError(sanitize_error(str(exc))) from exc
    except requests.RequestException as exc:
        raise requests.RequestException(
            f"Network error during search_titles: {sanitize_error(str(exc))}"
        ) from exc

    data = resp.json()
    return {
        "page":        data.get("page", page),
        "total_pages": data.get("total_pages", 0),
        "results":     data.get("results", []),
    }


def fetch_title(tmdb_id: int, media_type: str) -> dict:
    """
    Fetch full details for a specific TMDb title and normalize to contract schema.

    Uses the details endpoint (/{media_type}/{id}) which returns canonical genre
    names (not just numeric IDs).

    Args:
        tmdb_id:     Positive integer TMDb ID.
        media_type:  'movie' or 'tv'.

    Returns:
        Normalized dict matching Curatr contract columns plus 'fetched_at'.
        Keys: media_type, tmdb_id, title, release_year, rating, vote_count,
              genres, original_language, fetched_at.

    Raises:
        ValueError:      If media_type is invalid or tmdb_id <= 0.
        RuntimeError:    If TMDB_TOKEN is not set.
        requests.HTTPError: On non-2xx responses (token redacted).
    """
    _validate_media_type(media_type)

    if not isinstance(tmdb_id, int) or tmdb_id <= 0:
        raise ValueError(f"tmdb_id must be a positive integer, got: {tmdb_id!r}")

    url = f"{TMDB_BASE}/{media_type}/{tmdb_id}"

    try:
        resp = requests.get(url, headers=_headers(), timeout=TIMEOUT)
        resp.raise_for_status()
    except requests.HTTPError as exc:
        raise requests.HTTPError(sanitize_error(str(exc))) from exc
    except requests.RequestException as exc:
        raise requests.RequestException(
            f"Network error during fetch_title: {sanitize_error(str(exc))}"
        ) from exc

    return _normalize_details(resp.json(), media_type)
