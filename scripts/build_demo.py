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
    rows.append(f"""<tr id="case-{c['id']}" data-tier="{c['tier']}">
<td class="n">{c['id']}</td><td><span class="tag">{c['tier']}</span></td>
<td class="tx">“{escape(c['transcript'])}”<div class="ch">{escape(c.get('channel', ''))}</div></td>
<td>{escape(expected_text(c['expected']))}</td>
<td class="v{' ok' if sp else ' bad'}">{'Pass' if sp else 'Fail'}</td>
<td class="v{' ok' if np_ else ' bad'}{' crit' if crit else ''}">{'Pass' if np_ else 'Fail · ' + ', '.join(ncodes) + (' (critical)' if crit else '')}{'' if np_ else f'<div class="why">{escape(nerr)}</div>'}</td></tr>""")


def s(r):
    return r["summary"]


case_ids = [c["id"] for c in cases]
tier_of = {c["id"]: c["tier"] for c in cases}


def cell_state(res, cid):
    ok, codes, _ = verdict(res, cid)
    if ok:
        return "pass", "passed"
    return ("crit", "failed with a critical error") if set(codes) & CRITICAL else ("fail", "failed")


def strip(states, label_prefix):
    """One square per case, in case order: the page's shared picture of a run."""
    cells = []
    for cid, (st, words) in zip(case_ids, states):
        cells.append(f'<a class="cell {st}" href="#case-{cid}" data-case="{cid}" '
                     f'aria-label="{label_prefix} case {cid} ({tier_of[cid]}) {words}"></a>')
    return f'<div class="strip" role="group" aria-label="{label_prefix}: every case">{"".join(cells)}</div>'


def verdict_row(name, sub, r):
    m = s(r)
    states = [cell_state(r, cid) for cid in case_ids]
    gate = "GO" if m["gate"] else "NO-GO"
    return f"""<div class="vrow">
  <div class="vwho"><b>{name}</b><span>{sub}</span></div>
  {strip(states, name)}
  <div class="vscore"><b>{m['total']}</b><span>of 25 passed<br>{m['critical']} critical</span></div>
  <span class="gate {'go' if m['gate'] else 'nogo'}">{gate}</span>
</div>"""


def tier_counts(r):
    m = s(r)
    return {"T1–T2": (m["t12"], 16), "T3": (m["t3"], 5), "T4": (m["t4"], 4)}


abl_rows = []
for label, passed, crit, failed in abl:
    states = [("fail", "caught it") if cid in failed else ("pass", "still passed") for cid in case_ids]
    caught = ", ".join(map(str, failed)) if len(failed) <= 6 else f"{len(failed)} cases"
    abl_rows.append(f"""<div class="arow">
  <div class="awho"><b>{label} off</b><span>caught by {caught}</span></div>
  {strip(states, label + ' off')}
  <div class="ascore"><b>{passed}</b>/25<span>{crit} critical</span></div>
</div>""")

err_rows = "".join(f"<tr><td class='n'>{c}</td><td>{d}</td><td><span class='sev sev-{sev.lower()}'>{sev}</span></td></tr>" for c, d, sev in ERRORS)
tier_btns = "".join(f'<button type="button" role="radio" aria-checked="false" data-t="{t}">{t}&nbsp; <span>{n}</span></button>' for t, n in TIERS.items())

