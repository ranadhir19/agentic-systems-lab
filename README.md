# Agentic Systems Lab

Twenty-one original, implemented agentic-AI systems — each with architecture,
working code, seeded experiments, measured results, and honest conclusions.
Built as a portfolio of senior AI architecture work: the emphasis is on
*decision-making under uncertainty*, *coordination*, and *reliability*,
not on prompt tricks.

Install it as a library, learn from it as a textbook, run it as a lab.

## Install

```bash
pip install agentic-systems-lab
```

Requires Python 3.10+. The library itself is pure standard library;
`numpy` and `matplotlib` ship with it for the experiment runners and charts.

From source:

```bash
git clone https://github.com/ranadhir19/agentic-systems-lab
cd agentic-systems-lab
pip install -e .
```

## Quickstart

```python
from agentic_systems.meridian import MeridianSystem, RunConfig, TaskGenerator

tasks = TaskGenerator(seed=7).generate(24)
system = MeridianSystem(
    RunConfig("D", vertical=True, horizontal=True, optimized=True), seed=7)
results = [system.run(t) for t in tasks]
print(f"success: {sum(r.success for r in results)/len(results):.1%}")
```

One runnable example per system lives in [`examples/`](examples/) — start
there. The full **[User Guide](docs/user-guide.md)** explains the *why*
behind each system: the problem, the gap in existing approaches, the core
idea, when to reach for it, and the measured results.

## Projects

| # | Project | Package | What it is | Key result |
|---|---|---|---|---|
| 01 | [meridian-orchestration](01-meridian-orchestration/) | `agentic_systems.meridian` | Multi-orchestrator multi-agent system: vertical hierarchy + horizontal blackboard + online decision optimization (contextual Thompson sampling) | Learned router matches a hand-tuned tiering policy (90.4% vs 90.8% success) with zero hand-tuning |
| 02 | [sentinel-ledger](02-sentinel-ledger/) | `agentic_systems.sentinel` | Hash-chained evidence ledger + deterministic replay engine for agent decisions | 600/600 exact replays; 100% detection on seed/tool/tamper faults |
| 03 | [forge-inference](03-forge-inference/) | `agentic_systems.forge` | Discrete-event simulator of LLM inference serving; static vs continuous vs SRPT scheduling | Continuous batching: 9.2× lower mean latency at high load; SRPT cuts mean 34% but starves p99 |
| 04 | [skillbridge-mcp](04-skillbridge-mcp/) | `agentic_systems.skillbridge` | Model-agnostic framework for reusable AI skills: portable packages, versioned registry, MCP-style capability broker, model adapters, governance, cross-model eval | Cross-model variance more than halved (0.042 vs 0.095); framework pays off from 2+ models |
| 05 | [collective-memory-fabric](05-collective-memory-fabric/) | `agentic_systems.memory_fabric` | Governed collective memory protocol: versioned claims, evidence-weighted quorum reconciliation, expiry, revocation | 0% wrong-answer rate under sustained misinformation injection; weakest model family 69% → 95% |
| 06 | [healflow](06-healflow/) | `agentic_systems.healflow` | Self-healing workflow runtime: contracts, checkpoints, causal diagnosis, smallest-viable repair, verified recovery, repair memory | 6/6 safe outcomes; naive replan triple-charges a payment workflow |
| 07 | [intent-inference](07-intent-inference/) | `agentic_systems.intent_inference` | Intent classification vs intent inference: TF-IDF/softmax baseline head-to-head against a ChatGPT-style goal-inference pipeline (memory → understanding → goals → planner → orchestrator) | 100% task success vs 45% baseline; 0% → 100% on multi-intent and out-of-catalog |
| 08 | [semantic-fabric](08-semantic-fabric/) | `agentic_systems.semantic_fabric` | 8-layer semantic extraction (structural → cognitive): store meaning, not data; versioned semantic store with freshness monitoring | 27.2:1 compression; causal DAG P 0.75/R 1.00; 4/4 queries answered without raw data |
| 09 | [decision-partition](09-decision-partition/) | `agentic_systems.decision_partition` | Complexity scoring (state blocks × weight) + optimal agent partitioning: dedicated/shared/grouped rules, dynamic re-scoring | Insurance example → 4 agents exactly; 42–66% fewer agents than naive 1:1 |
| 10 | [sre-observability](10-sre-observability/) | `agentic_systems.sre_observability` | MAS-based unified observability: per-layer observers, boundary-gap assessment (TP/FN/time-to-detect), unified response, strategy bridge | Boundary recall 0.78 vs intra 0.91; service→product 0.00→1.00 after fix; unified 100%/78min vs siloed 73%/102min |
| 11 | [emergent-goals](11-emergent-goals/) | `agentic_systems.emergent_goals` | Do communicating agents invent their own goals? Curiosity + empowerment + homeostasis + goal imagination, 5 pre-registered hypotheses, 4 ablations | H1 supported (49.5 vs 34.5 goals); H4 FAILED — curiosity is metabolically costly (413 vs 1185 steps) |
| 12 | [ai-risk-twin](12-ai-risk-twin/) | `agentic_systems.ai_risk_twin` | Architecture-first CISO pre-check: use-case twin, 28-rule engine (NIST/OWASP/EU AI Act/GDPR), dynamic 125-question funnel, L0–L5 evidence | 29 findings; readiness 0.41 NOT READY; fix-and-rerun −20 severity |
| 13 | [ideology-mirror](13-ideology-mirror/) | `agentic_systems.ideology_mirror` | LLMs reflect creators' ideology: red-team battery (framing bias, refusal asymmetry), AI constitution, vendor grades, CI drift gate | Creator divergence up to 1.546; steering → 1.000 conformance; vendor grades A/B/D |
| 14 | [sre-learning](14-sre-learning/) | `agentic_systems.sre_learning` | Data-first SRE: train change-risk, causality, similarity, resolution agents on incident history + continuous learning loop | Change-risk AUC 0.761 (= Bayes ceiling); resolution 0.89 vs 0.41; learner 0.58→0.67 under drift |
| 15 | [leadership-insights](15-leadership-insights/) | `agentic_systems.leadership_insights` | Join Jira/GitHub/ServiceNow/Workday/Planview: entity resolution + 4 leadership lenses + cross-source insight engine | $35,040/yr license waste found; 7 vs 1 insights siloed vs integrated |
| 16 | [enriched-observability](16-enriched-observability/) | `agentic_systems.enriched_observability` | Three-stage AI enrichment (raw → processed → analytic) across 5 layers; chain reconstruction; 5 role views | Chain recall 1.00; 18.2 alerts → 5-item chain; breach forecast MAE 3.4 min |
| 17 | [delegation-integrity](17-delegation-integrity/) | `agentic_systems.delegation_integrity` | Principal hierarchy, scoped/time-bounded authority tokens, confused-deputy simulator, multi-principal conflict resolution | Naive attack success 1.000 → 0.000 with provenance; attribution 1.000 at all depths |
| 18 | [horizon-scaling](18-horizon-scaling/) | `agentic_systems.horizon_scaling` | Long-horizon reliability decay curves; checkpoints vs hierarchy vs voting vs recovery + cost-per-success | Baseline 0.804 → 0.035 (N=5→80), exponential R²=0.9999; hierarchy 0.740 at N=80 |
| 19 | [attention-economics](19-attention-economics/) | `agentic_systems.attention_economics` | Human attention as priced resource; 5 escalation policies; trust calibration (over/under-trust indices) | Stakes-adjusted EV wins all regimes; overconfidence costs 6x underconfidence |
| 20 | [injection-containment](20-injection-containment/) | `agentic_systems.injection_containment` | Prompt-injection propagation across 4-hop delegation chains; 4 containment defenses; semantic mosaic effect | Combined defenses: 0.00 residual attack; mosaic detector catches 1.00 |
| 21 | [behavioral-regression](21-behavioral-regression/) | `agentic_systems.behavioral_regression` | Frozen 120-task battery; paired tests across model versions; canary 1%→10%; pin/adopt/rollback policy | 4/4 policy decisions match ground truth; 0.00 false positives on benign shifts |

