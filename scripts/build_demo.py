"""Build the GitHub Pages demo (docs/index.html) from the cases and the latest reports.
python3 scripts/build_demo.py   (run run_eval.py for both agents first)"""
import subprocess
import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from harness import fsm as F  # noqa: E402
from harness.agents import SpecAgent  # noqa: E402
from harness.grader import CRITICAL, grade  # noqa: E402

cases = json.loads((ROOT / "data/cases.json").read_text())
spec = json.loads((ROOT / "reports/spec_results.json").read_text())
naive = json.loads((ROOT / "reports/naive_results.json").read_text())

TIERS = {"T1": "Clean booking", "T2": "Messy but bookable", "T3": "Book and flag", "T4": "Do not book"}
ERRORS = [("E1", "Wrong job type, business unit, or campaign", "High"),
          ("E2", "Wrong fee, membership missed, or billing contact wrong", "High"),
          ("E3", "Booked outside the service area or in the wrong market", "Critical"),
          ("E4", "Wrong slot or priority, or a duplicate job", "High"),
          ("E5", "Should have handed off and did not", "Critical"),
          ("E6", "Flagged, refused, or handed off a job it could have booked", "Low")]
CHECKS = {"job": "Job check", "fee": "Fee check", "area": "Area check", "slot": "Slot check", "handoff": "Hand-off rule"}


HANDOFF = {"CSR": "a CSR", "COMM": "the commercial team"}


def expected_text(e):
    a = e["action"]
    if a == "reschedule":
        return "Move the existing job to the new day; do not create a new job"
    if a in ("book", "book_flag"):
        parts = []
        for j in e.get("jobs", []) or []:
            fee = j.get("fee")
            parts.append(f"{j['job_type']} in {j['business_unit']}, " + (f"${fee} fee" if fee else "no fee"))
        txt = ("Book and flag for a CSR: " if a == "book_flag" else "Book: ") + "; ".join(parts)
        if e.get("flags"):
            txt += " (flag: " + ", ".join(f.replace("_", " ") for f in e["flags"]) + ")"
        return txt
    if a == "handoff":
        txt = f"Do not book; hand off to {HANDOFF.get(e.get('handoff_to'), e.get('handoff_to'))}"
        if e.get("safety_instruction"):
            txt = "Give the safety instruction; " + txt[0].lower() + txt[1:]
        return txt
    return "Do not book; tell the caller the area is not served"


def verdict(res, cid):
    c = next(x for x in res["cases"] if x["id"] == cid)
    return c["passed"], c["codes"], c["first_error"]


fsm = F.load_fsm()
abl = []
for key, label in CHECKS.items():
    agent = SpecAgent(disable={key})
    failed, crit = [], 0
    for c in cases:
        cf = F.fsm_for_case(fsm, c)
        codes = {e[0] for e in grade(c, agent.propose(c, cf), cf)}
        if codes:
            failed.append(c["id"])
            crit += bool(CRITICAL & codes)
    abl.append((label, 25 - len(failed), crit, failed))

rows = []
for c in cases:
    sp, _, _ = verdict(spec, c["id"])
    np_, ncodes, nerr = verdict(naive, c["id"])
    crit = bool(set(ncodes) & CRITICAL)
    rows.append(f"""<tr data-tier="{c['tier']}">
<td class="n">{c['id']}</td><td><span class="tag">{c['tier']}</span></td>
<td class="tx">“{escape(c['transcript'])}”<div class="ch">{escape(c.get('channel', ''))}</div></td>
<td>{escape(expected_text(c['expected']))}</td>
<td class="v">{'Pass' if sp else 'Fail'}</td>
<td class="v{' bad' if not np_ else ''}">{'Pass' if np_ else 'Fail · ' + ', '.join(ncodes) + (' (critical)' if crit else '')}{'' if np_ else f'<div class="why">{escape(nerr)}</div>'}</td></tr>""")


def s(r):
    return r["summary"]


def card(name, sub, r):
    m = s(r)
    return f"""<div class="card"><div class="k">{name}</div><div class="sub">{sub}</div>
<div class="big">{m['total']} <span>of 25</span></div>
<table class="mini"><tr><td>Clean and messy bookings (T1–T2)</td><td>{m['t12']} of 16</td></tr>
<tr><td>Book and flag (T3)</td><td>{m['t3']} of 5</td></tr><tr><td>Do not book (T4)</td><td>{m['t4']} of 4</td></tr>
<tr><td>Cases with a critical error</td><td>{m['critical']}</td></tr></table>
<div class="gate {'pass' if m['gate'] else 'fail'}">Gate: {'PASS' if m['gate'] else 'FAIL'}</div></div>"""