CSS = """
.head{padding:8px 0 0}
.head h1{margin:40px 0 14px}
.head .lead{max-width:38em}
/* verdict: the same 25 cases under the same gate, one square per case */
.verdict{margin:36px 0 0;border:1px solid var(--rule);border-radius:16px;background:#fbfaf6;overflow:hidden}
.vhead{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:8px 24px;padding:18px 24px;border-bottom:1px solid var(--rule)}
.vhead h2{all:unset;font:400 22px/1.2 var(--serif)}
.vhead p{margin:0;color:var(--ink-2);font-size:15px}
.vhead p b{color:var(--ink)}
.vrow,.arow{display:grid;grid-template-columns:minmax(0,15em) minmax(0,1fr) 7.5em 5.5em;align-items:center;gap:20px;padding:22px 24px}
.vrow+.vrow{border-top:1px solid var(--rule-soft)}
.vwho b,.awho b{display:block;font:400 20px/1.2 var(--serif)}
.vwho span,.awho span{display:block;color:var(--ink-2);font-size:14px;line-height:1.4;margin-top:4px}
.strip{display:grid;grid-template-columns:repeat(25,minmax(0,1fr));gap:4px}
.cell{display:block;aspect-ratio:1;border-radius:4px;border:1.5px solid transparent;transition:transform .2s var(--ease),box-shadow .2s}
.cell.pass{background:var(--green)}
.cell.fail{background:var(--paper);border-color:var(--ink)}
.cell.crit{background:var(--ink)}
.cell:hover,.cell:focus-visible,.cell.lit{transform:translateY(-3px);box-shadow:0 6px 12px -6px rgb(27 26 23/.5)}
.vscore b{font:400 44px/1 var(--serif)}
.vscore span{display:block;color:var(--ink-2);font-size:13px;line-height:1.35;margin-top:4px}
.gate{justify-self:end;display:inline-flex;align-items:center;justify-content:center;min-height:32px;padding:0 14px;border-radius:999px;font:500 13px/1 var(--mono);letter-spacing:.06em}
.gate.go{background:var(--green-wash);color:var(--green)}
.gate.nogo{background:var(--ink);color:var(--paper)}
.legend{display:flex;flex-wrap:wrap;gap:6px 20px;padding:14px 24px;border-top:1px solid var(--rule);color:var(--ink-2);font-size:13px}
.legend span{display:inline-flex;align-items:center;gap:8px}
.legend i{width:12px;height:12px;border-radius:3px;border:1.5px solid transparent}
.legend .pass{background:var(--green)}.legend .fail{border-color:var(--ink)}.legend .crit{background:var(--ink)}
/* page body: content and a side column */
.layout{display:grid;grid-template-columns:minmax(0,1fr) 270px;gap:56px;align-items:start;margin-top:8px}
.side{position:sticky;top:24px;margin-top:64px;display:grid;gap:22px;font-size:14px;color:var(--ink-2)}
.side h3{margin:0 0 6px;font:500 13px/1.3 var(--sans);color:var(--ink)}
.side p{margin:0}
.side nav a{display:block;padding:5px 0;color:var(--ink-2);text-decoration:none;border-bottom:1px solid var(--rule-soft)}
.side nav a:hover{color:var(--ink)}
.side pre{font-size:12px;margin:6px 0 0}
.point{font-size:17px;max-width:40em;margin:0}
.point b{font-weight:500}
.seg{display:flex;width:fit-content;max-width:100%;flex-wrap:wrap;gap:2px;padding:3px;border:1px solid var(--rule);border-radius:999px;margin:0 0 16px;background:#fbfaf6}
.seg button{min-height:34px;padding:0 14px;border:0;border-radius:999px;background:transparent;color:var(--ink-2);font:500 14px/1 var(--sans);cursor:pointer}
.seg button span{font-weight:400;opacity:.8}
.seg button[aria-checked=true]{background:var(--ink);color:var(--paper)}
.n{font-family:var(--mono);font-size:13px}
.tag{font:400 12px/1 var(--mono);border:1px solid var(--rule);border-radius:999px;padding:4px 8px;white-space:nowrap}
.tx{max-width:340px}.ch{font-size:13px;color:var(--ink-2);margin-top:4px}
.v{white-space:nowrap;font-weight:500}
.v.ok{color:var(--green)}
.v.bad{white-space:normal;color:var(--ink)}
.v.bad.crit::before{content:"";display:inline-block;width:8px;height:8px;border-radius:2px;background:var(--ink);margin-right:6px;vertical-align:1px}
.why{font-weight:400;font-size:13px;color:var(--ink-2);margin-top:4px;max-width:240px}
#cases tr.lit td{background:var(--green-wash)}
#cases tr{scroll-margin-top:24px}
.abl{border:1px solid var(--rule);border-radius:16px;background:#fbfaf6;overflow:hidden}
.arow{grid-template-columns:minmax(0,13em) minmax(0,1fr) 6.5em}
.arow+.arow{border-top:1px solid var(--rule-soft)}
.ascore{font:400 15px/1 var(--sans);color:var(--ink-2)}
.ascore b{font:400 30px/1 var(--serif);color:var(--ink)}
.ascore span{display:block;font-size:13px;margin-top:4px}
.note{color:var(--ink-2);font-size:15px;max-width:44em;margin-top:14px}
.rule{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.rule div{border:1px solid var(--rule);border-radius:16px;padding:20px 22px;background:#fbfaf6}
.rule div:last-child{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.rule h3{margin:0 0 6px;font:400 22px/1.2 var(--serif)}
.rule p{margin:0 0 10px;font-size:15px;opacity:.85}
.rule ul{margin:0;font-size:15px}
.rule div:last-child li::marker{color:rgb(244 242 236/.6)}
.sev{font:500 12px/1 var(--mono);padding:4px 8px;border-radius:999px;border:1px solid var(--rule)}
.sev-critical{background:var(--ink);color:var(--paper);border-color:var(--ink)}
.sev-low{color:var(--ink-2)}
@media (max-width:1000px){
 .layout{grid-template-columns:minmax(0,1fr);gap:0}
 .side{position:static;margin-top:48px;order:2}
 .vrow{grid-template-columns:minmax(0,1fr) auto;gap:14px 16px}
 .vrow .strip{grid-column:1/-1;grid-row:2}
 .vscore{grid-row:3}.vrow .gate{grid-row:3}
 .arow{grid-template-columns:minmax(0,1fr) auto;gap:12px 16px}
 .arow .strip{grid-column:1/-1;grid-row:2}
 .ascore{grid-column:2;grid-row:1}
 .rule{grid-template-columns:1fr}
}
@media (max-width:640px){.vrow,.arow{padding:18px}.vhead{padding:16px 18px}.strip{gap:3px}.tx{max-width:none}}
@media (prefers-reduced-motion:reduce){.cell{transition:none}}
"""

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Booking Eval Harness</title>
<meta name="description" content="A 25-case eval and go-live gate for an AI agent that books field-service jobs: the reference agent passes 25 of 25, the naive agent 5 of 25.">
<style>{CSS}</style></head><body><main>
<div class="head">
<h1>Booking Eval Harness</h1>
<p class="lead">A runnable 25-case eval for an AI booking agent at a home services contractor. It checks that every AI-booked job lands with the right job type, fee, service area and slot, and that the agent hands off the calls it should never book.</p>
</div>

