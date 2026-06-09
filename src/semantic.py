"""
semantic.py — the dense-retrieval ("understanding") component.

At ranking time we do NOT call any model over the network. We load embeddings that
were pre-computed offline by build_index.py (sentence-transformers/all-MiniLM-L6-v2,
384-d, L2-normalised, stored as float16 keyed by candidate_id) and the pre-computed
JD query vectors. Candidate↔JD similarity is then a single numpy matmul over the
whole pool — milliseconds.

If the embedding artifacts are missing (e.g. a fresh checkout that hasn't run the
precompute step), we transparently fall back to a TF-IDF char/word surrogate so the
pipeline always produces a ranking. The transformer path is the intended one and is
what the README/sandbox use; the fallback exists only for robustness.
"""
from __future__ import annotations
import os
import numpy as np

from . import jd_spec

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


# ---------------------------------------------------------------------------
# Loading pre-computed artifacts
# ---------------------------------------------------------------------------
def load_artifacts(artifacts_dir: str):
    emb_path = os.path.join(artifacts_dir, "embeddings.f16.npy")
    ids_path = os.path.join(artifacts_dir, "candidate_ids.npy")
    jd_path = os.path.join(artifacts_dir, "jd_vectors.npy")
    if not (os.path.exists(emb_path) and os.path.exists(ids_path) and os.path.exists(jd_path)):
        return None
    emb = np.load(emb_path).astype(np.float32)
    ids = np.load(ids_path, allow_pickle=True)
    jd_vecs = np.load(jd_path).astype(np.float32)
    id_to_row = {cid: i for i, cid in enumerate(ids)}
    return {"emb": emb, "ids": ids, "id_to_row": id_to_row, "jd_vecs": jd_vecs}


def semantic_scores(art, order_ids):
    """Return, for the candidates in `order_ids`, a dict of semantic sub-scores in
    [0,1]: 'main' (full JD), 'core' (retrieval/ranking facet), 'anti' (looks-AI-but-
    not-a-fit). Missing candidates get 0."""
    emb, id_to_row = art["emb"], art["id_to_row"]
    jd_vecs = art["jd_vecs"]            # rows: [main, core, anti]
    rows = np.array([id_to_row.get(cid, -1) for cid in order_ids])
    valid = rows >= 0
    sub = np.zeros((len(order_ids), 3), dtype=np.float32)
    if valid.any():
        cand_emb = emb[rows[valid]]                       # (k, d), already normalised
        sims = cand_emb @ jd_vecs.T                       # (k, 3) cosine
        sub[valid] = sims
    # cosine in [-1,1] → [0,1]
    main = np.clip((sub[:, 0] + 1) / 2, 0, 1)
    core = np.clip((sub[:, 1] + 1) / 2, 0, 1)
    anti = np.clip((sub[:, 2] + 1) / 2, 0, 1)
    return {"main": main, "core": core, "anti": anti, "valid": valid}


# ---------------------------------------------------------------------------
# Encoding (used by build_index.py offline, and by the TF-IDF fallback path)
# ---------------------------------------------------------------------------
def encode_with_transformer(texts, batch_size=256, progress=True, max_seq_length=128):
    import os
    import torch
    try:
        torch.set_num_threads(os.cpu_count() or 6)
    except Exception:
        pass
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)
    # Cap sequence length: candidate signal is concentrated in the first ~128 tokens
    # (headline + summary + lead role). Halving the default 256 ~doubles throughput
    # with negligible quality loss on these profiles.
    model.max_seq_length = max_seq_length
    return model.encode(texts, batch_size=batch_size, normalize_embeddings=True,
                        show_progress_bar=progress).astype(np.float32)


def jd_query_texts():
    return [jd_spec.JD_QUERY, jd_spec.JD_QUERY_CORE, jd_spec.JD_QUERY_ANTI]


# ---------------------------------------------------------------------------
# TF-IDF fallback (only if transformer artifacts are absent)
# ---------------------------------------------------------------------------
def tfidf_fallback_scores(docs, order_index):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    queries = jd_query_texts()
    vec = TfidfVectorizer(max_features=40000, ngram_range=(1, 2), sublinear_tf=True,
                          stop_words="english")
    X = vec.fit_transform(docs + queries)
    Xd, Xq = X[:-3], X[-3:]
    sims = cosine_similarity(Xd, Xq)                 # (N, 3) in [0,1]
    main = sims[order_index, 0]
    core = sims[order_index, 1]
    anti = sims[order_index, 2]
    # rescale TF-IDF sims (typically small) to occupy the band better
    def rescale(a):
        a = np.asarray(a, dtype=np.float32)
        m = a.max() or 1.0
        return np.clip(a / m, 0, 1)
    return {"main": rescale(main), "core": rescale(core), "anti": rescale(anti),
            "valid": np.ones(len(order_index), dtype=bool)}
