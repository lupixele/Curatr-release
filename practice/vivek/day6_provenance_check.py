# PRACTICE — NOT REFERENCE DATA
# Day 6: Provenance Documentation and Cross-Machine Reproduction
# Goal: Verify SHA-256 checksumming works deterministically for DATA_SOURCES.md.

import hashlib

# Fictional clean dataset to verify reproducible SHA-256 checksumming
sample_csv_text = "media_type,tmdb_id,title,release_year,rating,vote_count,genres,original_language\nmovie,101,Inception,2010,8.4,35000,Action|Sci-Fi,en\n"

# Compute SHA-256 checksum of file content
hasher = hashlib.sha256()
hasher.update(sample_csv_text.encode("utf-8"))
checksum = hasher.hexdigest()

print(f"Generated SHA-256 checksum: {checksum}")
assert len(checksum) == 64
print("Checksum generation verified for DATA_SOURCES.md documentation.")

# Verify determinism: running twice on same content gives same hash
hasher2 = hashlib.sha256()
hasher2.update(sample_csv_text.encode("utf-8"))
checksum2 = hasher2.hexdigest()
assert checksum == checksum2
print("Determinism verified: same input always produces same SHA-256.")
