"""
profile.py — parse a raw candidate record into the fields the ranker needs, build
the text document we embed / lexically match, and provide small date helpers.

Pure-Python, no heavy deps, so this runs in the fast ranking step.
"""
from __future__ import annotations
from datetime import date
from functools import lru_cache

# Reference "today" for recency / tenure math. Pinned for reproducibility so the
# ranking is deterministic regardless of when rank.py is run.
TODAY = date(2026, 6, 9)


def parse_date(s):
    if not s or not isinstance(s, str):
        return None
    try:
        y, m, d = (int(x) for x in s.split("-")[:3])
        return date(y, m, d)
    except Exception:
        return None


def months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def norm(s) -> str:
    """Lower-case, turn em/en dashes into spaces (so titles like
    'ML Engineer — Search & Ranking' tokenize cleanly), but KEEP regular hyphens and
    slashes so hyphenated terms ('fine-tuning', 'learning-to-rank') and 'a/b test'
    still match the lexicons. Squeeze whitespace."""
    if not s:
        return ""
    s = str(s).lower().replace("—", " ").replace("–", " ")
    return " ".join(s.split())


def build_document(cand: dict) -> str:
    """
    The candidate 'document' used for semantic embedding and lexical matching.
    Order matters a little for truncation: headline + summary first (most signal),
    then career titles/descriptions, then skills, then education.
    """
    p = cand.get("profile", {})
    parts = [
        p.get("headline", ""),
        p.get("summary", ""),
        f"Current role: {p.get('current_title','')} at {p.get('current_company','')}.",
    ]
    for h in cand.get("career_history", []):
        parts.append(f"{h.get('title','')} at {h.get('company','')}: {h.get('description','')}")
    skills = cand.get("skills", [])
    if skills:
        parts.append("Skills: " + ", ".join(s.get("name", "") for s in skills))
    for e in cand.get("education", []):
        parts.append(f"{e.get('degree','')} in {e.get('field_of_study','')}".strip())
    return "\n".join(x for x in parts if x and x.strip())


def semantic_document(cand: dict, max_chars: int = 1100) -> str:
    """A compact, signal-dense version of the profile for embedding. The summary and
    headline carry the strongest fit signal (the Tier-5 template lives there), then
    the two most recent role descriptions, then skills. Truncated for encode speed."""
    p = cand.get("profile", {})
    parts = [
        p.get("headline", ""),
        p.get("summary", ""),
        f"{p.get('current_title','')} at {p.get('current_company','')}.",
    ]
    for h in cand.get("career_history", [])[:2]:
        parts.append(f"{h.get('title','')}: {h.get('description','')}")
    skills = cand.get("skills", [])
    if skills:
        parts.append("Skills: " + ", ".join(s.get("name", "") for s in skills))
    text = " ".join(x for x in parts if x and x.strip())
    return text[:max_chars]


def career_text(cand: dict) -> str:
    """Just the headline+summary+career descriptions — the 'trusted' free text where
    real evidence lives (as opposed to the cheap-to-stuff skills list)."""
    p = cand.get("profile", {})
    parts = [p.get("headline", ""), p.get("summary", "")]
    for h in cand.get("career_history", []):
        parts.append(h.get("title", ""))
        parts.append(h.get("description", ""))
    return norm("\n".join(parts))


def skill_names(cand: dict):
    return [norm(s.get("name", "")) for s in cand.get("skills", [])]


def all_titles(cand: dict):
    """Current title plus every career title, normalised."""
    p = cand.get("profile", {})
    out = [norm(p.get("current_title", ""))]
    out += [norm(h.get("title", "")) for h in cand.get("career_history", [])]
    return [t for t in out if t]


class Candidate:
    """Lightweight parsed view, computed once per candidate."""
    __slots__ = ("raw", "id", "profile", "signals", "career", "skills",
                 "doc", "ctext", "titles", "skill_set", "skill_list", "yoe")

    def __init__(self, raw: dict):
        self.raw = raw
        self.id = raw.get("candidate_id", "")
        self.profile = raw.get("profile", {})
        self.signals = raw.get("redrob_signals", {})
        self.career = raw.get("career_history", [])
        self.skills = raw.get("skills", [])
        self.doc = build_document(raw)
        self.ctext = career_text(raw)
        self.titles = all_titles(raw)
        # ordered, de-duplicated skill names: deterministic for any output/joining.
        # (skill_set is kept for fast membership tests where order is irrelevant.)
        self.skill_list = list(dict.fromkeys(skill_names(raw)))
        self.skill_set = set(self.skill_list)
        self.yoe = float(self.profile.get("years_of_experience", 0) or 0)
