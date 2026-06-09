"""
Sanity checks that the structured + integrity layers behave on known archetypes:
  * keyword-stuffer  -> flagged, heavily penalised
  * plain-language Tier-5 -> high title + domain, clean
  * honeypot (impossible tenure / mastery-without-time) -> hp flag, crushed
Run: python tests/test_trap_defense.py  (needs the released candidates.jsonl path)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.profile import Candidate
from src import scoring
from src.behavioral import availability_multiplier

DATA = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CANDIDATES")

WANT = {
    "CAND_0000021": "keyword-stuffer (Project Manager + buzzwords)",
    "CAND_0005538": "plain-language Tier-5 (Senior AI Engineer, Adobe)",
    "CAND_0006567": "plain-language Tier-5 (Senior AI Engineer, Meta)",
    "CAND_0061257": "plain-language Tier-5 (Staff MLE, LinkedIn)",
    "CAND_0007353": "honeypot-ish (dur>span @ Wayne Enterprises)",
    "CAND_0008960": "honeypot-ish (dur>span @ Stark Industries)",
}


def main():
    found = {}
    with open(DATA, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            if any(cid in line for cid in WANT):
                c = json.loads(line)
                if c["candidate_id"] in WANT:
                    found[c["candidate_id"]] = c
            if len(found) == len(WANT):
                break

    print(f"{'id':16} {'title':18} {'titl':>5} {'dom':>5} {'care':>5} "
          f"{'hp':>5} {'stuf':>5} {'final':>7}  note")
    for cid, note in WANT.items():
        if cid not in found:
            print(f"{cid:16} (not found in scan)")
            continue
        cand = Candidate(found[cid])
        comp = scoring.structured_components(cand)
        behav, _ = availability_multiplier(cand)
        # use neutral semantic (0.5) to isolate structured behaviour
        blend = scoring.combine(comp, 0.5, 0.5, 0.5, behav)
        print(f"{cid:16} {cand.profile.get('current_title','')[:18]:18} "
              f"{comp['title']:5.2f} {comp['domain']:5.2f} {comp['career']:5.2f} "
              f"{comp['hp_mult']:5.2f} {comp['st_mult']:5.2f} {blend['final']:7.3f}  {note}")
        if comp["hp_flags"]:
            print(f"{'':16} hp_flags={comp['hp_flags']}")


if __name__ == "__main__":
    main()
