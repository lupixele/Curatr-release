"""tmdb_client.py - Live TMDb API client for Curatr.

Provides real-time search and title detail fetching from TMDb API, normalizing
external payloads into the Curatr contract schema specified in
Curatr-dev/docs/03-data-and-function-contracts.md.

Supports both:
- TMDb v4 API Read Access Token (Bearer JWT, starts with 'eyJ')
- TMDb v3 API Key (32-character hexadecimal string)
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
import re
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import requests

# Automatically load environment variables from .env if present
load_dotenv()

TMDB_BASE_URL = "https://api.themoviedb.org/3"
DEFAULT_TIMEOUT = 10  # seconds

# Standard TMDb genre ID mappings as fallback if detail payload is not yet fetched
TMDB_MOVIE_GENRES: Dict[int, str] = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}

TMDB_TV_GENRES: Dict[int, str] = {
    10759: "Action & Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    10762: "Kids",
    9648: "Mystery",
    10763: "News",
    10764: "Reality",
    10765: "Sci-Fi & Fantasy",
    10766: "Soap",
    10767: "Talk",
    10768: "War & Politics",
    37: "Western",
}


def _clean_credential(val: str) -> str:
    """Strip whitespace and surrounding quotes."""
    return str(val or "").strip().strip('"').strip("'").strip()


def _is_placeholder(val: str) -> bool:
    """Check if value is an unedited placeholder string."""
    v = val.lower()
    placeholders = ["your_", "example", "placeholder", "xxx", "insert", "here", "token_here", "key_here"]
    return any(p in v for p in placeholders) or len(val) < 10


def _get_auth_headers_and_params() -> tuple[Dict[str, str], Dict[str, str]]:
    """Retrieve auth credentials from environment and route to Bearer or Query Param appropriately."""
    headers = {
        "Accept": "application/json",
        "User-Agent": "Curatr-rei-nexus/1.0",
    }
    params: Dict[str, str] = {}

    token = _clean_credential(os.environ.get("TMDB_TOKEN", ""))
    api_key = _clean_credential(os.environ.get("TMDB_API_KEY", ""))

    # Ignore any placeholders
    valid_token = token if (token and not _is_placeholder(token)) else ""
    valid_key = api_key if (api_key and not _is_placeholder(api_key)) else ""

    raw_cred = valid_token or valid_key

    if not raw_cred:
        raise ValueError(
            "TMDb API key or token is missing or still set to a placeholder. "
            "Please add a valid TMDb v3 API Key (32 hex characters) or v4 Read Access Token (starts with eyJ)."
        )

    # If credential is a JWT token (TMDb v4 tokens start with 'eyJ')
    if raw_cred.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {raw_cred}"
    else:
        # v3 API Key (32 hex characters) or general API key
        params["api_key"] = raw_cred

    return headers, params


def validate_tmdb_connection() -> tuple[bool, str]:
    """Test connection and authentication against TMDb API."""
    try:
        headers, params = _get_auth_headers_and_params()
        endpoint = f"{TMDB_BASE_URL}/configuration"
        resp = requests.get(endpoint, headers=headers, params=params, timeout=DEFAULT_TIMEOUT)
        if resp.status_code == 200:
            return True, "Authenticated successfully with TMDb API."
        elif resp.status_code == 401:
            return False, "HTTP 401 Unauthorized: Invalid API key or token. Please verify your TMDb credentials."
        else:
            return False, f"TMDb responded with HTTP status {resp.status_code}."
    except Exception as e:
        return False, str(e)


def _clean_genres_list(raw_genres: Any, media_type: str = "movie") -> str:
    """Extract canonical genre names from TMDb genre objects or genre_ids."""
    if not raw_genres:
        return ""

    names: List[str] = []
    # If list of dicts: [{"id": 28, "name": "Action"}]
    if isinstance(raw_genres, list):
        for item in raw_genres:
            if isinstance(item, dict) and "name" in item and item["name"]:
                names.append(str(item["name"]).strip())
            elif isinstance(item, int):
                # Map genre id
                lookup = TMDB_MOVIE_GENRES if media_type == "movie" else TMDB_TV_GENRES
                if item in lookup:
                    names.append(lookup[item])
            elif isinstance(item, str) and item.strip():
                names.append(item.strip())
    elif isinstance(raw_genres, str):
        delim = "|" if "|" in raw_genres else ","
        names = [g.strip() for g in raw_genres.split(delim) if g.strip()]

    unique_sorted = sorted(list(set(names)))
    return "|".join(unique_sorted)


def normalize_title_record(
    raw: dict,
    media_type: str,
    include_fetched_at: bool = False,
) -> dict:
    """Normalize raw TMDb API item to match Curatr schema."""
    m_type = media_type.lower().strip()
    tmdb_id = int(raw.get("id", 0))

    # Title extraction
    if m_type == "movie":
        title_val = raw.get("title") or raw.get("original_title") or ""
        date_str = str(raw.get("release_date") or "").strip()
    else:
        title_val = raw.get("name") or raw.get("original_name") or ""
        date_str = str(raw.get("first_air_date") or "").strip()

    title_str = str(title_val).strip()

    # Year extraction
    release_year: Optional[int] = None
    if date_str:
        match = re.match(r"^(\d{4})", date_str)
        if match:
            try:
                release_year = int(match.group(1))
            except ValueError:
                release_year = None

    # Rating and votes
    try:
        rating = float(raw.get("vote_average", 0.0))
    except (ValueError, TypeError):
        rating = 0.0

    try:
        vote_count = int(raw.get("vote_count", 0))
    except (ValueError, TypeError):
        vote_count = 0

    # Genres (can be in 'genres' list of dicts or 'genre_ids' list of ints)
    raw_genres = raw.get("genres") or raw.get("genre_ids") or []
    genres_clean = _clean_genres_list(raw_genres, media_type=m_type)

    orig_lang = str(raw.get("original_language") or "").strip()

    record: Dict[str, Any] = {
        "media_type": m_type,
        "tmdb_id": tmdb_id,
        "title": title_str,
        "release_year": release_year,
        "rating": rating,
        "vote_count": vote_count,
        "genres": genres_clean,
        "original_language": orig_lang,
    }

    # Additional UI metadata
    if "overview" in raw:
        record["overview"] = str(raw.get("overview") or "").strip()
    if "poster_path" in raw:
        record["poster_path"] = raw.get("poster_path")

    if include_fetched_at:
        record["fetched_at"] = datetime.now(timezone.utc).isoformat()

    return record


def search_titles(query: str, media_type: str, page: int = 1) -> dict:
    """Search TMDb catalog for movies or TV shows matching the query.

    Blank queries return empty results locally without triggering an HTTP request.
    """
    cleaned_query = (query or "").strip()
    m_type = media_type.lower().strip()
    if m_type not in ["movie", "tv"]:
        raise ValueError(f"Invalid media_type '{media_type}'. Must be 'movie' or 'tv'.")

    # Contract requirement: blank queries return locally without a request
    if not cleaned_query:
        return {
            "page": 1,
            "total_pages": 0,
            "results": [],
        }

    headers, params = _get_auth_headers_and_params()
    params["query"] = cleaned_query
    params["page"] = str(max(1, int(page)))
    params["include_adult"] = "false"

    endpoint = f"{TMDB_BASE_URL}/search/{m_type}"

    try:
        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code == 401:
            raise RuntimeError(
                "TMDb Authentication Failed (HTTP 401 Unauthorized). "
                "Your API key or Bearer token is invalid or expired. "
                "Please verify it under themoviedb.org -> Settings -> API."
            ) from None
        raise RuntimeError(
            f"TMDb search request failed for {m_type} (HTTP status: {status_code})"
        ) from None
    except json.JSONDecodeError:
        raise RuntimeError("Invalid JSON returned by TMDb API") from None

    raw_results = data.get("results", [])
    normalized_results = [
        normalize_title_record(r, media_type=m_type, include_fetched_at=False)
        for r in raw_results
    ]

    return {
        "page": int(data.get("page", 1)),
        "total_pages": int(data.get("total_pages", 1)),
        "results": normalized_results,
    }


def fetch_title(tmdb_id: int, media_type: str) -> dict:
    """Fetch complete metadata for a specific TMDb ID and media type.

    Returns normalized title dictionary matching contract plus 'fetched_at'.
    """
    m_type = media_type.lower().strip()
    if m_type not in ["movie", "tv"]:
        raise ValueError(f"Invalid media_type '{media_type}'. Must be 'movie' or 'tv'.")

    try:
        t_id = int(tmdb_id)
        if t_id <= 0:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError(f"Invalid tmdb_id '{tmdb_id}'. Must be a positive integer.")

    headers, params = _get_auth_headers_and_params()
    endpoint = f"{TMDB_BASE_URL}/{m_type}/{t_id}"

    try:
        response = requests.get(
            endpoint,
            headers=headers,
            params=params,
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code == 401:
            raise RuntimeError(
                "TMDb Authentication Failed (HTTP 401 Unauthorized). "
                "Your API key or Bearer token is invalid or expired."
            ) from None
        raise RuntimeError(
            f"TMDb title lookup failed for {m_type} ID {t_id} (HTTP status: {status_code})"
        ) from None
    except json.JSONDecodeError:
        raise RuntimeError("Invalid JSON returned by TMDb API") from None

    return normalize_title_record(data, media_type=m_type, include_fetched_at=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TMDb API Client CLI test.")
    parser.add_argument("--query", help="Search query")
    parser.add_argument("--id", type=int, help="TMDb ID to fetch")
    parser.add_argument("--type", default="movie", choices=["movie", "tv"], help="Media type")
    parser.add_argument("--test-connection", action="store_true", help="Test current API credentials")
    args = parser.parse_args()

    if args.test_connection:
        ok, msg = validate_tmdb_connection()
        print(f"Connection status: {'SUCCESS' if ok else 'FAILED'}")
        print(f"Details: {msg}")
    elif args.query:
        print(f"Searching {args.type} for '{args.query}'...")
        res = search_titles(args.query, args.type)
        print(f"Page {res['page']} of {res['total_pages']}, found {len(res['results'])} items.")
        for item in res["results"][:3]:
            print(f" - [{item['tmdb_id']}] {item['title']} ({item['release_year']}) rating={item['rating']} votes={item['vote_count']} genres={item['genres']}")
    elif args.id:
        print(f"Fetching {args.type} details for ID {args.id}...")
        item = fetch_title(args.id, args.type)
        print(f"Title: {item['title']} ({item['release_year']})")
        print(f"Rating: {item['rating']}, Votes: {item['vote_count']}")
        print(f"Genres: {item['genres']}")
        print(f"Fetched at: {item['fetched_at']}")
    else:
        print("Provide --test-connection, --query <term>, or --id <tmdb_id>.")