<section class="verdict" aria-labelledby="verdict-h">
  <div class="vhead"><h2 id="verdict-h">Same 25 calls, same gate</h2><p>Gate: <b>24 of 25</b> on all three runs, <b>zero</b> critical errors</p></div>
  {verdict_row("Reference agent", "The spec's four checks and hand-off rule, written as code", spec)}
  {verdict_row("Naive agent", "Books the first open window from the caller's words", naive)}
  <div class="legend"><span><i class="pass"></i>Passed</span><span><i class="fail"></i>Failed</span><span><i class="crit"></i>Critical error</span><span>Each square is one call. Select one to read it.</span></div>
</section>

<div class="layout">
<div class="content">

<h2 id="point">Why the gate exists</h2>
<p class="point">A booking counts as a win even when a detail is wrong: a plan member quoted the $95 standard fee instead of the $49 member fee is still a "booking." This harness defines what a correct booking is for one contractor, and the gate an agent must pass before it books on its own.</p>
<p class="note">The reference agent reads structured facts, not the raw transcript, so its 25 of 25 shows the checks can be written as code and the grader agrees with a correct policy. It is not a claim about a model. The naive agent shows what the grader catches. A live-model adapter is included but has not been run.</p>

<h2 id="every-case">Every call</h2>
<div class="seg" role="radiogroup" aria-label="Filter by tier"><button type="button" role="radio" aria-checked="true" data-t="all">All&nbsp; <span>25</span></button>{tier_btns}</div>
<div class="scroll"><table class="t" id="cases"><thead><tr><th>#</th><th>Tier</th><th>What the caller said</th><th>Correct outcome</th><th>Reference</th><th>Naive</th></tr></thead><tbody>
{''.join(rows)}
</tbody></table></div>

