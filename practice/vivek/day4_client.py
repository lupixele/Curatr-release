# PRACTICE — NOT REFERENCE DATA
# Day 4: Production API Client and API Handoff Gate
# Goal: Practice search_titles contract, empty query short-circuit, error sanitization.

import re


def sanitize_error_message(msg: str) -> str:
    """Removes any Bearer tokens or sensitive keys from error messages."""
    return re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]+", r"\1[MASKED]", msg)


# Contract compliance practice for search_titles
def practice_search_titles(query: str, media_type: str, page: int = 1) -> dict:
    if not query or not query.strip():
        return {"page": 1, "total_pages": 0, "results": []}

    # Fictional contract response
    return {
        "page": page,
        "total_pages": 1,
        "results": [
            {
                "media_type": media_type,
                "tmdb_id": 999,
                "title": f"{query.strip().title()} (Mock Match)",
                "release_year": 2021,
                "rating": 7.9,
                "vote_count": 1250,
                "genres": "Drama|Mystery",
                "original_language": "en"
            }
        ]
    }


# Test blank query returns empty structure without network call
blank_res = practice_search_titles("", "movie")
assert blank_res["results"] == [] and blank_res["total_pages"] == 0
print("Blank query contract verified:", blank_res)

# Test populated query response shape
res = practice_search_titles("Arrival", "movie")
print("Search result:", res["results"][0]["title"])

# Test error message masking
leaky_msg = "Error connecting with Authorization: Bearer secret_token_xyz123"
masked = sanitize_error_message(leaky_msg)
assert "secret_token_xyz123" not in masked
print("Sanitized error test passed:", masked)
