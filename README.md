# Booking eval harness

A runnable version of the 25-case eval set in the booking-check spec (`Netic_Hoffmann_Booking_Check.pdf`), which defines what a correct booking is for one contractor and the gate an agent must pass before it books on its own. It scores a booking agent on the four checks in the spec (job, fee, area, slot) and on the hand-off rule, and it applies the same go-live gate.

All data here is constructed test data. The field service system is a mock shaped like a ServiceTitan account (business units with ZIP lists, a fee table, customers with memberships by location, open jobs, and capacity windows). The $49 member and $95 standard service fees come from Hoffmann Brothers' public Home Protection Plan page; everything else is invented. Nothing comes from Hoffmann Brothers' or Netic's systems.

## Run it

```
python3 run_eval.py --agent spec --runs 3     # reference agent
python3 run_eval.py --agent naive --runs 3    # "always book" agent
python3 ablation.py                           # switch off one check at a time
```

Python 3.9+ and the standard library only (3.10+ for the live-model agent below). Reports go to `reports/`.

To score a live model, install `anthropic` and `pydantic`, set `ANTHROPIC_API_KEY`, and run `python3 run_eval.py --agent claude --runs 3`. The model reads the raw transcript and a snapshot of the mock system and returns a structured proposal. Each case runs three times because a model's answers vary between runs, and a case passes only if it passes every run. This adapter has not been run (no API key where it was built), so there are no live-model results here.

## What is in it

| Path | What it is |
|---|---|
| `data/fsm_mock.json` | The mock field service system: fees ($95 standard, $49 member, $0 plan tune-up, no fee on estimates), 8 residential business units across three markets plus a commercial unit, 7 customers, and capacity windows (one emergency, six routine). |
| `data/cases.json` | 25 cases: a transcript, the facts a correct agent would extract, and the expected outcome. T1 clean bookings (8), T2 harder bookings (8), T3 book and flag (5), T4 do not book (4). |
| `harness/grader.py` | Grades one proposal and returns error codes E1 to E6. E3 (outside the service area) and E5 (should have handed off) are critical. |
| `harness/agents.py` | `SpecAgent`, a reference implementation of the spec, and `NaiveAgent`, which books the first open window from the caller's words. |
| `harness/claude_agent.py` | The live-model adapter. |
| `run_eval.py` | Runs an agent over the 25 cases and applies the gate. |
| `ablation.py` | Runs the reference agent with one check switched off at a time. |

The gate: 24 of 25 cases on all three runs, with zero critical errors, T1-T2 at 15 of 16 or better, T3 5 of 5, and T4 4 of 4.

## Results

| Agent | Cases passed | T1-T2 | T3 | T4 | Cases with a critical error | Gate |
|---|---|---|---|---|---|---|
| Reference (`spec`) | 25 of 25 | 16 of 16 | 5 of 5 | 4 of 4 | 0 | Pass |
| Always book (`naive`) | 5 of 25 | 5 of 16 | 0 of 5 | 0 of 4 | 7 | Fail |

How to read these. The reference agent reads the structured facts, not the transcript, so its 25 of 25 shows that the checks can be written as code and that the grader agrees with a correct policy. It is not a claim about a model. The naive agent shows what the grader catches when an agent books whatever it hears: wrong job types, member fees quoted from the wrong home, bookings outside the service area, and calls that should have gone to a person.

## Ablation

An eval set that still passes with a check switched off is not testing that check. With one check off, the reference agent fails these cases:

| Check switched off | Cases passed | Cases with a critical error | Cases that caught it |
|---|---|---|---|
| Job check | 23 of 25 | 0 | 9, 11 |
| Fee check | 22 of 25 | 0 | 10, 13, 17 |
| Area check | 23 of 25 | 2 | 14, 23 |
| Slot check | 6 of 25 | 0 | 19 cases |
| Hand-off rule | 22 of 25 | 3 | 22, 24, 25 |

Every check has at least two cases that catch it, and the area check and hand-off rule produce critical errors when they are off. The job and area checks are caught by only two cases each, which is the thinnest coverage and the first place to add cases. The slot ablation is blunt: with the check off, the agent takes the first open window, which is the emergency window, so almost every routine booking fails.

## Limits

- The cases are written by hand, and the expected outcomes encode one reading of the spec. A real version would be built from a contractor's own calls and reviewed with their dispatchers.
- The grader checks outcomes (job type, unit, fee, slot, flags, hand-offs). It does not grade what the agent said to the caller, apart from a flag the agent sets to say it gave the safety instruction on a gas call.
- Every case expects "Normal" priority and a routine window, so escalating urgent work into the emergency window is only tested in one direction (routine work must stay out of it). A contractor that escalates no-heat calls would need cases for that.
- Some expected outcomes are judgment calls. Case 11 (furnace caller, no hot water) expects a water heater job; a home with a boiler and an indirect water heater would make it an HVAC job, which a real version would settle with the contractor.
- 25 cases is a go-live gate for one contractor, not a benchmark. The daily health check in the spec covers what the cases cannot.
