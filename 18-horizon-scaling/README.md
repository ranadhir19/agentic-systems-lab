# Horizon Scaling — How Agent Reliability Decays with Task Length, and What Flattens the Curve

## Problem

Agents that ace 5-step tasks collapse on 80-step ones. Every practitioner
knows reliability decays with horizon length, but the decay is rarely
*measured*: is it exponential? Which error types drive it? And which
architectures actually flatten the curve versus just adding cost? This is
the central empirical question behind autonomous agent deployment (cf.
METR's time-horizon work on AI agents): before trusting an agent with a
long task, you need its decay curve.

## Gap

The systems in this repo handle failures *within* a task (HealFlow
recovers, the SRE systems observe, the risk twin assesses) but none
measure how success scales with horizon length, compare mitigations
head-to-head on the same task family, or price reliability in
cost-per-successful-task. Without the curve, architecture choice is
folklore: "add checkpoints" or "use voting" with no numbers behind when
each pays off.

## Solution

A seeded long-horizon task simulator plus five agents on one task family:

- **Task model.** A task is N sequential steps. Each step draws
  clean / *corrupt* (recoverable but latent) / *fatal* (aborts the
  attempt). Corruption persists and *compounds*: while corrupted, the
  per-step fatal probability is multiplied by (1 + cascade). A perfect
  final grader decides success; intermediate verification (checkpoints)
  is *fallible* (detects corruption with probability 0.8). That
  asymmetry is the honest core: your own checks can miss what the final
  grading catches, so corruption can predate a rollback point and become
  unrecoverable.
- **Baseline**: linear executor, no intermediate checks.
- **Checkpoints(k)**: verify every k steps; rollback + full segment redo
  on detection (bounded redos).
- **Hierarchy(s)**: planner decomposes into sub-tasks; workers get
  narrower specs, so per-step error is halved; sub-task boundaries are
  verified, failures redo only the sub-task.
- **Recovery(k)**: checkpoints + *diagnosis* (targeted redo from the
  corrupted step, not the segment start) + in-place step retries on
  fatal errors — HealFlow-style smallest repair.
- **Voting(n)**: each step executed n times, majority vote wins.

Cost model: a step costs 1.0, a verification 2.0, a diagnosis 3.0.
Headline metric: **cost per successful task**.

## Results

Seed 7; 2000 trials per cell; default family p_fatal=0.01, p_err=0.03.

**The decay curve is exponential, exactly as theory predicts.**
Baseline success: 0.804 (N=5) → 0.645 (N=10) → 0.420 (N=20) →
0.188 (N=40) → **0.035 (N=80)**. Log-linear fit gives per-step
q = 0.95903, R^2 = 0.9999, against the theoretical (1-pf)(1-pe) =
0.96030. The model is calibrated: the simulation reproduces the math.

**Every mitigation flattens the curve** (fitted per-step q):

| Agent | N=80 success | q_hat |
|---|---|---|
| baseline | 0.035 | 0.95903 |
| checkpoints(k=5) | 0.596 | 0.99355 |
| recovery(k=5) | 0.613 | 0.99386 |
| voting(n=3) | 0.676 | 0.99513 |
| hierarchy(s=10) | **0.740** | **0.99624** |

**But reliability is not the bill.** Cost per successful task:

| Agent | N=10 | N=40 | N=80 |
|---|---|---|---|
| baseline | **14.7** | 158.4 | 1211.0 |
| checkpoints(k=5) | 17.7 | 85.9 | 200.4 |
| hierarchy(s=10) | 14.8 | **66.3** | **145.4** |
| voting(n=3) | 31.6 | 145.7 | 355.3 |
| recovery(k=5) | 17.4 | 85.5 | 197.3 |

Cheapest: baseline at N<=10 (mitigations aren't worth it for short
tasks), hierarchy beyond. Voting is never cheapest — 3x step cost.

**Checkpoint-interval sweep (N=40):** k=5 is optimal by
cost-per-success (86.5). k=2 verifies slightly better (0.772 vs 0.764
success) but verification overhead dominates (105.5). k=40 barely
helps (0.531 success, 164.8 cost).

**Error mix matters (N=40):** in the fatal-heavy mix, checkpoints
(0.951) and recovery (0.958) dominate — fatal errors are immediately
visible, so rollback-and-redo is brutally effective. In the
corruption-heavy mix, hierarchy wins (0.767) via narrower specs.
Voting is the flattest across mixes (0.66–0.75) but always pricey.

**Interaction (N=80):** hierarchy + checkpoints reaches 0.798 success
vs 0.750 (hierarchy) and 0.615 (checkpoints) — but cost-per-success is
149.6 vs hierarchy's 145.4. Diminishing returns: the combination wins
on reliability, loses on price.

## Insights

- **Measure the curve before choosing the architecture.** The
  exponential fit (R^2 = 0.9999) means one number — per-step q —
  summarizes an agent's horizon robustness. Compare q, not anecdotes.
- **Short tasks need no mitigations.** Below ~10 steps the baseline is
  cheapest; every mitigation is pure overhead there.
- **Decomposition wins on price, voting wins on predictability.**
  Hierarchy is cheapest at long horizons; voting's success is the most
  mix-independent (closed-form binomial, validated against simulation).
- **Diagnosis is a cost optimization, not a reliability one.**
  Recovery barely beats plain checkpoints on success (0.613 vs 0.596)
  but targeted repair shaves redo cost — its edge shows in the bill.
- **Fallible verification is the fundamental limit.** Corruption that
  predates the rollback point cannot be fixed by redoing; this caps
  every checkpoint-based design and is why hierarchy (preventing
  errors via narrower specs) beats checkpoints (catching them).

## Implementation

```
src/agentic_systems/horizon_scaling/
  tasks.py    # TaskSpec, RunReport, step-outcome model, theory helpers
  agents.py   # baseline, checkpoints, hierarchy, recovery, voting,
              # hierarchy+checkpoints (one shared verify-and-rollback core)
  metrics.py  # Wilson CIs, exponential-decay fit, cost-per-success
  catalog.py  # default task family + error-mix presets
18-horizon-scaling/
  experiments/run_experiments.py  # phases (a)-(f), seed 7
```

## Limitations

- Synthetic step outcomes; real agent errors are correlated and
  task-dependent, not i.i.d. draws.
- The cascade multiplier (2.0) and detection probability (0.8) are
  modeling choices, not measured constants — the *shapes* of the
  curves are the finding, not the absolute numbers.
- Voting lumps fatal and corrupt attempts into "wrong votes"; real
  voting needs a judge, whose own errors aren't modeled.
- Hierarchy's spec_factor (0.5) is an assumption: narrower specs are
  modeled as halving per-step error. The qualitative ranking
  (decomposition helps) is robust to the exact value; the magnitude
  is not.

## Reproducibility

```
cd 18-horizon-scaling && python3 experiments/run_experiments.py
```

Regenerates `results/results.md` and `results/charts.png` from seed 7
(~15 seconds). `tests/test_smoke.py`: 9 tests, including
simulation-vs-theory checks for the baseline and voting agents.