abl_rows = "".join(f"<tr><td>{l}</td><td>{p} of 25</td><td>{cr}</td><td>{', '.join(map(str, f)) if len(f) <= 6 else f'{len(f)} cases'}</td></tr>" for l, p, cr, f in abl)
err_rows = "".join(f"<tr><td><b>{c}</b></td><td>{d}</td><td>{sev}</td></tr>" for c, d, sev in ERRORS)
tier_btns = "".join(f'<button data-t="{t}">{t} · {n}</button>' for t, n in TIERS.items())

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Booking Eval Harness</title>
<style>
.point{{border-left:2px solid var(--green);padding:4px 0 4px 18px;margin:32px 0 0;max-width:46em;font-size:17px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}}
.card{{margin:0}}.k{{font:400 22px/1.2 var(--serif)}}.sub{{color:var(--ink-2);font-size:14px;margin-top:4px}}
.big{{font:400 56px/1 var(--serif);margin:18px 0 14px}}.big span{{font:400 15px/1 var(--sans);color:var(--ink-2)}}
.mini{{font-size:14px}}.mini td{{padding:8px 0;border-bottom:1px solid var(--rule)}}.mini td:last-child{{text-align:right}}
.gate{{margin-top:16px;display:inline-flex;align-items:center;min-height:28px;padding:0 12px;border-radius:999px;
font:500 13px/1 var(--mono);letter-spacing:.04em}}.gate.pass{{background:var(--green-wash);color:var(--green)}}
.gate.fail{{background:var(--ink);color:var(--paper)}}
.n{{font-family:var(--mono);font-size:13px}}.tag{{font:400 12px/1 var(--mono);border:1px solid var(--rule);border-radius:999px;padding:4px 8px;white-space:nowrap}}
.tx{{max-width:360px}}.ch{{font-size:13px;color:var(--ink-2);margin-top:4px}}.v{{white-space:nowrap;font-weight:500;color:var(--green)}}
.v.bad{{white-space:normal;color:var(--ink)}}.why{{font-weight:400;font-size:13px;color:var(--ink-2);margin-top:4px;max-width:240px}}
.filters{{margin:16px 0 18px;display:flex;flex-wrap:wrap;gap:8px}}.filters button{{min-height:36px;font-size:14px}}
.filters button.on{{background:var(--green);border-color:var(--green);color:#fff}}
.note{{color:var(--ink-2);font-size:15px;max-width:46em;margin-top:14px}}
@media (max-width:640px){{.tx{{max-width:none}}.big{{font-size:46px}}}}
</style></head><body><main>
<h1>Booking Eval Harness</h1>
<p class="lead">A runnable 25-case eval for an AI booking agent at a home services contractor. It checks that every AI-booked job lands with the right job type, fee, service area and slot, and that the agent hands off the calls it should never book.</p>

<div class="point"><b>The point.</b> A booking counts as a win even when a detail is wrong: a plan member quoted the $95 standard fee instead of the $49 member fee is still a "booking." This harness defines what a correct booking is for one contractor and the gate an agent must pass before it books on its own: <b>24 of 25 cases on all three runs, with zero critical errors.</b></div>

<h2>Results</h2>
<div class="cards">
{card("Reference agent", "A direct implementation of the spec's four checks and hand-off rule", spec)}
{card("Naive agent", "Books the first open window from the caller's words", naive)}
</div>
<p class="note">The reference agent reads structured facts, not the raw transcript, so its 25 of 25 shows the checks can be written as code and the grader agrees with a correct policy. It is not a claim about a model. The naive agent shows what the grader catches. A live-model adapter is included but has not been run.</p>

<h2>Every case</h2>
<p class="note">Constructed test calls, not real customer data. The $49 and $95 fees come from Hoffmann Brothers' public Home Protection Plan page; everything else is invented.</p>
<div class="filters"><button data-t="all" class="on">All 25</button>{tier_btns}</div>
<div class="scroll"><table class="t" id="cases"><thead><tr><th>#</th><th>Tier</th><th>What the caller said</th><th>Correct outcome</th><th>Reference</th><th>Naive</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table></div>

<h2>Does each check have cases that catch it?</h2>
<p class="note">An eval set that still passes with a check switched off is not testing that check. Here the reference agent runs with one check off at a time.</p>
<div class="scroll"><table class="t"><thead><tr><th>Check switched off</th><th>Cases passed</th><th>Cases with a critical error</th><th>Cases that caught it</th></tr></thead><tbody>{abl_rows}</tbody></table></div>
<p class="note">The job and area checks are caught by only two cases each, the thinnest coverage and the first place to add cases. With the slot check off, the agent takes the first open window, which is the emergency window, so almost every routine booking fails.</p>

<h2>Error types</h2>
<div class="scroll"><table class="t"><thead><tr><th>Code</th><th>What went wrong</th><th>Severity</th></tr></thead><tbody>{err_rows}</tbody></table></div>

<h2>The rule when a check is unsure</h2>
<p>Book and flag when a CSR can fix the error before the technician leaves (a lapsed membership, an unclear job type, an unconfirmed promotion). Do not book, and hand off, when it cannot be fixed later (an out-of-area address, a gas smell, a commercial job, a billing dispute). Stopping a booking costs the job, especially after hours; booking the wrong one costs a truck roll or a safety risk.</p>

<h2>Run it yourself</h2>
<pre>python3 run_eval.py --agent spec --runs 3
python3 run_eval.py --agent naive --runs 3
python3 ablation.py</pre>
<p class="note">Python 3.9+ and the standard library only. Built by Pranav Gudise from public information only; not affiliated with Netic, Hoffmann Brothers, or ServiceTitan.</p>
</main>
<script>
document.querySelectorAll('.filters button').forEach(b=>b.addEventListener('click',()=>{{
 document.querySelectorAll('.filters button').forEach(x=>x.classList.toggle('on',x===b));
 const t=b.dataset.t;document.querySelectorAll('#cases tbody tr').forEach(r=>r.style.display=(t==='all'||r.dataset.tier===t)?'':'none');
}}));
</script></body></html>
"""
out = ROOT / "docs"
out.mkdir(exist_ok=True)
(out / "index.html").write_text(html)
subprocess.run([sys.executable, str(ROOT / "scripts" / "demo_chrome.py"), str(out / "index.html"), "--repo", "booking-eval-harness"], check=True)
(out / ".nojekyll").write_text("")
print("wrote docs/index.html")
