"""
ranker.py — orchestration. Streams candidates.jsonl, computes structured features,
blends the pre-computed dense-semantic similarity, applies behavioural & integrity
multipliers, sorts, and emits the top-100 with reasoning.

This is the code path that must run within the 5-min / 16 GB / CPU-only budget. It
is pure numpy + Python over pre-computed embeddings — no model inference, no network.
"""
from __future__ import annotations
import csv
import json
import os
import sys
import time

import numpy as np

from .profile import Candidate, build_document
from .behavioral import availability_multiplier
from . import scoring, semantic, reasoning


def load_candidates(path):
    cands = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cands.append(Candidate(json.loads(line)))
    return cands


def rank(candidates_path, out_path, artifacts_dir="artifacts", topk=100, verbose=True):
    t0 = time.time()
    cands = load_candidates(candidates_path)
    n = len(cands)
    if verbose:
        print(f"[rank] loaded {n} candidates in {time.time()-t0:.1f}s", file=sys.stderr)

    ids = [c.id for c in cands]

    # --- Semantic component (dense embeddings, pre-computed; TF-IDF fallback) ---
    art = semantic.load_artifacts(artifacts_dir)
    if art is not None:
        sem = semantic.semantic_scores(art, ids)
        sem_mode = "dense(all-MiniLM-L6-v2)"
    else:
        if verbose:
            print("[rank] embedding artifacts not found → TF-IDF fallback", file=sys.stderr)
        docs = [c.doc for c in cands]
        sem = semantic.tfidf_fallback_scores(docs, list(range(n)))
        sem_mode = "tfidf-fallback"
    sem_main, sem_core, sem_anti = sem["main"], sem["core"], sem["anti"]
    if verbose:
        print(f"[rank] semantic scores ready ({sem_mode}) at {time.time()-t0:.1f}s", file=sys.stderr)

    # --- Per-candidate structured + integrity + behavioural, then combine ---
    finals = np.zeros(n, dtype=np.float64)
    comps = [None] * n
    blends = [None] * n
    for i, c in enumerate(cands):
        comp = scoring.structured_components(c)
        behav, _ = availability_multiplier(c)
        blend = scoring.combine(comp, float(sem_main[i]), float(sem_core[i]),
                                float(sem_anti[i]), behav)
        finals[i] = blend["final"]
        comps[i] = comp
        blends[i] = blend
    if verbose:
        print(f"[rank] scored all candidates at {time.time()-t0:.1f}s", file=sys.stderr)

    # --- Sort: score desc, candidate_id asc as deterministic tie-break ---
    order = sorted(range(n), key=lambda i: (-finals[i], ids[i]))
    top = order[:topk]

    # --- Output scores: map to a readable, strictly-decreasing band so the CSV is
    #     monotonic and never trips the tie-break rule (ties → vacuous). ---
    raw_top = np.array([finals[i] for i in top], dtype=np.float64)
    lo, hi = raw_top.min(), raw_top.max()
    if hi <= lo:
        norm = np.linspace(0.99, 0.45, len(top))
    else:
        norm = 0.45 + (raw_top - lo) / (hi - lo) * (0.99 - 0.45)
    out_scores = []
    prev = 1.0
    for v in norm:
        s = round(float(v), 4)
        if s >= prev:
            s = round(prev - 0.0001, 4)
        prev = s
        out_scores.append(s)

    # --- Write CSV ---
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["candidate_id", "rank", "score", "reasoning"])
        for rank_pos, (i, sc) in enumerate(zip(top, out_scores), start=1):
            text = reasoning.make_reasoning(cands[i], blends[i], blends[i]["final"] /
                                            (raw_top.max() or 1.0))
            w.writerow([ids[i], rank_pos, f"{sc:.4f}", text])

    if verbose:
        hp_in_top = sum(1 for i in top if comps[i]["hp_flags"])
        stuffers_in_top = sum(1 for i in top if comps[i]["is_stuffer"])
        print(f"[rank] wrote {len(top)} rows to {out_path} at {time.time()-t0:.1f}s",
              file=sys.stderr)
        print(f"[rank] sanity: honeypot-flagged in top100={hp_in_top}, "
              f"stuffer-flagged in top100={stuffers_in_top}", file=sys.stderr)
    return top, [ids[i] for i in top]
