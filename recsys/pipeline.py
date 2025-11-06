
import os, re
import numpy as np
import pandas as pd
import faiss
from groq import Groq
from sentence_transformers import SentenceTransformer

_ASSETS = {"model": None, "index": None, "course_ids": None,
           "popularity": None, "recency": None, "details_df": None, "index_df": None}

def get_groq_client():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError("GROQ_API_KEY not set")
    return Groq(api_key=key)

def load_assets(data_dir="data"):
    if _ASSETS["model"] is None:
        _ASSETS["model"] = SentenceTransformer("all-MiniLM-L6-v2")
    if _ASSETS["details_df"] is None:
        _ASSETS["details_df"] = pd.read_parquet(f"{data_dir}/details.parquet")
        _ASSETS["index_df"]   = pd.read_parquet(f"{data_dir}/index.parquet")
        _ASSETS["index"]      = faiss.read_index(f"{data_dir}/courses.faiss")
        _ASSETS["course_ids"] = _ASSETS["index_df"]["course_id"].to_numpy()
        _ASSETS["popularity"] = _ASSETS["index_df"]["popularity_score"].to_numpy()
        _ASSETS["recency"]    = _ASSETS["index_df"]["recency_score"].to_numpy()
    return _ASSETS

def _mmr_selection(cand_df, k=3, lambda_=0.7):
    selected, remaining = [], cand_df.index.tolist()
    if not remaining:
        return cand_df.iloc[:0]
    first = cand_df["score"].idxmax()
    selected.append(first); remaining.remove(first)
    while len(selected) < min(k, len(cand_df)):
        best_id, best_val = None, -1e9
        for i in remaining:
            rel = cand_df.at[i, "score"]
            div = max(cand_df.loc[selected, "cosine_sim"].values) if selected else 0.0
            mmr = lambda_ * rel - (1 - lambda_) * div
            if mmr > best_val:
                best_val, best_id = mmr, i
        selected.append(best_id); remaining.remove(best_id)
    return cand_df.loc[selected].sort_values("score", ascending=False)

def llm_reason(row, query, model_name="llama-3.3-70b-versatile"):
    client = get_groq_client()
    prompt = f"""
You recommend courses. Be concise.
User request: "{query}"
Use ONLY these fields:
Title: {row['course_title']}
Subject: {row['subject']}
Level: {row['level']}
Duration_hours: {row['content_duration']}
Price: {row['price']}
Num_reviews: {int(row['num_reviews'])}
Rating: {row['combined_rating']}
Write ONE friendly sentence on why this fits. Mention level match and one numeric fact. No inventions.
"""
    r = client.chat.completions.create(
        model=model_name,
        messages=[{"role":"user","content":prompt}],
        temperature=0.6,
        max_tokens=60,
    )
    return r.choices[0].message.content.strip()

def top3_with_reasons(query: str, k_candidates: int = 200):
    a = load_assets()
    model, index = a["model"], a["index"]
    course_ids, popularity, recency = a["course_ids"], a["popularity"], a["recency"]
    details_df = a["details_df"]

    q = model.encode([query], normalize_embeddings=True).astype(np.float32)
    D, I = index.search(q, k_candidates)
    sims, ids = D[0], course_ids[I[0]]

    cand = pd.DataFrame({
        "course_id": ids,
        "cosine_sim": sims,
        "popularity_score": popularity[I[0]],
        "recency_score": recency[I[0]],
    })
    cand["score"] = 0.85*cand["cosine_sim"] + 0.14*cand["popularity_score"] + 0.01*cand["recency_score"]

    picked = _mmr_selection(cand, k=3, lambda_=0.7)
    out = picked.merge(details_df, on="course_id", how="left")
    out["why"] = out.apply(lambda r: llm_reason(r, query), axis=1)

    cols = ["course_title","subject","level","price","content_duration",
            "num_reviews","combined_rating","url","why","score"]
    return out[cols].reset_index(drop=True)
