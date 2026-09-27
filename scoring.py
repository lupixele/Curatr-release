"""scoring.py - Baselines and mathematical scoring functions for Curatr.

Implements Bayesian weighted scoring (global_score) and genre-adjusted scoring
(genre_score) adhering strictly to Curatr-dev/docs/03-data-and-function-contracts.md.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
import os
import time
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd


def global_score(rating: float, vote_count: int, C: float, m: float) -> float:
    """Bayesian weighted score pulling raw rating toward global prior C.

    Formula: S_global = (v * R + m * C) / (v + m)
    """
    v = float(vote_count)
    return (v * float(rating) + float(m) * float(C)) / (v + float(m))


def genre_score(rating: float, vote_count: int, C: float, m: float, G: float) -> float:
    """Genre-adjusted score evaluating performance relative to genre baseline G.

    Formula: S_genre = C + (v / (v + m)) * (R - G)
    """
    v = float(vote_count)
    return float(C) + (v / (v + float(m))) * (float(rating) - float(G))


def build_baselines(clean_df: pd.DataFrame) -> dict:
    """Compute global priors (C, m) and genre baselines from clean dataframe.

    Baselines are computed strictly separately for each media type ('movie' and 'tv').
    Global mean C and 25th percentile vote count m are calculated BEFORE expanding genres.
    Genre baselines use unweighted title means. If title count for a genre is < 30,
    it falls back to global C with fallback=True.
    """
    baselines: Dict[str, Any] = {
        "schema_version": 1,
        "reference_years": [2014, 2023],
        "source_note": "asaniczka Full TMDb 2014-2023 reference",
        "prepared_at": datetime.now(timezone.utc).isoformat(),
    }

    for media_type in ["movie", "tv"]:
        sub = clean_df[clean_df["media_type"] == media_type]
        if sub.empty:
            raise ValueError(f"No eligible records found for media_type '{media_type}'")

        # C: unweighted mean of raw ratings
        c_val = float(sub["rating"].mean())
        # m: 25th-percentile vote count (pandas default linear interpolation)
        m_val = float(sub["vote_count"].quantile(0.25))
        title_count = int(len(sub))

        # Genre baselines
        # Explode genres on pipe delimiter
        exploded = (
            sub[["rating", "genres"]]
            .assign(genre=sub["genres"].astype(str).str.split("|"))
            .explode("genre")
        )
        exploded["genre"] = exploded["genre"].astype(str).str.strip()
        exploded = exploded[exploded["genre"] != ""]

        genre_stats = (
            exploded.groupby("genre")["rating"]
            .agg(raw_mean="mean", count="count")
            .reset_index()
        )

        genres_dict: Dict[str, Dict[str, Any]] = {}
        for _, row in genre_stats.iterrows():
            g_name = str(row["genre"])
            g_raw_mean = float(row["raw_mean"])
            g_count = int(row["count"])
            g_fallback = bool(g_count < 30)
            g_baseline = float(g_raw_mean if not g_fallback else c_val)

            genres_dict[g_name] = {
                "raw_mean": g_raw_mean,
                "count": g_count,
                "baseline": g_baseline,
                "fallback": g_fallback,
            }

        baselines[media_type] = {
            "C": c_val,
            "m": m_val,
            "title_count": title_count,
            "genres": genres_dict,
        }

    return baselines


def score_title(title: dict, baselines: dict) -> dict:
    """Validate inputs and calculate both global and genre scores for a single title dict.

    Returns a new dictionary retaining original fields plus:
    - global_score: float | None
    - genre_score: float | None
    - genre_baseline: float | None (G)
    - score_status: 'ok' | 'unrated' | 'unavailable'
    - genre_fallback: bool
    """
    res = dict(title)
    media_type = str(res.get("media_type", "")).strip().lower()

    def make_result(
        status: str,
        g_score: Optional[float] = None,
        j_score: Optional[float] = None,
        g_base: Optional[float] = None,
        fallback: bool = False,
    ) -> dict:
        res["global_score"] = g_score
        res["genre_score"] = j_score
        res["genre_baseline"] = g_base
        res["score_status"] = status
        res["genre_fallback"] = fallback
        return res

    # Validate media type
    if media_type not in baselines or media_type not in ["movie", "tv"]:
        return make_result("unavailable")

    type_baselines = baselines[media_type]
    c_val = type_baselines.get("C")
    m_val = type_baselines.get("m")
    if c_val is None or m_val is None or m_val <= 0:
        return make_result("unavailable")

    # Validate rating
    raw_rating = res.get("rating")
    if raw_rating is None:
        return make_result("unavailable")
    try:
        r_float = float(raw_rating)
        if math.isnan(r_float) or math.isinf(r_float) or r_float < 0.0 or r_float > 10.0:
            return make_result("unavailable")
    except (ValueError, TypeError):
        return make_result("unavailable")

    # Validate vote_count
    raw_votes = res.get("vote_count")
    if raw_votes is None:
        return make_result("unavailable")
    try:
        v_float = float(raw_votes)
        if math.isnan(v_float) or math.isinf(v_float):
            return make_result("unavailable")
        if not v_float.is_integer():
            return make_result("unavailable")
        v_int = int(v_float)
    except (ValueError, TypeError, OverflowError):
        return make_result("unavailable")

    if v_int < 0:
        return make_result("unavailable")
    if v_int == 0:
        return make_result("unrated")

    # Parse genres
    raw_genres = res.get("genres", "")
    genre_list: List[str] = []
    if isinstance(raw_genres, list):
        genre_list = [str(g).strip() for g in raw_genres if str(g).strip()]
    elif isinstance(raw_genres, str):
        delim = "|" if "|" in raw_genres else ","
        genre_list = [g.strip() for g in raw_genres.split(delim) if g.strip()]
    genre_list = sorted(list(set(genre_list)))

    # Compute G (equal-weight average of distinct effective genre baselines)
    known_genres = type_baselines.get("genres", {})
    if not genre_list:
        g_val = float(c_val)
        fallback_used = True
    else:
        baselines_list: List[float] = []
        fallback_used = False
        for g in genre_list:
            if g in known_genres:
                g_info = known_genres[g]
                baselines_list.append(float(g_info["baseline"]))
                if g_info.get("fallback", False):
                    fallback_used = True
            else:
                baselines_list.append(float(c_val))
                fallback_used = True
        g_val = float(sum(baselines_list) / len(baselines_list))

    # Compute formulas
    s_glob = global_score(r_float, v_int, float(c_val), float(m_val))
    s_gen = genre_score(r_float, v_int, float(c_val), float(m_val), g_val)

    return make_result(
        status="ok",
        g_score=float(s_glob),
        j_score=float(s_gen),
        g_base=float(g_val),
        fallback=bool(fallback_used),
    )


def score_dataframe(clean_df: pd.DataFrame, baselines: dict) -> pd.DataFrame:
    """Score all rows in clean dataframe using precomputed baselines.

    Calculates global_score, genre_score, genre_baseline, score_status,
    and genre_fallback for every record. Highly optimized for speed.
    """
    df = clean_df.copy()

    # Pre-build fast lookup mappings for movie and tv
    genre_baseline_lookup: Dict[str, Dict[str, float]] = {
        "movie": {},
        "tv": {},
    }
    genre_fallback_lookup: Dict[str, Dict[str, bool]] = {
        "movie": {},
        "tv": {},
    }
    c_map = {"movie": baselines["movie"]["C"], "tv": baselines["tv"]["C"]}
    m_map = {"movie": baselines["movie"]["m"], "tv": baselines["tv"]["m"]}

    for m_type in ["movie", "tv"]:
        for g_name, g_info in baselines[m_type]["genres"].items():
            genre_baseline_lookup[m_type][g_name] = float(g_info["baseline"])
            genre_fallback_lookup[m_type][g_name] = bool(g_info.get("fallback", False))

    # Cache genre string to (G, fallback) per media_type
    genre_string_cache: Dict[tuple, tuple[float, bool]] = {}

    def get_g_and_fallback(media_type: str, genres_str: str) -> tuple[float, bool]:
        key = (media_type, genres_str)
        if key in genre_string_cache:
            return genre_string_cache[key]

        c = c_map[media_type]
        if not isinstance(genres_str, str) or not genres_str.strip():
            res = (c, True)
            genre_string_cache[key] = res
            return res

        tags = [t.strip() for t in genres_str.split("|") if t.strip()]
        if not tags:
            res = (c, True)
            genre_string_cache[key] = res
            return res

        lookup_b = genre_baseline_lookup[media_type]
        lookup_f = genre_fallback_lookup[media_type]

        vals: List[float] = []
        any_fallback = False
        for tag in tags:
            if tag in lookup_b:
                vals.append(lookup_b[tag])
                if lookup_f[tag]:
                    any_fallback = True
            else:
                vals.append(c)
                any_fallback = True

        g = sum(vals) / len(vals)
        res = (g, any_fallback)
        genre_string_cache[key] = res
        return res

    # Compute G and fallback for each unique (media_type, genres) combination
    unique_pairs = df[["media_type", "genres"]].drop_duplicates()
    g_records = []
    for _, row in unique_pairs.iterrows():
        m_t = str(row["media_type"])
        g_s = str(row["genres"])
        g_val, f_val = get_g_and_fallback(m_t, g_s)
        g_records.append({
            "media_type": m_t,
            "genres": g_s,
            "genre_baseline": g_val,
            "genre_fallback": f_val,
        })
    g_df = pd.DataFrame(g_records)
    df = df.merge(g_df, on=["media_type", "genres"], how="left")

    # Vectorized calculation of scores
    c_series = df["media_type"].map(c_map).astype(float)
    m_series = df["media_type"].map(m_map).astype(float)
    v_series = df["vote_count"].astype(float)
    r_series = df["rating"].astype(float)
    g_series = df["genre_baseline"].astype(float)

    weight = v_series / (v_series + m_series)
    df["global_score"] = (v_series * r_series + m_series * c_series) / (v_series + m_series)
    df["genre_score"] = c_series + weight * (r_series - g_series)
    df["score_status"] = "ok"

    # Reorder columns per contract
    contract_cols = [
        "media_type",
        "tmdb_id",
        "title",
        "release_year",
        "rating",
        "vote_count",
        "genres",
        "original_language",
        "global_score",
        "genre_score",
        "genre_baseline",
        "score_status",
        "genre_fallback",
    ]
    return df[contract_cols]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute baselines and score dataset for Curatr.")
    parser.add_argument("--clean-csv", default="data/clean_titles.csv", help="Path to clean CSV")
    parser.add_argument("--baselines-json", default="data/baselines.json", help="Path to output baselines JSON")
    parser.add_argument("--scored-csv", default="data/scored_titles.csv", help="Path to output scored CSV")
    args = parser.parse_args()

    t0 = time.time()
    print(f"Loading cleaned dataset from {args.clean_csv}...")
    df_clean = pd.read_csv(args.clean_csv)
    print(f"Loaded {len(df_clean):,} clean titles.")

    print("Building baselines for movies and TV...")
    baselines = build_baselines(df_clean)

    os.makedirs(os.path.dirname(args.baselines_json), exist_ok=True)
    with open(args.baselines_json, "w", encoding="utf-8") as f:
        json.dump(baselines, f, indent=2)
    print(f"Saved baselines to {args.baselines_json}.")
    print(f"  Movie C: {baselines['movie']['C']:.3f}, m: {baselines['movie']['m']:.1f}, genres: {len(baselines['movie']['genres'])}")
    print(f"  TV C: {baselines['tv']['C']:.3f}, m: {baselines['tv']['m']:.1f}, genres: {len(baselines['tv']['genres'])}")

    print("Scoring all titles...")
    df_scored = score_dataframe(df_clean, baselines)

    os.makedirs(os.path.dirname(args.scored_csv), exist_ok=True)
    df_scored.to_csv(args.scored_csv, index=False, encoding="utf-8")
    elapsed = round(time.time() - t0, 2)
    print(f"Scored {len(df_scored):,} titles in {elapsed}s and saved to {args.scored_csv}.")
