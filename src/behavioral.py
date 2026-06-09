"""
behavioral.py — turn the 23 Redrob platform signals into an *availability &
hireability* multiplier.

The JD is explicit: "a perfect-on-paper candidate who hasn't logged in for 6 months
and has a 5% recruiter response rate is, for hiring purposes, not actually available.
Down-weight them appropriately." So behaviour is a modifier on top of fit, not a
fit signal itself — a great profile that's unreachable should drop, but behaviour
alone never makes an unqualified person a top pick.

Returns a multiplier centred slightly below 1.0, roughly in [0.55, 1.15].
"""
from __future__ import annotations
from .profile import parse_date, TODAY


def _recency_factor(last_active):
    d = parse_date(last_active)
    if d is None:
        return 0.8
    days = (TODAY - d).days
    if days <= 30:
        return 1.0
    if days <= 90:
        return 0.96
    if days <= 180:
        return 0.88
    if days <= 365:
        return 0.72
    return 0.55


def availability_multiplier(cand) -> tuple[float, dict]:
    s = cand.signals
    notes = {}

    recency = _recency_factor(s.get("last_active_date"))
    notes["recency"] = recency

    resp = s.get("recruiter_response_rate", 0.0)
    if resp is None:
        resp = 0.0
    # Responsiveness: a 5% responder is essentially unreachable; ~0.5+ is healthy.
    # Gentle floor so a strong fit who replies sometimes isn't crushed.
    resp_factor = 0.75 + 0.25 * min(resp / 0.5, 1.0)     # 0.75 .. 1.0
    notes["resp"] = resp

    open_flag = bool(s.get("open_to_work_flag", False))
    open_factor = 1.0 if open_flag else 0.92
    notes["open"] = open_flag

    icr = s.get("interview_completion_rate", 0.0) or 0.0
    icr_factor = 0.92 + 0.08 * min(icr, 1.0)             # 0.92 .. 1.0

    completeness = (s.get("profile_completeness_score", 0) or 0) / 100.0
    comp_factor = 0.96 + 0.04 * completeness             # 0.96 .. 1.0

    # Recruiter demand (others already want them) — a mild positive.
    saved = s.get("saved_by_recruiters_30d", 0) or 0
    demand_factor = 1.0 + 0.05 * min(saved / 5.0, 1.0)   # up to +5%

    # Verification / reachability — small bump for verified + linkedin.
    trust = 0.0
    trust += 0.015 if s.get("verified_email") else 0.0
    trust += 0.015 if s.get("verified_phone") else 0.0
    trust += 0.01 if s.get("linkedin_connected") else 0.0
    trust_factor = 1.0 + trust                            # up to +4%

    mult = (recency * resp_factor * open_factor * icr_factor *
            comp_factor * demand_factor * trust_factor)

    # Clamp to a gentle envelope: behaviour shades the ordering and sinks the truly
    # unavailable, but does not override a clear fit-tier difference.
    mult = max(0.62, min(1.08, mult))
    notes["mult"] = mult
    return mult, notes


def availability_concern(cand) -> str | None:
    """A short human-readable concern for the reasoning column, if any."""
    s = cand.signals
    resp = s.get("recruiter_response_rate", 1.0) or 0.0
    d = parse_date(s.get("last_active_date"))
    days = (TODAY - d).days if d else 999
    if days > 180:
        return f"inactive ~{days//30} months"
    if resp < 0.2:
        return f"low recruiter response rate ({resp:.0%})"
    notice = s.get("notice_period_days", 0) or 0
    if notice >= 90:
        return f"long notice period ({notice}d)"
    return None
