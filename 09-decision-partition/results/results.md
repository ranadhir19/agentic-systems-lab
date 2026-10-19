# Decision-partition experiment results

All runs seeded and deterministic.

## A -- insurance reproduction (concept's worked example)

| Decision | Blocks | Weight | Score | Level | Agent |
|---|---|---|---|---|---|
| Identity validation | 3 | 1.0 | 3.0 | low | Intake Agent |
| Damage assessment | 5 | 2.0 | 10.0 | high | Damage Specialist |
| Policy rules compliance | 4 | 2.0 | 8.0 | medium | Compliance Agent |
| Fraud detection | 5 | 2.0 | 10.0 | high | Fraud Specialist |
| Final settlement | 4 | 1.0 | 4.0 | low | Intake Agent |

Agents: 4 (naive 1:1 would use 5); coordination channels 6 vs 10 naive.

## B -- synthetic scaling (mean of 5 seeds)

| Decisions | Naive agents | Partitioned agents | Reduction | Load std | Overhead (partitioned / naive) |
|---|---|---|---|---|---|
| 10 | 10 | 5.8 | 42.0% | 4.03 | 15.0 / 45.0 |
| 25 | 25 | 11.6 | 53.6% | 11.41 | 62.2 / 300.0 |
| 50 | 50 | 17.2 | 65.6% | 25.05 | 140.8 / 1225.0 |

## C -- sensitivity (assignment churn vs base partition)

Block-count sweep (mean churn over 12 decisions):

| Blocks | Churn |
|---|---|
| 2 | 0.403 |
| 3 | 0.375 |
| 4 | 0.375 |
| 5 | 0.257 |
| 6 | 0.215 |
| 7 | 0.215 |
| 8 | 0.299 |

Composite-weight sweep:

| Composite weight | Churn |
|---|---|
| 1.0 | 1.000 |
| 1.5 | 0.917 |
| 2.0 | 0.000 |
| 2.5 | 0.750 |
| 3.0 | 0.750 |

## D -- dynamic re-partition

| Step | Evidence | Scores (id/dmg/pol/frd/set) | Crossed | Triggers | Agents | Stability |
|---|---|---|---|---|---|---|
| 1 | Identity validation: +2 blocks | 5/10/8/10/4 | True | Identity validation: low->medium | 5 | 0.60 |
| 2 | Final settlement: +1 blocks | 5/10/8/10/5 | True | Final settlement: low->medium | 4 | 0.60 |
| 3 | Policy rules compliance: +3 blocks | 5/10/14/10/5 | True | Policy rules compliance: medium->high | 4 | 1.00 |
| 4 | Identity validation: -2 blocks | 3/10/14/10/5 | True | Identity validation: medium->low | 5 | 0.60 |
| 5 | Fraud detection: -1 blocks | 3/10/14/8/5 | True | Fraud detection: high->medium | 5 | 1.00 |

## E -- latency-aware scoring

| Latency weight | Agents | Churn vs base |
|---|---|---|
| 0.0 | 8 | 0.00 |
| 0.5 | 8 | 0.50 |
| 1.0 | 9 | 0.50 |
| 2.0 | 9 | 0.50 |
| 4.0 | 10 | 0.42 |
