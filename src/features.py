"""
features.py — the structured "fit" scorer. This is the part that reads a profile the
way a recruiter does: title & career arc, what they actually built (career text),
experience band, product-vs-services history, location, and the JD's explicit
disqualifiers (research-only, CV/speech-only, title-chasing, dropped-out-of-coding).

Every component returns a value in roughly [0, 1] (a few can go slightly negative as
penalties). scoring.py combines them with weights and the behavioural/integrity
multipliers. Each component also stashes human-readable evidence used by reasoning.py.
"""
from __future__ import annotations
import math
from . import jd_spec
from .profile import norm


# ---------------------------------------------------------------------------
# Title fit
# ---------------------------------------------------------------------------
def _title_weight(title: str) -> float:
    # order matters: management/non-eng checked, but engineering substrings win.
    best = 0.0
    for kw in jd_spec.TITLE_CORE:
        if kw in title:
            best = max(best, 1.0)
    for kw in jd_spec.TITLE_DS:
        if kw in title:
            best = max(best, 0.85)
    for kw in jd_spec.TITLE_SWE:
        if kw in title:
            best = max(best, 0.62 if "backend" in title or "software" in title else 0.5)
    if "software engineer" in title and ("ml" in title or "machine learning" in title):
        best = max(best, 0.85)
    for kw in jd_spec.TITLE_TECH:
        if kw in title:
            best = max(best, 0.22)
    # Non-eng titles cap the score low unless an eng keyword already matched high.
    if best < 0.3:
        for kw in jd_spec.TITLE_NONENG:
            if kw in title:
                return 0.03
    return best


def title_fit(cand) -> tuple[float, dict]:
    """Max title weight across the arc, but current title gets full weight and past
    titles are discounted to 0.85 so a current engineer dominates a past one."""
    cur = norm(cand.profile.get("current_title", ""))
    cur_w = _title_weight(cur)
    past_w = 0.0
    best_past_title = ""
    for h in cand.career[1:]:
        w = _title_weight(norm(h.get("title", "")))
        if w > past_w:
            past_w, best_past_title = w, h.get("title", "")
    score = max(cur_w, 0.85 * past_w)

    # Pure-management current title with no recent IC engineering → JD down-weights
    # "senior engineer who hasn't written production code in 18 months".
    mgmt = any(k in (" " + cur + " ") for k in jd_spec.TITLE_MANAGEMENT)
    if mgmt and "engineer" not in cur and cur_w < 0.5:
        score *= 0.7
    ev = {"current_title": cand.profile.get("current_title", ""),
          "current_w": cur_w, "best_past": best_past_title, "score": score}
    return score, ev


# ---------------------------------------------------------------------------
# Domain fit — what they actually built. Career text is trusted; skills are gated by
# title credibility so a Marketing Manager's "RAG" skill earns almost nothing.
# ---------------------------------------------------------------------------
def _weighted_hits(text: str, lexicon: dict) -> tuple[float, list[str]]:
    total, hits = 0.0, []
    for phrase, w in lexicon.items():
        if phrase in text:
            total += w
            hits.append(phrase.strip())
    return total, hits


def domain_fit(cand, title_score: float) -> tuple[float, dict]:
    ctext = cand.ctext
    core_t, core_hits = _weighted_hits(ctext, jd_spec.CONCEPTS_CORE)
    ml_t, ml_hits = _weighted_hits(ctext, jd_spec.CONCEPTS_ML)
    prod_t, prod_hits = _weighted_hits(ctext, jd_spec.CONCEPTS_PROD)
    bonus_t, bonus_hits = _weighted_hits(ctext, jd_spec.CONCEPTS_BONUS)

    # Skills list: count core+ml concepts present as skill names, but gate the credit
    # by how credible the candidate's title/career is (anti keyword-stuffer).
    skill_blob = " " + " ".join(cand.skill_set) + " "
    sk_core, _ = _weighted_hits(skill_blob, jd_spec.CONCEPTS_CORE)
    sk_ml, _ = _weighted_hits(skill_blob, jd_spec.CONCEPTS_ML)
    gate = min(1.0, 0.15 + title_score)          # 0.15 floor .. up to ~1.15→1.0
    skills_credit = 0.25 * (sk_core + 0.5 * sk_ml) * gate

    # Saturate each bucket so a long description can't run away.
    def sat(x, k):
        return 1.0 - math.exp(-x / k)

    raw = (1.5 * sat(core_t, 2.5) +     # retrieval/ranking is the bullseye
           0.7 * sat(ml_t, 3.0) +
           0.9 * sat(prod_t, 2.5) +
           0.4 * sat(bonus_t, 2.0) +
           0.5 * sat(skills_credit, 1.5))
    score = raw / 4.0                    # back to ~[0,1]
    ev = {"core_hits": core_hits, "ml_hits": ml_hits, "prod_hits": prod_hits,
          "bonus_hits": bonus_hits, "core_t": core_t, "prod_t": prod_t}
    return min(score, 1.0), ev