## Reproducing the benchmarks

Each project's experiment runner regenerates its `results/` from scratch:

```bash
cd 01-meridian-orchestration
python3 experiments/run_experiments.py   # regenerates results/results.md + charts.png
```

All randomness uses stable seeds, so re-running on any machine reproduces
the results tables exactly. (Wall-clock timings like ms/decision measure
your machine, not the architecture.)

Smoke tests live in each project's `tests/` and run without extra
dependencies:

```bash
python3 -c "import sys; sys.path.insert(0,'tests'); import test_smoke; [getattr(test_smoke,n)() for n in dir(test_smoke) if n.startswith('test_')]"
```

## Layout

```
src/agentic_systems/      # the installable library (pip install agentic-systems-lab)
  meridian/               # 01 · learned multi-agent orchestration
  sentinel/               # 02 · tamper-evident evidence ledger
  forge/                  # 03 · LLM inference serving simulator
  skillbridge/            # 04 · portable, governed AI skills
  memory_fabric/          # 05 · governed collective memory
  healflow/               # 06 · self-healing workflows
  intent_inference/       # 07 · intent classification vs inference
examples/                 # one runnable quickstart per system
docs/                     # GitHub Pages site + user guide
01-meridian-orchestration/  # per-system: README, experiments/, results/, tests/
02-sentinel-ledger/
...
pyproject.toml            # PEP 621 packaging (setuptools)
PYPI_RELEASE.md           # checklist for publishing to PyPI
```

## Notes

- All agents, tools, and faults are **simulated with seeded RNG**. The
  benchmarks measure *architectural and protocol* tradeoffs, not production
  model behavior. Seeds are documented in each experiment runner.
- All twenty-one systems are original implementations built for this repo.
- Results tables are generated by the experiment runners — re-running
  reproduces them exactly.

## License

MIT — see [LICENSE](LICENSE).
