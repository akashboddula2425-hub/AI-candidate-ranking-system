"""
integrity.py — profile-consistency checks.

Two jobs:
  1. honeypot_score(): catch the ~80 'subtly impossible' profiles the organisers
     planted (forced to relevance tier 0; >10% in your top-100 = disqualification).
     We rely on *internal contradictions* a careful recruiter would notice, not on
     special-casing — exactly as the spec recommends.
  2. stuffer_score(): catch the keyword-stuffer archetype — a non-engineering
     professional who has sprayed AI buzzwords into their skills list.

Both return a penalty multiplier in (0, 1]; 1.0 = clean.
"""
from __future__ import annotations
from .profile import parse_date, months_between, TODAY, norm
from . import jd_spec

_AI_BUZZ = {
    "rag", "pinecone", "embeddings", "vector search", "semantic search", "langchain",
    "llms", "sentence transformers", "hugging face transformers", "information retrieval",
    "recommendation systems", "faiss", "fine-tuning llms", "prompt engineering",
    "weaviate", "qdrant", "milvus",
}


def honeypot_flags(cand) -> list[str]:
    """Return a list of impossibility flags. Empty list == looks self-consistent."""
    flags = []
    yoe = cand.yoe
    yoe_months = yoe * 12.0

    # (a) A role claiming far more tenure than the dates allow — e.g. "8 years at a
    #     company founded 3 years ago". duration_months should not exceed the span
    #     between start_date and (end_date or today) by more than a rounding margin.
    for h in cand.career:
        sd = parse_date(h.get("start_date"))
        ed = parse_date(h.get("end_date")) or TODAY
        dm = h.get("duration_months", 0) or 0
        if sd is None:
            continue
        if sd > TODAY:
            flags.append("future_start")
        span = months_between(sd, ed)
        if dm - span > 13:               # >1y more tenure than dates permit
            flags.append(f"tenure_impossible:{h.get('company','?')}")

    # (b) "Expert/advanced in N skills with 0 months of use" — claimed mastery with
    #     zero duration. A few can be data noise; several is a manufactured profile.
    adv0 = sum(1 for s in cand.skills
               if s.get("proficiency") in ("expert", "advanced")
               and (s.get("duration_months", 0) or 0) == 0)
    if adv0 >= 4:
        flags.append(f"mastery_without_time:{adv0}")

    # (c) Total claimed career duration wildly exceeds stated years of experience.
    career_total = sum((h.get("duration_months", 0) or 0) for h in cand.career)
    if career_total - yoe_months > 60:   # >5y more career than experience claimed
        flags.append("career_exceeds_experience")

    # (d) An assessment score for a skill the candidate doesn't even list, at expert
    #     level with no time — only counts when combined with (b)-style emptiness.
    return flags


def honeypot_score(cand) -> tuple[float, list[str]]:
    """Multiplier in (0,1]. Strong impossibilities are crushed so they cannot reach
    the top of the list even if every other signal is glowing."""
    flags = honeypot_flags(cand)
    if not flags:
        return 1.0, flags
    # Any hard impossibility (bad dates / mastery-without-time) → effectively removed.
    hard = any(f.startswith(("tenure_impossible", "mastery_without_time", "future_start"))
               for f in flags)
    if hard:
        return 0.03, flags
    return 0.5, flags   # softer inconsistency → heavy but not fatal


def stuffer_score(cand, title_fit: float) -> tuple[float, bool]:
    """
    Penalise keyword-stuffers: low title/career relevance but a skills list peppered
    with AI buzzwords, often with a give-away summary ('AI enthusiast', 'took online
    courses on RAG'). Returns (multiplier, is_stuffer).
    """
    buzz = len(cand.skill_set & _AI_BUZZ)
    if title_fit >= 0.5:
        return 1.0, False                # a real engineer listing buzzwords is fine

    ctext = cand.ctext
    tell = any(t in ctext for t in jd_spec.CONCEPTS_TUTORIAL)

    if title_fit <= 0.1 and buzz >= 3:
        # Classic stuffer: non-eng title + several buzzwords.
        return (0.25 if tell else 0.35), True
    if title_fit < 0.4 and buzz >= 5 and tell:
        return 0.4, True
    return 1.0, False
