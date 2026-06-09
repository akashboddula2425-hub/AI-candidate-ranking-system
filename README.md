# Redrob — Intelligent Candidate Discovery & Ranking

A hybrid (dense-semantic + structured-reasoning) ranker that shortlists the top 100
candidates from a 100,000-profile pool for the released **Senior AI Engineer — Founding
Team** job description.

It is built around one idea: **rank candidates the way a great recruiter would — by
understanding what the role *means*, not by counting keywords.** The system reads the
whole profile (career history, what they actually built, behavioural signals,
platform activity), reasons about the gap between what the JD *says* and what it
*needs*, and is deliberately engineered to fall for none of the dataset's traps
(keyword-stuffers, computer-vision-only specialists, research-only academics,
title-chasers, and the ~80 impossible "honeypot" profiles).

---

## TL;DR — reproduce the submission

```bash
pip install -r requirements.txt

# 1) OFFLINE pre-computation (one-time, may exceed 5 min). Builds the dense index.
python build_index.py --candidates ./candidates.jsonl

# 2) RANKING step — the single reproduce command. Runs in well under 5 min on CPU.
python rank.py --candidates ./candidates.jsonl --out ./submission.csv

# 3) validate format
python validate_submission.py submission.csv
```

The ranking step (`rank.py`) uses **no network, no GPU, and no per-candidate LLM
calls**. It loads the pre-computed embeddings from `./artifacts/` and runs a pure
numpy + Python scoring pass. If `./artifacts/` is absent, it transparently falls back
to a TF-IDF semantic surrogate so the command still produces a valid ranking on a
fresh checkout.

---

## Why this architecture

The JD is unusually explicit about what is and isn't a fit, and the organisers state
plainly that *"find candidates whose skills section contains the most AI keywords"* is
a **trap they built into the data**. So a pure embedding-similarity or keyword model
loses — it ranks keyword-stuffers and honeypots into the top 10 (which is also a
disqualifier: honeypot rate > 10% in the top 100 fails Stage 3).

We therefore use a **hybrid** with a clear division of labour:

| Layer | Catches | Tech |
|---|---|---|
| **Dense semantic** | the *plain-language Tier-5* — someone who built "the ranking and retrieval systems that decide what to show" but never writes "RAG" or "Pinecone" | `sentence-transformers/all-MiniLM-L6-v2`, FAISS |
| **Structured fit** | title vs. career reality, what they *actually built*, experience band, product-vs-services history, location | hand-derived JD lexicons + rules |
| **Integrity guards** | keyword-stuffers and impossible honeypots | consistency checks (date arithmetic, mastery-without-time, title↔skills mismatch) |
| **Behavioural modifier** | who is *actually reachable & available* | the 23 Redrob platform signals → a multiplier |

The semantic layer provides *recall* over genuine fits described in plain language;
the structured + integrity layers provide *precision* and keep traps out of the top.
Neither alone is enough — that's the whole point of the role, and of this design.

### The decisive insight (from data inspection)

