"""Run the 25-case booking eval: python run_eval.py --agent naive|spec|claude --runs 3

A case passes only if it passes on every run. Gate: 24 of 25 cases on all three runs with zero
critical errors (E3, E5), with T1-T2 at 15 of 16 or better, T3 5 of 5, and T4 4 of 4.
Writes reports/<agent>_report.md and reports/<agent>_results.json.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from harness import fsm as F
from harness.grader import CRITICAL, grade

ERR_NAMES = {"E1": "Wrong job type, business unit, or campaign", "E2": "Wrong fee, membership, or billing contact",
             "E3": "Outside the service area or wrong market", "E4": "Wrong slot or priority, or duplicate",
             "E5": "Should have handed off and did not", "E6": "Flagged or handed off a clean booking"}


def get_agent(name):
    if name == "claude":
        from harness.claude_agent import ClaudeAgent
        return ClaudeAgent()
    from harness.agents import AGENTS
    return AGENTS[name]()


def run(agent_name, runs):
    agent, fsm, cases = get_agent(agent_name), F.load_fsm(), F.load_cases()
    results = []
    for c in cases:
        cf = F.fsm_for_case(fsm, c)
        per_run = []
        for _ in range(runs):
            p = agent.propose(c, cf)
            per_run.append({"proposal": p, "errors": grade(c, p, cf)})
        codes = sorted({e[0] for r in per_run for e in r["errors"]})
        results.append({"id": c["id"], "tier": c["tier"], "passed": all(not r["errors"] for r in per_run),
                        "runs_passed": sum(not r["errors"] for r in per_run), "codes": codes,
                        "first_error": next((e[1] for r in per_run for e in r["errors"]), ""), "runs": per_run})
    return results


def summarize(results):
    tier = lambda ts: [r for r in results if r["tier"] in ts]
    passed = lambda rs: sum(r["passed"] for r in rs)
    s = {"total": passed(results), "t12": passed(tier({"T1", "T2"})), "t3": passed(tier({"T3"})),
         "t4": passed(tier({"T4"})), "critical": sum(1 for r in results if CRITICAL & set(r["codes"]))}
    s["gate"] = s["total"] >= 24 and s["t12"] >= 15 and s["t3"] == 5 and s["t4"] == 4 and s["critical"] == 0
    s["errors"] = Counter(code for r in results for code in r["codes"])
    return s


def report(agent_name, runs, results, s):
    L = [f"# Booking eval report: {agent_name} agent", "",
         f"Cases are constructed test data, not Hoffmann Brothers or Netic data. Each case ran {runs} times and passes only if every run passes.", "",
         f"**Gate: {'PASS' if s['gate'] else 'FAIL'}.** {s['total']} of 25 cases passed; T1-T2 {s['t12']} of 16, T3 {s['t3']} of 5, T4 {s['t4']} of 4; "
         f"{s['critical']} case(s) with a critical error.", "",
         "| Error type | Cases |", "|---|---|"]
    L += [f"| {k} {ERR_NAMES[k]}{' (critical)' if k in CRITICAL else ''} | {s['errors'].get(k, 0)} |" for k in sorted(ERR_NAMES)]
    L += ["", "| # | Tier | Result | Runs passed | Errors | First failure |", "|---|---|---|---|---|---|"]
    L += [f"| {r['id']} | {r['tier']} | {'PASS' if r['passed'] else 'FAIL'} | {r['runs_passed']}/{runs} | {', '.join(r['codes'])} | {r['first_error']} |" for r in results]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--agent", default="spec", choices=["naive", "spec", "claude"])
    ap.add_argument("--runs", type=int, default=3)
    a = ap.parse_args()
    res = run(a.agent, a.runs)
    s = summarize(res)
    out = Path(__file__).resolve().parent / "reports"
    out.mkdir(exist_ok=True)
    (out / f"{a.agent}_report.md").write_text(report(a.agent, a.runs, res, s))
    (out / f"{a.agent}_results.json").write_text(json.dumps({"summary": {**s, "errors": dict(s["errors"])}, "cases": res}, indent=1))
    print(f"{a.agent}: {s['total']}/25 passed, T1-T2 {s['t12']}/16, T3 {s['t3']}/5, T4 {s['t4']}/4, critical {s['critical']}, gate {'PASS' if s['gate'] else 'FAIL'}")
