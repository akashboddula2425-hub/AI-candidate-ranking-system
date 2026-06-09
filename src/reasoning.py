"""
reasoning.py — generate the 1-2 sentence justification for each shortlisted
candidate. Stage-4 manual review checks that reasoning is specific, references real
profile facts, connects to JD requirements, acknowledges concerns honestly, varies
across candidates, and never hallucinates skills the candidate doesn't have.

We compose from facts we actually extracted (no LLM, no invented skills): the title,
years, the strongest retrieval/ranking evidence we found in their own text, their
companies, location, and the single most relevant behavioural note or concern. The
tone is tied to the score band so a rank-5 reads confident and a rank-95 reads hedged.
"""
from __future__ import annotations
from .profile import norm
from .behavioral import availability_concern

# Phrases we are willing to surface as "retrieval/ranking evidence", mapped to clean
# display text. Only used if actually present in the candidate's career text/skills.
_EVIDENCE_DISPLAY = [
    ("information retrieval", "information retrieval"),
    ("learning to rank", "learning-to-rank"),
    ("ranking", "ranking systems"),
    ("recommendation", "recommendation systems"),
    ("recommender", "recommender systems"),
    ("semantic search", "semantic search"),
    ("vector search", "vector search"),
    ("vector representation", "vector representations"),
    ("search & discovery", "search & discovery"),
    ("search and discovery", "search & discovery"),
    ("search infrastructure", "search infrastructure"),
    ("search backend", "search backends"),
    ("embedding", "embeddings"),
    ("bm25", "BM25 retrieval"),
    ("text encoder", "text encoders"),
    ("hybrid search", "hybrid search"),
    ("re-rank", "re-ranking"),
    ("personalization", "personalization"),
]

_SKILL_DISPLAY = {
    "faiss": "FAISS", "pinecone": "Pinecone", "weaviate": "Weaviate", "qdrant": "Qdrant",
    "milvus": "Milvus", "pgvector": "pgvector", "elasticsearch": "Elasticsearch",
    "opensearch": "OpenSearch", "haystack": "Haystack", "pytorch": "PyTorch",
    "learning to rank": "Learning-to-Rank", "bm25": "BM25", "qlora": "QLoRA",
    "lora": "LoRA", "peft": "PEFT", "sentence transformers": "Sentence-Transformers",
    "python": "Python",
}


def _found_evidence(cand, limit=2):
    seen, out = set(), []
    for needle, disp in _EVIDENCE_DISPLAY:
        if needle in cand.ctext and disp not in seen:
            out.append(disp)
            seen.add(disp)
        if len(out) >= limit:
            break
    return out


def _named_skills(cand, limit=3):
    out = []
    for s in cand.skill_list:          # original profile order → deterministic
        if s in _SKILL_DISPLAY:
            out.append(_SKILL_DISPLAY[s])
        if len(out) >= limit:
            break
    return out


def _companies(cand, limit=2):
    out = []
    for h in cand.career[:limit]:
        c = h.get("company", "")
        if c:
            out.append(c)
    return out


def make_reasoning(cand, comp: dict, score: float) -> str:
    """comp = dict of component scores/evidence from scoring.score_candidate."""
    p = cand.profile
    title = p.get("current_title", "Engineer")
    yoe = cand.yoe
    loc = p.get("location", "").split(",")[0].strip()

    evidence = _found_evidence(cand)
    skills = _named_skills(cand)
    comps = _companies(cand)
    concern = availability_concern(cand)

    # Lead clause: who they are.
    lead = f"{title} with {yoe:.0f} yrs"
    if comps:
        lead += f" ({', '.join(comps[:2])})"

    # Fit clause: what they actually built / bring, connected to the JD.
    if evidence:
        fit = f"; direct {', '.join(evidence)} experience"
    elif comp.get("domain", 0) > 0.45:
        fit = "; applied-ML / retrieval background"
    elif comp.get("title", 0) >= 0.85:
        fit = "; core ML engineering profile"
    else:
        fit = "; adjacent engineering background"
    if skills:
        fit += f" ({', '.join(skills)})"

    # Location clause.
    locclause = ""
    if comp.get("location", 0) >= 0.9 and loc:
        locclause = f"; {loc}-based"
    elif comp.get("location", 0) >= 0.6 and loc:
        locclause = f"; {loc}, open to relocate" if cand.signals.get("willing_to_relocate") else f"; {loc}"

    # Behaviour / concern clause — honesty for Stage-4.
    resp = cand.signals.get("recruiter_response_rate", None)
    if concern:
        tail = f". Concern: {concern}."
    elif resp is not None and resp >= 0.5:
        tail = f". Engaged (responds to {resp:.0%} of recruiters)."
    else:
        tail = "."

    text = lead + fit + locclause + tail

    # Tone calibration by band so reasoning matches rank.
    if score < 0.45:
        text = text.rstrip(".") + "; included as lower-confidence filler."
    text = " ".join(text.split())
    # Safety: keep it to ~2 sentences / reasonable length.
    return text[:300]
