
import pandas as pd
import numpy as np

# Input CSV
RAW = "data/courses_raw.csv"

# Outputs
DETAILS = "data/details.parquet"
INDEX = "data/index.parquet"

def main():
    df = pd.read_csv(RAW)

    # Basic cleaning / typing
    df["level"] = df["level"].fillna("All").str.replace(" Level", "", regex=False)
    for col in ["num_reviews","num_subscribers","price","content_duration","combined_rating"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df["published_timestamp"] = pd.to_datetime(df["published_timestamp"], errors="coerce")

    # Dedup by course_id, keep latest by timestamp if duplicates
    if "course_id" in df.columns:
        df = df.sort_values("published_timestamp").drop_duplicates("course_id", keep="last")

    # Recency score (0..1)
    ts_min = df["published_timestamp"].min()
    ts_max = df["published_timestamp"].max()
    denom = (ts_max - ts_min).days if pd.notnull(ts_max) and pd.notnull(ts_min) else 1
    df["recency_score"] = 0.0
    mask = df["published_timestamp"].notna()
    if mask.any():
        df.loc[mask, "recency_score"] = (
            (df.loc[mask, "published_timestamp"] - ts_min).dt.days / max(denom, 1)
        ).clip(0,1)

    # Popularity score (min-max blend of reviews, subs, rating)
    def minmax(x):
        x = x.to_numpy(dtype=float)
        lo, hi = np.nanmin(x), np.nanmax(x)
        if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
            return np.zeros_like(x, dtype=float)
        return (x - lo) / (hi - lo)

    r = minmax(df["num_reviews"].fillna(0))
    s = minmax(df["num_subscribers"].fillna(0))
    g = minmax(df["combined_rating"].fillna(0))
    df["popularity_score"] = 0.5*r + 0.3*s + 0.2*g

    # Text for embeddings
    df["text"] = (
        df["course_title"].fillna("") + " | " +
        df["subject"].fillna("") + " | " +
        df["level"].fillna("")
    )

    # Save details + index views
    details_cols = [
        "course_id","course_title","url",
        "subject","level","price","content_duration",
        "num_reviews","num_subscribers","combined_rating",
        "published_timestamp"
    ]
    index_cols = ["course_id","text","popularity_score","recency_score"]

    df[details_cols].to_parquet(DETAILS, index=False)
    df[index_cols].to_parquet(INDEX, index=False)
    print(f"Wrote {DETAILS} and {INDEX}")

if __name__ == "__main__":
    main()
