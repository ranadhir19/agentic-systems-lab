# Attention Economics — results (seed 7, n=2000)

## (a) Policy comparison across cost regimes

| Regime | always-ask | never-ask | fixed-tau=0.70 | fixed-tau=0.90 | stakes-adjusted | budget-aware(B=200) |
|---|---|---|---|---|---|---|
| cheap attention (c_int=2, c_err=1) | 17,394 | 55,726 | 39,393 | 17,062 | **16,799** | 37,704 |
| expensive attention (c_int=20, c_err=1) | 53,394 | 55,726 | 45,027 | 43,648 | **33,797** | 41,304 |
| high stakes (c_int=5, c_err=3) | 50,183 | 167,177 | 117,867 | 49,709 | **48,326** | 112,912 |

The stakes-adjusted (expected-value) policy wins in every regime. Never-ask is catastrophic under high stakes; always-ask is wasteful when attention is expensive. Budget-aware with B=200 is competitive only when attention is expensive -- a hard budget is a blunt instrument compared to pricing each ask.

## (b) Optimal threshold vs theory (homogeneous stakes=100)

| c_int / (stakes x c_err) | naive theory | corrected theory | measured |
|---|---|---|---|
| 0.01 | 0.99 | 0.94 | 0.95 |
| 0.02 | 0.98 | 0.93 | 0.95 |
| 0.05 | 0.95 | 0.90 | 0.91 |
| 0.10 | 0.90 | 0.85 | 0.89 |
| 0.20 | 0.80 | 0.75 | 0.77 |
| 0.40 | 0.60 | 0.55 | 0.50 |

Measured optimal fixed thresholds track the *fallibility-corrected* theory tau* = h - c_int/(stakes x c_err) (h = 0.95 human accuracy) within 0.05 at every ratio. The naive textbook rule (perfect human, tau* = 1 - rho) is systematically ~0.05 too trusting -- it prices the interruption but not the human's own error rate. The ask-vs-act rule is not a tuning problem; it is arithmetic, once the human is priced honestly.

## (c) Miscalibration cost (stakes-adjusted policy)

| Agent | ECE | total cost | asks | unaudited errors |
|---|---|---|---|---|
| underconfident (delta=-0.15) | 0.137 | 23,233 (+1,758) | 1937 | 9 |
| calibrated (delta=+0.00) | 0.020 | 21,476 (+0) | 1364 | 58 |
| overconfident (delta=+0.15) | 0.132 | 32,280 (+10,805) | 466 | 221 |

Overconfidence (+0.15) is the expensive direction: the policy trusts inflated confidence, under-asks, and errors slip through. Underconfidence wastes attention but errs safe -- miscalibration is asymmetric in cost.

## (d) Trust calibration

Cost-minimizing human trust threshold tau* = 0.90 (cost 21,493); EV-optimal reference cost 21,476.

Over-trust index at tau=0.50: +0.1645 excess unaudited-error rate vs optimal. Under-trust index at tau=0.95: +0.2385 excess interruption rate vs optimal. Both directions are measurable in cost -- trust must be *calibrated*, not maximized.

## (e) Attention budget exhaustion

| Budget | knapsack | truncated (stakes-adj) | truncated (fixed 0.8) | high-stakes asked: knapsack | high-stakes asked: truncated |
|---|---|---|---|---|---|
| 0 | 55,726 | 55,726 | 55,726 | 0.00 | 0.00 |
| 10 | 54,134 | 55,575 | 55,401 | 0.16 | 0.00 |
| 25 | 52,209 | 55,279 | 55,040 | 0.22 | 0.00 |
| 50 | 49,004 | 54,575 | 54,588 | 0.36 | 0.00 |
| 100 | 45,744 | 53,192 | 52,828 | 0.53 | 0.02 |
| 200 | 38,304 | 50,181 | 47,845 | 0.71 | 0.04 |
| 500 | 27,197 | 39,903 | 39,928 | 0.89 | 0.16 |
| 2000 | 21,476 | 21,476 | 29,556 | 0.96 | 0.96 |

First-come truncation starves high-stakes decisions: at B=50 the knapsack still asks the decisions that matter while truncation spends the budget on whatever arrived first. Attention bankruptcy is not about asking too little -- it is about asking in the wrong order.

## Reproducibility

Every number above is produced by `experiments/run_experiments.py` (seed 7). Re-running regenerates this file and `charts.png` exactly.
