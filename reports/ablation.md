# Ablation: does each check have cases that catch it?

Reference agent with one check switched off. Cases are constructed test data.

| Check switched off | Cases passed | Cases with a critical error | Cases that caught it |
|---|---|---|---|
| Job check (symptom to job type, one job per problem) | 23 of 25 | 0 | 9 (E1); 11 (E1) |
| Fee check (membership by address and status) | 22 of 25 | 0 | 10 (E2); 13 (E2); 17 (E2) |
| Area check (ZIP on the unit's list, ask once for a missing address) | 23 of 25 | 2 | 14 (E1, E3); 23 (E3) |
| Slot check (routine windows only, move instead of duplicate) | 6 of 25 | 0 | 1 (E4); 2 (E4); 3 (E4); 4 (E4); 5 (E4); 6 (E4); 7 (E4); 8 (E4); 9 (E4); 10 (E4); 11 (E4); 12 (E4); 13 (E4); 14 (E4); 16 (E4); 17 (E4); 18 (E4); 19 (E4); 20 (E4) |
| Hand-off rule (safety, commercial, billing) | 22 of 25 | 3 | 22 (E5); 24 (E5); 25 (E5) |
