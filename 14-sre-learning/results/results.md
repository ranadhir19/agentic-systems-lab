# SRE-Learning experiment results

World seed 7: 2400 changes / 180 days; train days 0-120, test days 120-180.

## A — change-risk prediction (held-out test changes)
AUC **0.7614** (Bayes ceiling 0.7613); precision 0.694, recall 0.217, F1 0.331; weight MAE vs ground truth 0.141.
Calibration (mean predicted, empirical rate, n):
- 0.13 -> 0.12 (n=361)
- 0.29 -> 0.32 (n=279)
- 0.48 -> 0.58 (n=117)
- 0.66 -> 0.72 (n=36)
- 0.81 -> 1.00 (n=1)

## B — change-incident linking (test incidents)
Top-1 accuracy **0.727**, top-3 **0.922** (n=231); recency-only baseline top-1 0.740.

## C — causal path prediction (top-k root-cause accuracy)
Graph + change-type (workflow): top-1 **0.850**, top-3 **0.993**; graph + change-type on correctly-linked only: top-1 0.958, top-3 1.000; correlation baseline: top-1 0.944, top-3 1.000 (n=287).

## D — similarity precision@k (120 test queries)
Learned metric: P@1 **1.000**, P@3 1.000, P@5 1.000; TF-IDF: P@1 0.900, P@3 0.917, P@5 0.920.

## E — resolution recommendation (simulated success rate)
Agent **0.885** vs most-frequent-action baseline 0.415 (n=287).

## F — continuous learning (monthly AUC on fixed validation)
Month: month1=0.5779, month2=0.5837, month3=0.5949, month4=0.6394, month5=0.6725; frozen month-1 model 0.5779.
AUC gain/month 0.0296.

## G — active learning (pair-accuracy by labeling budget)
Budget: budget_0=0.9637, unc_25=0.9663, rnd_25=0.9625, unc_50=0.9637, rnd_50=0.9625, unc_100=0.9712, rnd_100=0.9725, unc_200=0.9738, rnd_200=0.9663
