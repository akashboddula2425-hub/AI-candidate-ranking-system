"""
app.py — Streamlit sandbox demo for the Redrob ranker.

Satisfies the hackathon's sandbox requirement: upload a small candidate sample
(<= ~200 records, .jsonl or .json), the app runs the *same* ranking pipeline used to
produce the submission, and returns a ranked, downloadable CSV with reasoning — all
within the CPU compute budget.

For a faithful end-to-end demo it embeds the uploaded sample live with the same
sentence-transformer; if that model can't load it falls back to TF-IDF. Either way the
structured fit / integrity / behavioural logic is identical to rank.py.

Run locally:  streamlit run app.py
"""
import io
import json

import numpy as np
import streamlit as st

from src.profile import Candidate, semantic_document
from src.behavioral import availability_multiplier, availability_concern
from src import scoring, semantic, reasoning

st.set_page_config(page_title="Redrob Candidate Ranker", layout="wide")
st.title("🧭 Redrob — Intelligent Candidate Ranker")
st.caption("Hybrid dense-semantic + structured-reasoning ranker for the Senior AI "
           "Engineer JD. Upload a small candidate sample to see it run end-to-end.")


def parse_upload(raw_bytes):
    text = raw_bytes.decode("utf-8")
    cands = []
    text_stripped = text.lstrip()
    if text_stripped.startswith("["):
        for obj in json.loads(text):
            cands.append(obj)
    else:
        for line in text.splitlines():
            line = line.strip()
            if line:
                cands.append(json.loads(line))
    return cands


@st.cache_resource(show_spinner=False)
def get_encoder():
    try:
        from sentence_transformers import SentenceTransformer
        m = SentenceTransformer(semantic.MODEL_NAME)
        m.max_seq_length = 128
        return m
    except Exception:
        return None


def embed_sample(raw_cands):
    """Live-encode a small sample. Returns (sem_main, sem_core, sem_anti) arrays."""
    docs = [semantic_document(c) for c in raw_cands]
    model = get_encoder()
    if model is not None:
        emb = model.encode(docs, normalize_embeddings=True, show_progress_bar=False)
        jd = model.encode(semantic.jd_query_texts(), normalize_embeddings=True,
                          show_progress_bar=False)
        sims = (emb @ jd.T + 1) / 2
        return sims[:, 0], sims[:, 1], sims[:, 2], "dense (all-MiniLM-L6-v2)"
    sem = semantic.tfidf_fallback_scores(docs, list(range(len(docs))))
    return sem["main"], sem["core"], sem["anti"], "TF-IDF fallback"


uploaded = st.file_uploader("Candidate sample (.jsonl or .json)",
                            type=["jsonl", "json", "txt"])
topk = st.slider("Shortlist size", 5, 100, 25)

if uploaded is not None:
    raw = parse_upload(uploaded.read())
    st.write(f"Loaded **{len(raw)}** candidates.")
    with st.spinner("Ranking…"):
        sem_main, sem_core, sem_anti, mode = embed_sample(raw)
        cands = [Candidate(c) for c in raw]
        rows = []
        for i, c in enumerate(cands):
            comp = scoring.structured_components(c)
            behav, _ = availability_multiplier(c)
            blend = scoring.combine(comp, float(sem_main[i]), float(sem_core[i]),
                                    float(sem_anti[i]), behav)
            rows.append((c, comp, blend))
        rows.sort(key=lambda r: (-r[2]["final"], r[0].id))
        rows = rows[:topk]
        maxf = max((r[2]["final"] for r in rows), default=1.0) or 1.0

    st.caption(f"Semantic mode: **{mode}**")
    table, csv_rows = [], []
    for rank_pos, (c, comp, blend) in enumerate(rows, start=1):
        why = reasoning.make_reasoning(c, blend, blend["final"] / maxf)
        score = round(0.45 + 0.54 * (blend["final"] / maxf), 4)
        table.append({
            "rank": rank_pos, "candidate_id": c.id,
            "title": c.profile.get("current_title", ""),
            "yoe": c.yoe, "score": score,
            "flags": ("honeypot " if comp["hp_flags"] else "") +
                     ("stuffer" if comp["is_stuffer"] else ""),
            "reasoning": why,
        })
        csv_rows.append([c.id, rank_pos, f"{score:.4f}", why])

    st.dataframe(table, use_container_width=True, hide_index=True)

    buf = io.StringIO()
    import csv as _csv
    w = _csv.writer(buf)
    w.writerow(["candidate_id", "rank", "score", "reasoning"])
    w.writerows(csv_rows)
    st.download_button("⬇️ Download ranked CSV", buf.getvalue(),
                       file_name="ranked_sample.csv", mime="text/csv")
else:
    st.info("Tip: use the bundled `sample_candidates.json`, or any slice of "
            "`candidates.jsonl`, to try it.")
