# Booking eval report: naive agent

Cases are constructed test data, not Hoffmann Brothers or Netic data. Each case ran 3 times and passes only if every run passes.

**Gate: FAIL.** 5 of 25 cases passed; T1-T2 5 of 16, T3 0 of 5, T4 0 of 4; 7 case(s) with a critical error.

| Error type | Cases |
|---|---|
| E1 Wrong job type, business unit, or campaign | 7 |
| E2 Wrong fee, membership, or billing contact | 5 |
| E3 Outside the service area or wrong market (critical) | 4 |
| E4 Wrong slot or priority, or duplicate | 4 |
| E5 Should have handed off and did not (critical) | 3 |
| E6 Flagged or handed off a clean booking | 0 |

| # | Tier | Result | Runs passed | Errors | First failure |
|---|---|---|---|---|---|
| 1 | T1 | PASS | 3/3 |  |  |
| 2 | T1 | PASS | 3/3 |  |  |
| 3 | T1 | FAIL | 0/3 | E1, E3 | STL-PLUMB does not cover ZIP 37209 |
| 4 | T1 | FAIL | 0/3 | E1, E3 | STL-PLUMB does not cover ZIP 62269 |
| 5 | T1 | PASS | 3/3 |  |  |
| 6 | T1 | PASS | 3/3 |  |  |
| 7 | T1 | FAIL | 0/3 | E1 | campaign None instead of Angi |
| 8 | T1 | FAIL | 0/3 | E4 | created a new job instead of moving the existing one (duplicate) |
| 9 | T2 | FAIL | 0/3 | E1 | 1 job(s) booked, expected 2 |
| 10 | T2 | FAIL | 0/3 | E2 | quoted fee 95 instead of 49 |
| 11 | T2 | FAIL | 0/3 | E1 | missing Repair - Water Heater in STL-PLUMB; got [('Repair - Furnace', 'STL-HVAC')] |
| 12 | T2 | FAIL | 0/3 | E4 | slot D0-EVE instead of D1-AM |
| 13 | T2 | FAIL | 0/3 | E2 | quoted fee 49 instead of 95 |
| 14 | T2 | FAIL | 0/3 | E1, E3 | booked without asking for the missing address |
| 15 | T2 | FAIL | 0/3 | E4 | slot D1-AM instead of D2-PM |
| 16 | T2 | PASS | 3/3 |  |  |
| 17 | T3 | FAIL | 0/3 | E2 | quoted fee 49 instead of 95 |
| 18 | T3 | FAIL | 0/3 | E1 | missing Diagnostic - Heating in STL-HVAC; got [('Repair - AC', 'STL-HVAC')] |
| 19 | T3 | FAIL | 0/3 | E2 | missing 'billing' flag for the CSR queue |
| 20 | T3 | FAIL | 0/3 | E2 | missing 'promotion' flag for the CSR queue |
| 21 | T3 | FAIL | 0/3 | E4 | missing 'priority' flag for the CSR queue |
| 22 | T4 | FAIL | 0/3 | E5 | booked a case that should be 'handoff' |
| 23 | T4 | FAIL | 0/3 | E3 | booked a case that should be 'decline' |
| 24 | T4 | FAIL | 0/3 | E5 | booked a case that should be 'handoff' |
| 25 | T4 | FAIL | 0/3 | E5 | booked a case that should be 'handoff' |
