# Behavioral Regression — catch functional drift across model versions

## Problem

Enterprises pin an agent stack to a model version, the vendor ships a new
one, and behavior shifts silently. Task success drops a few points,
tool-call formats drift, refusals get sloppy, latency and cost profiles
move — and no test catches any of it before production, because the
"tests" are vibes-based spot checks. System 13 (ideology-mirror) measures
*ideological* drift across versions; nothing in this repo measures
*functional* drift: did the new version get worse at the job?

## Gap

Model vendors publish eval scores, not behavioral diffs against *your*
workload. Existing regression practice for agents is ad hoc: re-run a
handful of golden prompts, eyeball the outputs, ship it. There is no
frozen battery with statistical teeth, no staged canary with
stop/rollback rules, and no policy that turns a diff report into a
pin / adopt / rollback decision with a rationale an SRE can audit.

## Solution

A regression discipline for agents, in four parts:

1. **Frozen battery** (`battery.py`): 120 tasks across tool use,
   multi-step, instruction following, and edge cases (including
   must-refuse tasks), with fixed ids, difficulties, and categories —
   identical for every version and every seed.
2. **Paired drift detector** (`detector.py`): common random numbers make
   every (seed, task) comparison paired by construction. Binary metrics
   (per-category pass, tool-format compliance, refusal accuracy) use
   McNemar's exact test; continuous metrics (cost, latency, tokens) use
   paired t-tests. A metric is a regression only if significant
   (p < 0.05) *and* material (|effect| >= threshold). Severity scoring
   weights by business impact: a silent tool-format break outranks a
   verbosity change by design.
3. **Canary analyzer** (`canary.py`): staged rollout (1% → 10%) on the
   same canary tasks for baseline and candidate. Stop the rollout on a
   significant regression overall or in any category; hold on weak
   signals; promote otherwise. Reports tasks-to-flag.
4. **Policy engine** (`policy.py`): conservative rules — canary stop or
   severe correctness regression → rollback; cost increase with no
   benefit → pin the baseline; strict improvement → auto-adopt; anything
   else → pin. Every decision carries a rationale.

The five model versions (`versions.py`) encode realistic upgrade stories:
v1 baseline, v2 strict improvement (more verbose), v3 silent tool-format
regression (cheaper and faster — which is why it is dangerous), v4 pure
cost regression, v5 mixed trade-off (better instruction following, worse
tool use).

## Results

Seeds [7, 11, 42, 0, 99]; 120-task battery; every number measured
(`experiments/run_experiments.py` regenerates `results/` exactly).

- **(a) Sensitivity:** single-category regressions are caught once they
  reach ~0.10 success delta (tool_use 0.20 at 0.10, 0.80 at 0.20).
  False-positive rate on benign shifts — verbosity x1.5, latency x1.8,
  cost x1.4, uniform +0.02 improvement — is **0.00** across the board:
  the detector does not cry wolf on efficiency changes.
- **(b) Canary:** v3 (the silent break) is stopped at the 1% stage in
  **5/5 seeds after just 40 tasks** (tool_use −0.571, p=0.015). v5 stops
  in 4/5 seeds (one seed needed the full battery). v2 and v4 promote
  cleanly through both stages.
- **(c) Severity:** v3 (2.467) >> v5 (0.765) > v4 (0.543) > v2 (0.228,
  all benign cost) > v1 (0.000). The tool-format break scores an order
  of magnitude above a verbosity change, as designed.
- **(d) Policy:** **4/4 decisions match ground truth** — v2 auto-adopt,
  v3 rollback (canary stop), v4 pin (cost +71% with no gain), v5
  rollback (tool_use −0.140, p<0.0001).
- **(e) Ablation:** detection power vs suite size shows clear diminishing
  returns — v3 goes 0.00 → 0.80 → 1.00 at n=30/60/120; the subtler v5
  needs n=240 to reach 0.80. Below ~60 tasks the battery is blind.

## Insights

- **Common random numbers are the whole trick.** Pairing by construction
  turns a noisy A/B into a McNemar test with real power; without it,
  single-seed comparisons drown in sampling noise.
- **Significance without materiality is noise; materiality without
  significance is anecdote.** Requiring both is what keeps the benign
  FPR at zero.
- **Cheap and fast can be the danger signal.** v3 improves cost and
  latency while silently breaking tool calls — naive dashboards would
  celebrate the upgrade.
- **The canary is for big breaks; the battery is for subtle ones.**
  v5's mixed trade-off mostly survives canarying and is caught by the
  full detector — the two stages are complementary, not redundant.
- **Severity must be opinionated.** Unweighted diffs rank a verbosity
  bump next to a format break; business weights put them an order of
  magnitude apart.

## Implementation

```
src/agentic_systems/behavioral_regression/
  versions.py     # ModelVersion v1..v5, Task/TaskResult, SimulatedAgent (CRN)
  battery.py      # build_battery (frozen), run_battery, BatteryResult.aggregate
  detector.py     # DriftDetector: McNemar + paired t, severity scoring
  canary.py       # CanaryAnalyzer: 1% -> 10% stages, stop/hold/promote
  policy.py       # PolicyEngine: auto_adopt / pin / rollback + rationale
21-behavioral-regression/
  experiments/run_experiments.py   # a-e, seeds [7, 11, 42, 0, 99]
```

## Honest limits

- All five model versions are **simulated stand-ins** with parameterized
  behavioral shifts. The measured contribution is the regression
  *methodology* (frozen battery, paired testing, canary rules, policy),
  not claims about any real vendor model.
- Common random numbers are a variance-reduction device: real
  version upgrades do not come with paired draws, so field power will be
  lower than reported here for the same battery size.
- The severity weights encode a judgment (tool calls > verbosity); a
  different business would weight differently. The weights are explicit
  parameters, not hidden magic.
- Ground-truth policy labels (adopt/rollback/pin) are defined by the
  experiment designer; the 1.00 policy accuracy measures consistency
  with those labels, not with production outcomes.
