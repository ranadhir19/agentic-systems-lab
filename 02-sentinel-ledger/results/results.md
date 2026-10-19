# Sentinel experiment results

Clean replay: 600 decisions, 100.0% MATCH, 0.07 ms/decision.

| Fault injected | n | Detected |
|---|---|---|
| seed perturbed (+1) | 150 | 100.0% DIVERGED |
| tool result mutated | 150 | 100.0% DIVERGED (100% step-located) |
| seed stripped | 150 | 100.0% UNREPLAYABLE |
| ledger entry forged | 1 | detected at index 100 |

Chain verification is O(n):

| entries | verify ms |
|---|---|
| 100 | 1.4 |
| 500 | 6.7 |
| 1000 | 17.5 |
| 2000 | 25.9 |
| 4000 | 52.4 |
