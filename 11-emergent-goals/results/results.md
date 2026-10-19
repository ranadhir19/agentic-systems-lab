# Emergent Goals — Results

Seeds: [11, 22, 33, 44, 55, 66]; 10 agents; 1500 steps/episode; means +- SD across seeds.

## Per-condition means

| Metric | full | no-comm | extrinsic-only | no-goalgen |
|---|---|---|---|---|
| Self-generated goals | 49.500 +- 27.645 | 34.500 +- 13.913 | 0.000 +- 0.000 | 0.000 +- 0.000 |
| Goal adoption rate | 0.823 +- 0.103 | 0.780 +- 0.065 | 0.000 +- 0.000 | 0.000 +- 0.000 |
| Goal diversity (distinct cells) | 18.833 +- 9.191 | 33.667 +- 12.906 | 0.000 +- 0.000 | 0.000 +- 0.000 |
| Goal diversity (mean pairwise dist) | 14.592 +- 2.589 | 18.799 +- 0.487 | 0.000 +- 0.000 | 0.000 +- 0.000 |
| Tokens / 100 agent-steps | 4.198 +- 1.080 | 0.000 +- 0.000 | 5.745 +- 0.062 | 4.876 +- 0.374 |
| Mean neighbours (overall) | 2.884 +- 0.902 | 1.535 +- 0.401 | 2.716 +- 0.459 | 2.282 +- 0.271 |
| Mean neighbours (away from sources) | 2.770 +- 1.017 | 1.565 +- 0.420 | 3.204 +- 0.596 | 2.325 +- 0.291 |
| Cache ratio (withheld / collected) | 0.042 +- 0.035 | 0.031 +- 0.005 | 0.092 +- 0.073 | 0.013 +- 0.006 |
| Mean lifetime (steps) | 413.233 +- 282.743 | 319.583 +- 107.603 | 1185.150 +- 166.934 | 374.133 +- 116.606 |
| Deposits (extrinsic return) | 30.500 +- 15.628 | 70.333 +- 6.700 | 87.667 +- 9.177 | 124.500 +- 3.253 |
| Comm->goal lift (20-step window) | 1.175 +- 0.131 | n/a | n/a | n/a |
| Social goal fraction | 0.869 +- 0.086 | 0.000 +- 0.000 | 0.000 +- 0.000 | 0.000 +- 0.000 |
| Token context entropy (nats) | 0.449 +- 0.063 | n/a | 0.708 +- 0.071 | 0.655 +- 0.066 |

## Effect sizes: full vs each ablation (Cohen's d)

| Metric | full vs no-comm | full vs extrinsic-only | full vs no-goalgen |
|---|---|---|---|
| Self-generated goals | +0.69 | +2.53 | +2.53 |
| Goal adoption rate | +0.50 | +11.30 | +11.30 |
| Goal diversity (distinct cells) | -1.32 | +2.90 | +2.90 |
| Goal diversity (mean pairwise dist) | -2.26 | +7.97 | +7.97 |
| Tokens / 100 agent-steps | +5.50 | -2.02 | -0.84 |
| Mean neighbours (overall) | +1.93 | +0.23 | +0.90 |
| Mean neighbours (away from sources) | +1.55 | -0.52 | +0.59 |
| Cache ratio (withheld / collected) | +0.43 | -0.87 | +1.17 |
| Mean lifetime (steps) | +0.44 | -3.32 | +0.18 |
| Deposits (extrinsic return) | -3.31 | -4.46 | -8.33 |
| Comm->goal lift (20-step window) | n/a | n/a | n/a |
| Social goal fraction | +14.22 | +14.22 | +14.22 |
| Token context entropy (nats) | n/a | -3.86 | -3.20 |

## Hypothesis verdicts

- H1 (comm catalyzes goal generation): full 49.5 vs no-comm 34.5, d=+0.69.
- H2 (continuity behaviors): link-away full 2.77 vs no-comm 1.57 (d=+1.55); cache full 0.042.
- H3 (comm-goal coupling): social goal fraction full 0.869; comm->goal lift 1.17.
- H4 (survival dividend): full 413 vs extrinsic-only 1185 steps (d=-3.32).
- H5 (sustained open-endedness): see saturation chart; predicted negative.

