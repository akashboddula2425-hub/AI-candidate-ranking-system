"""
scoring.py — combine the structured fit components, the dense-semantic similarity,
and the behavioural / integrity multipliers into one final score per candidate.

Design intent (mirrors how the composite metric is weighted — top-10 quality is 50%):
the components that *separate a genuine fit from a trap* (title, what-they-built,
career arc, semantic understanding) carry the most weight, then experience and
location shade the ordering, then behaviour & integrity act as multipliers that can
rescue or sink a candidate the way real availability/credibility does.
"""
from __future__ import annotations
from . import features
from .integrity import honeypot_score, stuffer_score

# Fit weights (sum to 1.0). Two views of "what they built" — lexical (domain) and
# dense (semantic) — are intentionally both present: that's the hybrid.
W = {
    "title": 0.22,
    "domain": 0.22,
    "sem_main": 0.11,
    "sem_core": 0.13,
    "experience": 0.10,
    "career": 0.14,
    "location": 0.08,
}


def structured_components(cand) -> dict:
    """All the non-semantic, per-candidate signals + evidence (no batching needed)."""
    t, t_ev = features.title_fit(cand)
    d, d_ev = features.domain_fit(cand, t)
    e, e_ev = features.experience_fit(cand)
    c, c_ev = features.career_arc(cand)
    loc, loc_ev = features.location_fit(cand)
    dq_pen, dq_reasons = features.disqualifier_penalty(cand, d_ev)
    hp_mult, hp_flags = honeypot_score(cand)
    st_mult, is_stuffer = stuffer_score(cand, t)
    return {
        "title": t, "domain": d, "experience": e, "career": c, "location": loc,
        "title_ev": t_ev, "domain_ev": d_ev, "career_ev": c_ev, "loc_ev": loc_ev,
        "dq_pen": dq_pen, "dq_reasons": dq_reasons,
        "hp_mult": hp_mult, "hp_flags": hp_flags,
        "st_mult": st_mult, "is_stuffer": is_stuffer,
    }


def combine(comp: dict, sem_main: float, sem_core: float, sem_anti: float,
            behav_mult: float) -> dict:
    """Blend into a final score. Returns the final score plus the pieces (for
    reasoning / debugging)."""
    fit = (W["title"] * comp["title"] +
           W["domain"] * comp["domain"] +
           W["sem_main"] * sem_main +
           W["sem_core"] * sem_core +
           W["experience"] * comp["experience"] +
           W["career"] * comp["career"] +
           W["location"] * comp["location"])

    # Anti-query dampener: if the profile reads as "looks-AI-but-not-a-fit" (high anti
    # similarity) AND the title is weak, shave the fit — reinforces the stuffer guard
    # for cases the skills-list heuristic misses.
    if sem_anti > 0.62 and comp["title"] < 0.4:
        fit *= 0.85

    final = fit * behav_mult * comp["dq_pen"] * comp["hp_mult"] * comp["st_mult"]

    return {
        "fit": fit, "final": final,
        "title": comp["title"], "domain": comp["domain"],
        "experience": comp["experience"], "career": comp["career"],
        "location": comp["location"], "sem_main": sem_main, "sem_core": sem_core,
        "behav": behav_mult, "dq_pen": comp["dq_pen"], "hp_mult": comp["hp_mult"],
        "st_mult": comp["st_mult"],
    }