# ---------------------------------------------------------------------------
# Experience band
# ---------------------------------------------------------------------------
def experience_fit(cand) -> tuple[float, dict]:
    y = cand.yoe
    lo, hi = jd_spec.EXP_IDEAL_LO, jd_spec.EXP_IDEAL_HI
    if lo <= y <= hi:
        s = 1.0
    elif y < lo:
        # ramp up from 0 at 1y to 1.0 at 6y; juniors aren't a hard no but discounted
        s = max(0.15, (y - 1.0) / (lo - 1.0))
    else:
        # decay above 8y; 12y ~0.6, 16y ~0.3. The JD will consider out-of-band if
        # other signals are strong, so don't crush it.
        s = max(0.3, 1.0 - (y - hi) * 0.09)
    return s, {"yoe": y}


# ---------------------------------------------------------------------------
# Career arc: product-vs-services, stability (anti title-chaser), recency of IC work.
# ---------------------------------------------------------------------------
def career_arc(cand) -> tuple[float, dict]:
    months_total = sum((h.get("duration_months", 0) or 0) for h in cand.career) or 1
    services_months = 0
    product_hits = 0
    for h in cand.career:
        comp = norm(h.get("company", ""))
        dm = h.get("duration_months", 0) or 0
        if any(f in comp for f in jd_spec.SERVICES_FIRMS):
            services_months += dm
        if any(f in comp for f in jd_spec.PRODUCT_FIRMS):
            product_hits += 1
    product_ratio = 1.0 - services_months / months_total

    # Stability / anti title-chaser: many short stints with rising titles.
    short_stints = sum(1 for h in cand.career
                       if 0 < (h.get("duration_months", 0) or 0) < 20)
    njobs = len(cand.career)
    avg_tenure = months_total / max(njobs, 1)
    hopper = (njobs >= 4 and avg_tenure < 18) or short_stints >= 3

    score = 0.55 * product_ratio + 0.25       # product history is the main driver
    if product_hits:
        score += min(0.15, 0.05 * product_hits)
    if avg_tenure >= 24:
        score += 0.1                          # reward staying-power (JD wants 3+ yrs)
    if hopper:
        score -= 0.25
    score = max(0.0, min(1.0, score))
    ev = {"product_ratio": product_ratio, "services_months": services_months,
          "avg_tenure": avg_tenure, "hopper": hopper, "njobs": njobs,
          "product_hits": product_hits}
    return score, ev


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------
def location_fit(cand) -> tuple[float, dict]:
    loc = norm(cand.profile.get("location", ""))
    country = norm(cand.profile.get("country", ""))
    relo = bool(cand.signals.get("willing_to_relocate", False))

    if any(c in loc for c in jd_spec.LOC_PREFERRED):
        return 1.0, {"why": "Noida/Pune"}
    if any(c in loc for c in jd_spec.LOC_WELCOME):
        return 0.9, {"why": "India tier-1 (welcome city)"}
    if jd_spec.INDIA in country:
        return 0.72 if relo else 0.6, {"why": "India" + (" + willing to relocate" if relo else "")}
    # Abroad: JD doesn't sponsor visas → discount, small credit if willing to relocate.
    return (0.35 if relo else 0.2), {"why": country.title() + (" + relocate" if relo else " (abroad)")}


# ---------------------------------------------------------------------------
# Disqualifier penalties (multiplicative, applied in scoring.py)
# ---------------------------------------------------------------------------
def disqualifier_penalty(cand, domain_ev) -> tuple[float, list[str]]:
    ctext = cand.ctext
    pen = 1.0
    reasons = []

    # CV/speech-heavy WITHOUT NLP/IR — JD: "re-learning fundamentals here".
    cv_t, _ = _weighted_hits(ctext, jd_spec.CONCEPTS_CV_SPEECH)
    cv_skills = sum(1 for s in cand.skill_set
                    if s in {"yolo", "opencv", "computer vision", "object detection",
                             "image classification", "asr", "tts", "speech recognition",
                             "gans", "diffusion models", "cnn"})
    ir_present = domain_ev.get("core_t", 0) > 1.0
    if (cv_t >= 2.0 or cv_skills >= 4) and not ir_present:
        pen *= 0.55
        reasons.append("CV/speech focus without IR/NLP")

    # Research-only without production deployment.
    research = sum(1 for m in jd_spec.CONCEPTS_RESEARCH if m in ctext)
    prod_present = domain_ev.get("prod_t", 0) > 0.8
    if research >= 2 and not prod_present:
        pen *= 0.6
        reasons.append("research-leaning, little production signal")

    return pen, reasons
