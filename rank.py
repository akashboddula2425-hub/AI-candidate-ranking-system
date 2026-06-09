#!/usr/bin/env python3
"""
rank.py — produce the top-100 submission CSV from candidates.jsonl.

This is the single reproduce command for the hackathon:

    python rank.py --candidates ./candidates.jsonl --out ./submission.csv

It runs the *ranking step only*: it loads candidates, blends a pre-computed
dense-semantic similarity (from ./artifacts, built offline by build_index.py) with a
structured recruiter-style fit model and behavioural / integrity multipliers, and
writes the ranked CSV. No network, no GPU, no per-candidate LLM calls — it is pure
numpy + Python over pre-computed embeddings and runs well within the 5-minute budget.

If ./artifacts is missing, it transparently falls back to a TF-IDF semantic surrogate
so the command still works end-to-end on a fresh checkout.
"""
import argparse
import sys

from src.ranker import rank


def main():
    ap = argparse.ArgumentParser(description="Redrob hybrid candidate ranker")
    ap.add_argument("--candidates", required=True, help="path to candidates.jsonl")
    ap.add_argument("--out", default="submission.csv", help="output CSV path")
    ap.add_argument("--artifacts", default="artifacts",
                    help="dir with pre-computed embeddings (default: artifacts)")
    ap.add_argument("--topk", type=int, default=100)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    rank(args.candidates, args.out, artifacts_dir=args.artifacts,
         topk=args.topk, verbose=not args.quiet)
    print(f"Done → {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
