# Decision Partition — Complexity-Scored Allocation of Decisions to Agents

## Research problem

Users want a complex decision-processing workflow executed by a
multi-agent system. They can already say which decisions are *simple* and
which are *composite* (needing decomposition into sub-decisions), but not
how many agents the workflow needs or which decisions each agent should
own. Guessing wrong is expensive: one agent per decision explodes
coordination overhead, while cramming unrelated complex decisions into one
agent overloads it and blurs accountability.

## Gap

There is no principled, reproducible bridge between "here are our
decisions" and "here is the agent topology". Existing practice is manual:
architects eyeball the workflow and assign agents by intuition, with no
quantified complexity measure, no sensitivity analysis, and no mechanism
to re-allocate work when beliefs change as the system learns.

## Proposed solution

Decision Partition scores every decision by how many distinct state
groups it forces an agent to distinguish, weighted by category:

    complexity score = |partition blocks| x category weight

with weights simple = 1.0, composite = 2.0, and levels high (score >= 10),
medium (5 <= score < 10), low (score < 5). It then applies allocation
rules: high-complexity decisions get dedicated agents, medium ones share
an agent only with similar-domain decisions (Jaccard overlap of domain
tags), and low ones are grouped into a single general agent to avoid
overhead. Every assignment carries a machine-readable rationale.

On top of this core, the system adds three extensions:

- **Dynamic re-scoring.** Evidence updates (new state distinctions
  discovered, old ones retired, reclassification simple <-> composite)
  re-score decisions; re-partitioning fires only when a complexity-level
  threshold is crossed, and stability is tracked across re-partitions.
- **Cost-aware scoring.** Optional compute/latency add-ons fold operating
  cost into the effective score, so a nominally simple but expensive
  decision can earn a dedicated agent.
- **Sequential planning.** Decisions with dependencies are topologically
  staged; each stage is partitioned independently, with handoff costs and
  critical-path complexity reported.

## Implementation

`agentic_systems/decision_partition/`:

- `decisions.py` — the `Decision` model: name, category, state blocks,
  domain tags, optional compute/latency costs, dependency list.
- `scoring.py` — `Scorer`: base score, level buckets, latency/compute
  add-ons (`effective_score`).
- `partition.py` — `partition_decisions` (dedicated / domain-shared /
  grouped rules), `Partition` with per-agent rationales, `partition_metrics`
  (agent count vs naive 1:1, load balance, coordination-overhead estimate),
  `assignment_churn` between partitions.
- `dynamic.py` — `DynamicPartitioner`: `observe()` evidence updates,
  threshold-crossing detection, `maybe_repartition()`, stability history.
- `planner.py` — `topological_stages`, per-stage partitions,
  `critical_path_score`, cross-agent handoff accounting.
- `catalog.py` — the insurance-claim worked example with the concept's
  exact numbers and canonical agent names.

## Architecture

```mermaid
flowchart TB
    P[Problem statement:\ndecisions + simple/composite labels] --> D[Decision model\nblocks, domains, costs, deps]
    D --> S[Scorer\nscore = |blocks| x weight\n+ latency/compute add-ons]
    S --> L{Level?}
    L -->|>= 10| A1[Dedicated agent]
    L -->|5..9| A2[Shared agent\nif domain overlap]
    L -->|< 5| A3[General agent]
    A1 --> PT[Partition\n+ rationales + metrics]
    A2 --> PT
    A3 --> PT
    E[Evidence updates] --> DY[DynamicPartitioner\nre-score, threshold check]
    DY -->|crossed| PT
    DEP[Dependencies] --> PL[Sequential planner\nstages, handoffs, critical path]
```

## Experiments

`experiments/run_experiments.py` — five seeded experiments:

**A — insurance reproduction.** The concept's worked example reproduces
exactly: scores (3, 10, 8, 10, 4), levels (low, high, medium, high, low),
and the 4-agent partition (Damage Specialist, Fraud Specialist,
Compliance Agent, Intake Agent for identity + settlement).

**B — synthetic scaling.** Random workflows of 10/25/50 decisions, 5
seeds each: partitioned agent count vs naive 1:1, load balance, and
coordination-overhead estimate.

**C — sensitivity.** One decision's block count swept 2..8 (mean churn
over 12 decisions); composite weight swept 1.0..3.0. Measures how often
assignments change.

**D — dynamic re-partition.** Five evidence updates injected into the
insurance workflow (e.g. identity gains biometric checks, policy gains
rider clauses, fraud loses a model signal): threshold crossings trigger
re-partitions; stability tracked each step.

**E — latency-aware scoring.** Latency weight swept 0..4 on a 12-decision
workflow with per-decision latencies: agent count and churn vs the base
partition.

![charts](results/charts.png)

Full table: [results/results.md](results/results.md).

## Results & conclusions

1. **The concept reproduces exactly.** Scores (3, 10, 8, 10, 4) and the
   4-agent partition match the write-up block for block; the sequential
   plan stages identity -> {damage, policy, fraud} -> settlement with a
   critical-path score of 17.0 and 6 cross-agent handoffs.
2. **Partitioning scales sub-linearly.** 10/25/50 decisions need only
   5.8/11.6/17.2 agents on average (42-66% fewer than 1:1), and the
   coordination-overhead estimate drops from 1225 to 141 at n=50.
3. **Partitions are locally stable but globally sensitive.** Varying one
   decision's block count moves 21-40% of assignments on average, while
   changing the composite weight re-partitions almost everything
   (churn 0.75-1.0) — the weight is the high-leverage parameter.
4. **Re-partition only on threshold crossings.** All five evidence updates
   crossed a level boundary and triggered exactly one re-partition each;
   stability stayed at 0.6-1.0, so the topology evolves without thrash.
5. **Cost can override simplicity.** Raising the latency weight from 0 to
   4 grew the 12-decision workflow from 8 to 10 agents with up to 50%
   assignment churn — expensive "simple" decisions earn dedicated agents.

## Run it

```bash
cd 09-decision-partition
python3 experiments/run_experiments.py   # regenerates results/results.md + charts.png
python3 -c "import sys; sys.path.insert(0,'tests'); import test_smoke; [getattr(test_smoke,n)() or print(n,'OK') for n in dir(test_smoke) if n.startswith('test_')]"
```

Requires: Python 3.10+, `numpy`, `matplotlib`.

## Limitations

Block counts are supplied by the user, not estimated from data — the
scorer quantifies stated complexity, it does not discover it. Domain
similarity is tag Jaccard, a coarse proxy for real semantic overlap.
Coordination overhead is an estimate (channels + handoffs), not a
measured communication cost. The dynamic re-partitioner reacts to
threshold crossings only; gradual drift inside a level never triggers.

## What I'd build next

- Learned block estimation: derive state distinctions from decision logs
  instead of hand-authoring them.
- Embedding-based domain similarity in place of tag Jaccard.
- Joint optimization of partition + stage schedule against a latency
  budget, rather than scoring-then-partitioning.
- Costed re-partitioning: only re-allocate when the expected gain exceeds
  the migration cost of moving a decision between agents.