- The genuine **Tier-5** candidates share a summary that maps onto the JD almost
  one-to-one ("…the ranking and retrieval systems that decide what to show… shipping
  real systems over research-only work… a working v1 in six weeks over a perfect v2 in
  six months"). They list *plain-language* skills (`Ranking Systems`, `Information
  Retrieval Systems`, `BM25`, `Text Encoders`) — **not** the obvious buzzwords. Only a
  semantic view surfaces them.
- **Keyword-stuffers** are non-engineering professionals (Marketing/Project/HR
  Managers) whose *skills list* is sprayed with `RAG`, `Pinecone`, `Embeddings`, often
  with a give-away summary ("AI enthusiast… took online courses on RAG"). We neutralise
  them by **gating** AI-skill credit on title/career credibility — a Marketing
  Manager's "RAG" skill earns almost nothing.
- **Honeypots** contain internal contradictions (a role claiming more tenure than the
  dates allow; "expert" in many skills with 0 months of use). We catch these with
  simple arithmetic and crush their score, so they never reach the top.
- `Python` appears as a listed skill on only ~1.4% of profiles — a quiet positive
  signal that the buzzword-stuffers lack.

---

## How a candidate is scored

`final = fit × behavioural × disqualifier × honeypot × stuffer`

where `fit` is a weighted blend (weights in `src/scoring.py`):

```
0.22 title        — current + best career title, max across the arc (anti-stuffer)
0.22 domain       — retrieval/ranking/recsys evidence in their OWN words (skills gated)
0.13 semantic-core— dense similarity to the retrieval/ranking facet of the JD
0.11 semantic-main— dense similarity to the full distilled JD
0.14 career arc   — product-vs-services ratio, tenure stability (anti title-chaser)
0.10 experience   — soft band peaking at the JD's ideal 6–8 yrs
0.08 location     — Noida/Pune > welcome cities > India > abroad (no visa sponsorship)
```

Multipliers:

- **behavioural** (`src/behavioral.py`, ~0.5–1.15): recency of activity, recruiter
  response rate, open-to-work, interview-completion, completeness, recruiter demand,
  verification. The JD: *"a perfect-on-paper candidate who hasn't logged in for 6
  months… is not actually available. Down-weight them."*
- **disqualifier** (`src/features.py`): CV/speech focus without IR/NLP (×0.55);
  research-leaning with no production signal (×0.6).
- **honeypot** (`src/integrity.py`): hard impossibility → ×0.03.
- **stuffer** (`src/integrity.py`): non-eng title + buzzword skills → ×0.25–0.4.

Every component also emits human-readable evidence, which `src/reasoning.py` turns
into a specific, non-templated, hallucination-free justification per candidate.

---

## Repository layout

```
rank.py                 # ← the single reproduce command (fast ranking step)
build_index.py          # offline pre-computation: embeddings + FAISS index
app.py                  # Streamlit sandbox demo (rank a small uploaded sample)
validate_submission.py  # organisers' format validator (copied for convenience)
requirements.txt
submission_metadata.yaml
src/
  jd_spec.py            # the JD distilled into lexicons, title weights, queries
  profile.py            # parse a candidate, build the document, date helpers
  features.py           # structured fit components + disqualifier penalties
  semantic.py           # load pre-computed embeddings; TF-IDF fallback
  integrity.py          # honeypot + keyword-stuffer detection
  behavioral.py         # 23 signals → availability multiplier
  reasoning.py          # specific, varied, honest reasoning strings
  scoring.py            # weighted blend of everything
  ranker.py             # orchestration: stream → score → sort → top-100
artifacts/              # pre-computed (built by build_index.py)
  embeddings.f16.npy    #   (100000, 384) float16, L2-normalised
  candidate_ids.npy     #   row→candidate_id alignment
  jd_vectors.npy        #   (3, 384) [main, core, anti] JD query embeddings
  faiss.index           #   IndexFlatIP for the production retrieval path
docs/                   # the approach deck (PDF)
```

## Compute profile

- **Ranking step**: CPU-only, no network. ~10–30 s of scoring after a one-time read
  of the candidate file; comfortably inside the 5-min / 16 GB budget.
- **Pre-computation** (`build_index.py`): ~30 min on a 12-core CPU to embed 100K
  profiles with all-MiniLM-L6-v2 (`max_seq_length=128`). One-time, offline,
  explicitly allowed to exceed the 5-min window by the spec.

## Reproducibility notes

- `TODAY` is pinned (`src/profile.py`) so recency/tenure math is deterministic.
- Embeddings are keyed by `candidate_id`, so the artifacts align with any ordering of
  `candidates.jsonl`. `build_index.py` regenerates them from scratch.
- Sorting tie-break is `(score desc, candidate_id asc)`; output scores are emitted on a
  strictly-decreasing band so the CSV is always monotonic and passes the validator.

See `submission_metadata.yaml` for team / AI-tools declaration and
`docs/` for the approach deck.
