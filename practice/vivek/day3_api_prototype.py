# PRACTICE — NOT REFERENCE DATA
# Day 3: Verify Handoff and API Prototyping
# Goal: Simulate the two-step TMDb API flow (search → details → normalize).

from datetime import datetime, timezone


# Fictional simulation of two-step TMDb API query and normalization
mock_search_payload = {
    "page": 1,
    "total_pages": 1,
    "results": [
        {"id": 550, "title": "Fight Club", "release_date": "1999-10-15", "genre_ids": [18, 53]}
    ]
}

mock_details_payload = {
    "id": 550,
    "title": "Fight Club",
    "release_date": "1999-10-15",
    "vote_average": 8.433,
    "vote_count": 27000,
    "genres": [{"id": 18, "name": "Drama"}, {"id": 53, "name": "Thriller"}],
    "original_language": "en"
}


def normalize_details(raw_json, media_type):
    raw_date = raw_json.get("release_date") if media_type == "movie" else raw_json.get("first_air_date")
    year = int(raw_date[:4]) if raw_date and len(raw_date) >= 4 and raw_date[:4].isdigit() else None
    genre_names = [g["name"].strip() for g in raw_json.get("genres", []) if "name" in g]
    return {
        "media_type": media_type,
        "tmdb_id": int(raw_json["id"]),
        "title": raw_json.get("title") if media_type == "movie" else raw_json.get("name", ""),
        "release_year": year,
        "rating": round(float(raw_json.get("vote_average", 0.0)), 4),
        "vote_count": int(raw_json.get("vote_count", 0)),
        "genres": "|".join(sorted(set(genre_names))),
        "original_language": raw_json.get("original_language", ""),
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    }


# Step 1: Extract candidate IDs from search
candidates = [(r["id"], r.get("title")) for r in mock_search_payload["results"]]
print("Step 1 candidates found:", candidates)

# Step 2: Normalize fetched details into contract dictionary
normalized = normalize_details(mock_details_payload, "movie")
print("Step 2 normalized record:")
for k, v in normalized.items():
    print(f"  {k}: {v}")
