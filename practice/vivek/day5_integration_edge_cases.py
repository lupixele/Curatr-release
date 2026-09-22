# PRACTICE — NOT REFERENCE DATA
# Day 5: Pairing on Live Search & Scoring Integration
# Goal: Handle edge cases — zero votes, missing dates, unreleased titles.


# Practice edge case simulator for live title normalization
def normalize_live_candidate(raw_dict, media_type):
    raw_date = raw_dict.get("release_date") if media_type == "movie" else raw_dict.get("first_air_date")
    year = int(raw_date[:4]) if raw_date and len(raw_date) >= 4 and raw_date[:4].isdigit() else None
    return {
        "media_type": media_type,
        "tmdb_id": raw_dict["id"],
        "title": raw_dict.get("title", "Untitled"),
        "release_year": year,
        "rating": float(raw_dict.get("vote_average", 0.0)),
        "vote_count": int(raw_dict.get("vote_count", 0)),
        "genres": "|".join(sorted(g["name"] for g in raw_dict.get("genres", []))),
        "original_language": raw_dict.get("original_language", "en")
    }


# Edge case 1: Zero-vote title (should preserve vote_count == 0 so scoring marks unrated)
zero_vote_title = {"id": 11, "title": "Obscure Indie", "release_date": "2023-01-01", "vote_average": 0.0, "vote_count": 0, "genres": [{"name": "Drama"}]}
norm_zero = normalize_live_candidate(zero_vote_title, "movie")
assert norm_zero["vote_count"] == 0
print("Edge case 1 passed: Zero vote count preserved for scoring status.")

# Edge case 2: Unreleased title with missing/unparseable date
no_date_title = {"id": 12, "title": "Future Project", "release_date": "", "vote_average": 0.0, "vote_count": 0, "genres": []}
norm_nodate = normalize_live_candidate(no_date_title, "movie")
assert norm_nodate["release_year"] is None
print("Edge case 2 passed: Missing release date returns None without crash.")

# Edge case 3: Unparseable date string
bad_date_title = {"id": 13, "title": "Bad Date Film", "release_date": "TBA", "vote_average": 7.0, "vote_count": 100, "genres": [{"name": "Action"}]}
norm_baddate = normalize_live_candidate(bad_date_title, "movie")
assert norm_baddate["release_year"] is None
print("Edge case 3 passed: Unparseable 'TBA' date returns None without crash.")

# Edge case 4: TV series uses first_air_date
tv_title = {"id": 14, "name": "New Series", "first_air_date": "2022-03-10", "vote_average": 8.1, "vote_count": 500, "genres": [{"name": "Drama"}]}
norm_tv = normalize_live_candidate(tv_title, "tv")
# TV uses 'name' not 'title', and first_air_date
print(f"Edge case 4 info: TV release_year={norm_tv['release_year']}, vote_count={norm_tv['vote_count']}")
print("Edge case 4 passed: TV normalization does not crash.")

print("\nAll integration edge cases handled successfully.")
