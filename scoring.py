import pandas as pd
import os
import json

def compute_media_baselines(sub_df):
    c = sub_df["rating"].mean()
    m = sub_df["vote_count"].quantile(0.25)

    exploded = sub_df.assign(
        genre = sub_df["genres"].str.split("|")
    ).explode("genre")

    genre_stats = (
        exploded.groupby("genre").agg(
            raw_mean = ("rating","mean"),
            raw_count = ("rating","count")
        ).reset_index()
    )

    genres_dict = {}

    for _, row in genre_stats.iterrows():
        genre_name = str(row["genre"]).strip()
        if not genre_name:
            continue
        count = int(row["raw_count"])
        raw_mean = float(row["raw_mean"])

        if count < 30:
            baseline = c
            fallback = True
        else:
            baseline = raw_mean
            fallback = False

        genres_dict[genre_name] = {
            "raw_mean": round(raw_mean,4),
            "count": count,
            "baseline": round(baseline,4),
            "fallback": fallback,
        }

    return {
            "C": round(c,4),
            "m": round(m,4),
            "title_count": int(len(sub_df)),
            "genres": genres_dict,
        }


def build_baselines(clean_df):
    mv_df = clean_df[clean_df["media_type"] == "movie"]
    tv_df = clean_df[clean_df["media_type"] == "tv"]

    return {
        "schema_version": 1,
        "reference_years": [2014, 2023],
        "source_note" : "asaniczka full TMDb movies/tv datasets",
        "movie": compute_media_baselines(mv_df),
        "tv": compute_media_baselines(tv_df),
    }



def global_score(rating, vote_count, C, m):
    """Bayesian shrinkage toward the global baseline C."""
    return (vote_count * rating + m * C) / (vote_count + m)
def genre_score(rating, vote_count, C, m, G):
    """Genre-adjusted score centered around C."""
    return C + (vote_count / (vote_count + m)) * (rating - G)


def score_title(title_dict, baselines):
    """Score one title using baselines."""
    media_type = title_dict["media_type"]
    movie_type = title_dict["media_type"]
    rating = title_dict["rating"]
    vote_count = title_dict["vote_count"]

    if media_type not in ["movie", "tv"]:
        return {
            **title_dict,
            "global_score": None,
            "genre_score": None,
            "genre_baseline": None,
            "score_status": "unavailable",
            "genre_fallback": False
        }
    base_type = baselines[media_type]
    C = base_type["C"]
    m = base_type["m"]

    if vote_count is None or vote_count == 0:
        return {
            **title_dict,
            "global_score": None,
            "genre_score": None,
            "genre_baseline": None,
            "score_status": "unrated",
            "genre_fallback": False
        }
    if rating is None:
        return {
            **title_dict,
            "global_score": None,
            "genre_score": None,
            "genre_baseline": None,
            "score_status": "unavailable",
            "genre_fallback": False
        }
    
    genre_list = [g.strip() for g in title_dict["genres"].split("|") if g.strip()]

    if not genre_list:
        G = C
        genre_fallback = True
    else:
        genre_baselines = []
        genre_fallback = False
        for g in genre_list:
             if g in base_type["genres"]:
                g_meta = base_type["genres"][g]
                genre_baselines.append(g_meta["baseline"])
                if g_meta.get("fallback",True):
                    genre_fallback = True
             else:
                genre_baselines.append(C)
                genre_fallback = True
        G = sum(genre_baselines)/len(genre_baselines)
    
    s_glob = global_score(rating,vote_count,C,m)
    s_gen = genre_score(rating,vote_count,C,m,G)

    return {
        **title_dict,
        "genre_score" : round(s_gen,4),
        "global_score" : round(s_glob,4),
        "genre_baseline" : round(G,4),
        "score_status": "ok",
    "genre_fallback": genre_fallback
    }


def score_dataframe(clean_df,baselines):
    records = clean_df.to_dict("records")
    scored_records = [score_title(row,baselines) for row in records]
    return pd.DataFrame(scored_records)
        

    


if __name__ == "__main__":
    with open(r"data\baselines.json") as f:
        baselines = json.load(f)
    clean_df = pd.read_csv(r"data\clean_titles.csv")
    print("Scoring titles...")
    scored_df = score_dataframe(clean_df, baselines)
    scored_df.to_csv(r"data\scored_titles.csv", index=False)
    print("Saved data/scored_titles.csv!")
    print(scored_df["score_status"].value_counts())

    #df = pd.read_csv(r"P:\Silas\Projects\rei-nexus\curatr\Curatr-release\data\clean_titles.csv")
    #print("Building baselines...")
    #baselines = build_baselines(df)

    #out_path = r"P:\Silas\Projects\rei-nexus\curatr\Curatr-release\data\baselines.json"
    #with open(out_path, "w", encoding="utf-8") as f:
        #json.dump(baselines, f, indent=2)

    #print(f"Saved baselines to {out_path}")
    #print(f"Movie C: {baselines['movie']['C']}, m: {baselines['movie']['m']}")
    #print(f"TV C:    {baselines['tv']['C']}, m: {baselines['tv']['m']}")
    #print(f"Movie genres found: {len(baselines['movie']['genres'])}")
    #print(f"TV genres found:    {len(baselines['tv']['genres'])}")