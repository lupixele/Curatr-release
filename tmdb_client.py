import os
import requests
from datetime import datetime, timezone

BASE_URL = "https://api.themoviedb.org/3"

def get_token():
    """Reads TMDb token from environment. Never hardcode it!"""
    token = os.environ.get("TMDB_TOKEN")
    if not token:
        raise ValueError("TMDB_TOKEN environment variable is not set.")
    return token

def normalize_result(raw, media_type):
    """
    Converts a raw TMDb API result into the same dictionary
    format as clean_titles.csv so score_title() can use it directly.
    """
    # Title field differs between movies and TV
    if media_type == "movie":
        title = raw.get("title", "")
        date_str = raw.get("release_date", "")
    else:
        title = raw.get("name", "")
        date_str = raw.get("first_air_date", "")

    # Extract year from date string like "2019-07-26"
    try:
        release_year = int(date_str[:4]) if date_str else None
    except (ValueError, TypeError):
        release_year = None

    # API returns genre_ids in search results (not genre names)
    # We leave genres as empty string here; fetch_title gets the real names
    genre_ids = raw.get("genre_ids", [])

    return {
        "media_type": media_type,
        "tmdb_id": raw.get("id"),
        "title": title,
        "release_year": release_year,
        "rating": raw.get("vote_average"),
        "vote_count": raw.get("vote_count"),
        "genres": "",  # Populated properly in fetch_title()
        "original_language": raw.get("original_language", ""),
        "poster_path": raw.get("poster_path"),
    }

def normalize_detail(raw, media_type):
    """
    Converts a TMDb detail response into our clean dictionary format.
    fetch_title() returns full genre names (not just IDs), so we parse them here.
    """
    if media_type == "movie":
        title = raw.get("title", "")
        date_str = raw.get("release_date", "")
    else:
        title = raw.get("name", "")
        date_str = raw.get("first_air_date", "")

    try:
        release_year = int(date_str[:4]) if date_str else None
    except (ValueError, TypeError):
        release_year = None

    # Detail endpoint gives full genre objects like: [{"id": 28, "name": "Action"}]
    raw_genres = raw.get("genres", [])
    genre_names = sorted(set(
        g["name"].strip() for g in raw_genres if g.get("name", "").strip()
    ))
    genres_str = "|".join(genre_names)

    return {
        "media_type": media_type,
        "tmdb_id": raw.get("id"),
        "title": title,
        "release_year": release_year,
        "rating": raw.get("vote_average"),
        "vote_count": raw.get("vote_count"),
        "genres": genres_str,
        "original_language": raw.get("original_language", ""),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "poster_path": raw.get("poster_path"),
    }

def search_titles(query, media_type, page=1):
    """
    Searches TMDb for titles matching the query.
    Returns: {"page": int, "total_pages": int, "results": [list of dicts]}
    """
    # Blank queries return empty result without making a request
    if not query or not query.strip():
        return {"page": 1, "total_pages": 0, "results": []}

    token = get_token()
    url = f"{BASE_URL}/search/{media_type}"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "query": query.strip(),
        "language": "en-US",
        "page": page,
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        raise Exception("TMDb search request failed. Check your connection or token.")

    data = response.json()
    results = [normalize_result(r, media_type) for r in data.get("results", [])]

    return {
        "page": data.get("page", 1),
        "total_pages": data.get("total_pages", 0),
        "results": results,
    }

def fetch_title(tmdb_id, media_type):
    """
    Fetches full details for one title from TMDb.
    Returns a normalized dictionary ready for score_title().
    """
    token = get_token()
    url = f"{BASE_URL}/{media_type}/{tmdb_id}"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"language": "en-US"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        raise Exception(f"TMDb fetch failed for {media_type} ID {tmdb_id}.")

    return normalize_detail(response.json(), media_type)

if __name__ == "__main__":
    print("Testing TMDb client...")
    try:
        # Test search
        results = search_titles("Inception", "movie")
        print(f"Search returned {len(results['results'])} results")
        print(f"First result: {results['results'][0]['title']} ({results['results'][0]['release_year']})")

        # Test fetch details
        first_id = results["results"][0]["tmdb_id"]
        detail = fetch_title(first_id, "movie")
        print(f"\nFull details for: {detail['title']}")
        print(f"  Rating:    {detail['rating']}")
        print(f"  Genres:    {detail['genres']}")
        print(f"  Votes:     {detail['vote_count']}")
        print(f"  Fetched:   {detail['fetched_at']}")
    except Exception as e:
        print(f"Error: {e}")