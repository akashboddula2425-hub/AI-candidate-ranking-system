#!/usr/bin/env python3
"""
build_index.py — OFFLINE pre-computation step (may exceed the 5-minute budget).

Encodes every candidate's profile document with sentence-transformers/all-MiniLM-L6-v2
(CPU), L2-normalises, and saves compact artifacts that rank.py loads at ranking time:

    artifacts/embeddings.f16.npy   (N, 384) float16, L2-normalised
    artifacts/candidate_ids.npy    (N,)     candidate_id strings (row alignment)
    artifacts/jd_vectors.npy       (3, 384) float32  [main, core, anti] JD queries
    artifacts/faiss.index          FAISS IndexFlatIP over the candidate embeddings

Run once, before ranking:

    python build_index.py --candidates ./candidates.jsonl

The split (slow precompute offline, fast ranking online) is exactly the
latency-quality tradeoff the JD/spec asks for: no LLM-per-candidate, a cheap dense
index built once, and a sub-minute ranking pass over it.
"""
import argparse
import json
import os
import sys
import time

import numpy as np

from src.profile import semantic_document
from src import semantic


def iter_candidates(path):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidates", required=True)
    ap.add_argument("--artifacts", default="artifacts")
    ap.add_argument("--batch-size", type=int, default=128)
    ap.add_argument("--limit", type=int, default=0, help="encode only first N (debug)")
    args = ap.parse_args()

    os.makedirs(args.artifacts, exist_ok=True)
    t0 = time.time()

    ids, docs = [], []
    for c in iter_candidates(args.candidates):
        ids.append(c.get("candidate_id", ""))
        docs.append(semantic_document(c))
        if args.limit and len(ids) >= args.limit:
            break
    print(f"[build] {len(docs)} documents read in {time.time()-t0:.1f}s", file=sys.stderr)

    # Candidate embeddings
    emb = semantic.encode_with_transformer(docs, batch_size=args.batch_size, progress=True)
    np.save(os.path.join(args.artifacts, "embeddings.f16.npy"), emb.astype(np.float16))
    np.save(os.path.join(args.artifacts, "candidate_ids.npy"), np.array(ids, dtype=object))
    print(f"[build] candidate embeddings {emb.shape} saved at {time.time()-t0:.1f}s",
          file=sys.stderr)

    # JD query vectors [main, core, anti]
    jd_vecs = semantic.encode_with_transformer(semantic.jd_query_texts(),
                                               batch_size=8, progress=False)
    np.save(os.path.join(args.artifacts, "jd_vectors.npy"), jd_vecs.astype(np.float32))

    # FAISS index (production retrieval path / sandbox demo). Optional but on-theme.
    try:
        import faiss
        index = faiss.IndexFlatIP(emb.shape[1])
        index.add(emb.astype(np.float32))
        faiss.write_index(index, os.path.join(args.artifacts, "faiss.index"))
        print(f"[build] FAISS index ({index.ntotal} vecs) saved", file=sys.stderr)
    except Exception as e:
        print(f"[build] (skipped FAISS index: {e})", file=sys.stderr)

    print(f"[build] DONE in {time.time()-t0:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
