"""Turn off one check at a time in the reference agent and show which cases catch it.
python ablation.py  ->  reports/ablation.md
An eval set that still passes with a check switched off is not testing that check."""
from pathlib import Path

from harness import fsm as F
from harness.agents import SpecAgent
from harness.grader import CRITICAL, grade

CHECKS = {"job": "Job check (symptom to job type, one job per problem)",
          "fee": "Fee check (membership by address and status)",
          "area": "Area check (ZIP on the unit's list, ask once for a missing address)",
          "slot": "Slot check (routine windows only, move instead of duplicate)",
          "handoff": "Hand-off rule (safety, commercial, billing)"}

fsm, cases = F.load_fsm(), F.load_cases()
rows = []
for key, label in CHECKS.items():
    agent = SpecAgent(disable={key})
    failed, crit = [], 0
    for c in cases:
        cf = F.fsm_for_case(fsm, c)
        errs = grade(c, agent.propose(c, cf), cf)
        if errs:
            failed.append(f"{c['id']} ({', '.join(sorted({e[0] for e in errs}))})")
            crit += bool(CRITICAL & {e[0] for e in errs})
    rows.append(f"| {label} | {25 - len(failed)} of 25 | {crit} | {'; '.join(failed)} |")
out = ["# Ablation: does each check have cases that catch it?", "",
       "Reference agent with one check switched off. Cases are constructed test data.", "",
       "| Check switched off | Cases passed | Cases with a critical error | Cases that caught it |", "|---|---|---|---|"] + rows
OUT = Path(__file__).resolve().parent / "reports"
OUT.mkdir(exist_ok=True)
(OUT / "ablation.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
