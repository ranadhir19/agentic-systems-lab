# Agentic Systems Lab

Seven original, implemented agentic-AI systems — each with architecture,
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
- All seven systems are original implementations built for this repo.
- Results tables are generated by the experiment runners — re-running
  reproduces them exactly.

## License

MIT — see [LICENSE](LICENSE).
