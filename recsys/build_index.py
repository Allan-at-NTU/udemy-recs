
import numpy as np
import pandas as pd
import faiss
from sentence_transformers import SentenceTransformer

INDEX_IN  = "data/index.parquet"
EMB_OUT   = "data/embeddings.npy"
FAISS_OUT = "data/courses.faiss"

def main():
    idx = pd.read_parquet(INDEX_IN)
    texts = idx["text"].fillna("").tolist()

    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = model.encode(texts, batch_size=64, normalize_embeddings=True)
    emb = emb.astype("float32")

    # HNSW index for cosine (IP on normalized vectors)
    dim = emb.shape[1]
    index = faiss.IndexHNSWFlat(dim, 32)
    index.hnsw.efConstruction = 200
    index.add(emb)

    # Save artifacts
    np.save(EMB_OUT, emb)
    faiss.write_index(index, FAISS_OUT)
    print(f"Wrote {EMB_OUT} and {FAISS_OUT}")

if __name__ == "__main__":
    main()