<h2 id="coverage">Does every check get caught?</h2>
<p class="note" style="margin:0 0 16px">An eval set that still passes with a check switched off is not testing that check. The reference agent runs again with one check off at a time; an outlined square is a call that caught it.</p>
<div class="abl">{''.join(abl_rows)}</div>
<p class="note">The job and area checks are caught by only two calls each, the thinnest coverage and the first place to add cases. With the slot check off, the agent takes the first open window, which is the emergency window, so almost every routine booking fails.</p>

<h2 id="unsure">When a check is unsure</h2>
<div class="rule">
  <div><h3>Book and flag</h3><p>A CSR can fix it before the technician leaves.</p><ul><li>A lapsed membership</li><li>An unclear job type</li><li>An unconfirmed promotion</li></ul></div>
  <div><h3>Do not book, hand off</h3><p>It cannot be fixed later.</p><ul><li>An out-of-area address</li><li>A gas smell</li><li>A commercial job</li><li>A billing dispute</li></ul></div>
</div>
<p class="note">Stopping a booking costs the job, especially after hours; booking the wrong one costs a truck roll or a safety risk.</p>

<h2 id="errors">Error codes</h2>
<div class="scroll"><table class="t"><thead><tr><th>Code</th><th>What went wrong</th><th>Severity</th></tr></thead><tbody>{err_rows}</tbody></table></div>
</div>

<aside class="side" aria-label="About this build">
  <nav aria-label="On this page"><a href="#point">Why the gate exists</a><a href="#every-case">Every call</a><a href="#coverage">Check coverage</a><a href="#unsure">When a check is unsure</a><a href="#errors">Error codes</a></nav>
  <div><h3>Data</h3><p>Constructed test calls, not real customer data. The $49 and $95 fees come from a contractor's public Home Protection Plan page; everything else is invented.</p></div>
  <div><h3>Run it yourself</h3><p>Python 3.9+, standard library only.</p><pre>python3 run_eval.py --agent spec --runs 3
python3 run_eval.py --agent naive --runs 3
python3 ablation.py</pre></div>
  <div><a class="pill" href="https://github.com/pg2342-hub/booking-eval-harness">Code on GitHub</a></div>
</aside>
</div>
</main>
<script>
const seg=[...document.querySelectorAll('.seg button')];
seg.forEach(b=>b.addEventListener('click',()=>{{
 seg.forEach(x=>x.setAttribute('aria-checked',String(x===b)));
 const t=b.dataset.t;document.querySelectorAll('#cases tbody tr').forEach(r=>r.hidden=!(t==='all'||r.dataset.tier===t));
}}));
document.querySelectorAll('.cell').forEach(c=>{{
 const id=c.dataset.case;
 const lit=on=>document.querySelectorAll(`.cell[data-case="${{id}}"]`).forEach(x=>x.classList.toggle('lit',on));
 c.addEventListener('mouseenter',()=>lit(true));c.addEventListener('mouseleave',()=>lit(false));
 c.addEventListener('click',()=>{{
  seg[0].click();
  const row=document.getElementById('case-'+id);
  document.querySelectorAll('#cases tr.lit').forEach(r=>r.classList.remove('lit'));
  row&&row.classList.add('lit');
 }});
}});
</script></body></html>
"""
out = ROOT / "docs"
out.mkdir(exist_ok=True)
(out / "index.html").write_text(html)
subprocess.run([sys.executable, str(ROOT / "scripts" / "demo_chrome.py"), str(out / "index.html"), "--repo", "booking-eval-harness"], check=True)
(out / ".nojekyll").write_text("")
print("wrote docs/index.html")
