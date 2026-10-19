# Agentic Systems Lab — User Guide

Seven original agentic-AI systems, packaged as one installable Python
library. Each system is a complete, working answer to a hard problem in
production agentic AI — with seeded experiments you can re-run, measured
results, and honest conclusions about what works and what doesn't.

This guide explains the *why* behind each system: what problem it solves,
what the naive approach gets wrong, and when to reach for it.

## Installation

```bash
pip install agentic-systems-lab
```

Requires Python 3.10+. The library itself is pure standard library;
`numpy` and `matplotlib` are included for the experiment runners and charts.

From a source checkout:

```bash
git clone https://github.com/ranadhir19/agentic-systems-lab
cd agentic-systems-lab
pip install -e .
```

Verify:

```python
import agentic_systems
print(agentic_systems.__version__)   # 0.1.0
from agentic_systems.meridian import MeridianSystem
from agentic_systems.healflow import HealFlowRuntime
```

Runnable examples for every system live in `examples/` — each is a short
script you can read top to bottom:

```bash
python3 examples/01_meridian_quickstart.py
```

## When to use which system

| If your problem is... | Start with | It teaches you... |
|---|---|---|
| Routing work across agents/models without hand-tuned rules | `meridian` | Online decision optimization: contextual bandits that learn which worker tier fits which subtask, balancing quality, cost, and latency |
| Proving what an agent did, or catching tampering | `sentinel` | Tamper-evident logging: hash-chained evidence ledgers and deterministic replay with first-divergence pinpointing |
| Serving LLMs efficiently under load | `forge` | Inference systems thinking: why continuous batching beats static batching, and why SRPT's mean-latency win hides a p99 tail |
| Reusing agent skills across model providers | `skillbridge` | Portability engineering: versioned skill packages, capability brokering, model adapters, and governance policy as code |
| Agents sharing beliefs without being lied to | `memory_fabric` | Epistemic defense: versioned claims, evidence-weighted quorum reconciliation, expiry, and revocation |
| Workflows that break in production at 3am | `healflow` | Self-healing runtime design: contracts, checkpoints, causal diagnosis, smallest-viable repair, verified recovery |
| Understanding what a user wants across paraphrases, multi-intent turns, and conversation history | `intent_inference` | Goal inference vs intent classification: emergent structured goals, ask-vs-act planning, memory-grounded context resolution |

---

## 7. Intent Inference — goal inference vs intent classification

**The problem.** Traditional chatbots treat language understanding as
classification: utterance → one predefined intent label → dialogue
manager → API call. This breaks on paraphrases ("Can you tell me whether
I can afford lunch today?"), multi-intent utterances ("I forgot my
password, but I also changed my phone number, and I can't receive OTP"),
implicit goals ("I'm hungry"), intent that evolves across turns, and
utterances whose meaning exists only in context ("Book me a hotel" …
"Make it cheaper").

**The gap.** Intent taxonomies are designed by developers, not discovered
from users. Everything outside the catalog — or combining several
in-catalog intents — collapses to "Sorry, I didn't understand. Please
rephrase." The dialogue manager has no notion of goals, missing
information, or conversation history.

**The idea.** A ChatGPT-style pipeline in which intent is **emergent,
never classified**: conversation memory → semantic understanding
(meaning frames, not labels) → structured goal extraction
(primary/secondary goals, constraints, missing info, confidence) →
planner (decompose, ask-vs-act, tool selection) → orchestrator
dispatching specialist agents. "My Apple laptop screen becomes dark after
login" yields `diagnose_display` with missing-info questions — *Is an
external monitor connected? Have you tried safe mode?* — exactly the
structured output a reasoning assistant would produce. A question is
asked only when its evidence is genuinely absent ("Transfer $200 to
savings" asks nothing).

**Key result.** Head-to-head on a frozen 20-case suite (seed 7): the
TF-IDF + softmax classifier gets 45% task success — 0% on multi-intent,
0% on out-of-catalog, 40% on paraphrases. The inference pipeline gets
100% on every phenomenon, with 6 targeted clarifications instead of 7
useless fallbacks. No utterance ever yields "unknown".

**Try it:**

```python
from agentic_systems.intent_inference import InferencePipeline

pipe = InferencePipeline(seed=7)
r = pipe.turn("My laptop is overheating and I also forgot my Wi-Fi password")
print([g.id for g in r.goals])   # ['laptop_support', 'wifi_help']
print(r.response)
```

**When to use it.** Conversational agents where users paraphrase, combine
requests, speak implicitly, or rely on context — and where asking a
targeted question beats saying "I didn't understand".

## 1. Meridian — learned multi-agent orchestration

**The problem.** A single orchestrator becomes a bottleneck on complex
work: it serializes decisions, routes every subtask through one policy,
and wastes expensive worker capacity on trivial steps while starving hard
ones. Flat agent swarms have the opposite problem — no structure, no
accountability.

**The gap.** Existing orchestrators use fixed topologies and hand-tuned
routing rules. Nothing learns online which worker tier fits which subtask,
and the quality/cost/latency tradeoff is managed by static thresholds
rather than an explicit objective.

**The idea.** Meridian combines three layers: a **vertical hierarchy**
(meta-orchestrator → domain orchestrators → workers) for decomposition, a
**horizontal blackboard** (propose/request/commit) so domains resolve
dependencies peer-to-peer instead of escalating, and a **decision
optimizer** — a contextual Thompson-sampling router with profile-based
priors, plus a decomposition planner — that learns the routing policy
online by optimizing a scalarized quality − cost − latency objective.

**Key result.** On a 240-task benchmark the learned router reaches 90.4%
success, matching a hand-tuned tiering policy (90.8%) with zero hand-tuning
— and it keeps adapting, which a fixed rule cannot do.

**Try it:**

```python
from agentic_systems.meridian import MeridianSystem, RunConfig, TaskGenerator

tasks = TaskGenerator(seed=7).generate(24)
system = MeridianSystem(
    RunConfig("D", vertical=True, horizontal=True, optimized=True), seed=7)
results = [system.run(t) for t in tasks]
print(f"success: {sum(r.success for r in results)/len(results):.1%}")
```

**When to use it.** Anywhere you route subtasks across heterogeneous
workers or models and the "right" routing changes over time: agent fleets,
mixture-of-experts serving, tiered model cascades.

---

## 2. Sentinel — tamper-evident evidence ledger

**The problem.** When an agent takes a consequential action, you need to
prove *why*: what it saw, what tools it called, what the model decided.
Without that, audits are impossible and tampering is undetectable.

**The gap.** Logs are mutable, tool results are rarely pinned, and
"replaying" an agent decision usually means re-running it and hoping for
the same output.

**The idea.** Every decision is sealed into a hash-chained ledger entry
(inputs hash, tool-call hashes, seed, output hash). A replay engine
re-executes the decision deterministically from the record and returns a
verdict: MATCH, DIVERGED (with the first diverging step located), or
UNREPLAYABLE (seed stripped). Forging a ledger entry breaks the chain and
is detected at the exact index.

**Key result.** 600/600 exact replays; 100% detection on seed perturbation,
tool drift (100% step-located), missing seeds, and ledger forgery.

**Try it:**

```python
from agentic_systems.sentinel import (
    EvidenceLedger, ReplayEngine, SimulatedAgent, record_decision)

ledger, agent = EvidenceLedger(), SimulatedAgent()
rec = record_decision(agent, ledger, "d-1", inputs="summarize Q3",
                      policy="analyst", seed=42,
                      tools=[("tool:search", "q3 args", "q3 results")])
verdict = ReplayEngine(agent.execute).replay(rec)
print(verdict.verdict)   # MATCH
```

**When to use it.** Regulated agent deployments, financial or medical
workflows, any setting where "the agent did it" needs a verifiable,
replayable trail.

---

## 3. Forge — LLM inference serving simulator

**The problem.** LLM serving throughput is dominated by scheduling: how
requests are batched onto the GPU, how the KV cache is managed, and which
request goes next.

**The gap.** Intuition about batching ("bigger batches = better") breaks
down under real arrival patterns, and scheduling policies interact with
memory pressure in non-obvious ways.

**The idea.** A discrete-event simulator of an inference server: iteration
cost `t = T0 + K·batch_tokens`, a KV-cache capacity cap, Poisson arrivals.
Compare static FCFS batching, continuous (iteration-level) batching, and
continuous + shortest-remaining-processing-time.

**Key result.** At 4 req/s, continuous batching cuts mean latency ~9x vs
static (20.6s vs 189.5s). SRPT cuts the mean another 34% — but its p99
explodes: starving long requests is the hidden price.

**Try it:**

```python
from agentic_systems.forge import Engine, generate_requests
import copy

reqs = generate_requests(300, 0.004, seed=42)   # 4 req/s
for policy in ("static-fcfs", "continuous", "continuous-srpt"):
    r = Engine(policy).run(copy.deepcopy(reqs)).report()
    print(f"{policy:16s} mean={r['mean_e2e_ms']:8.0f}ms  p99={r['p99_e2e_ms']:8.0f}ms")
```

**When to use it.** Capacity planning for inference deployments,
evaluating scheduling policies before touching production, teaching how
serving systems actually behave under load.

---

## 4. SkillBridge — portable, governed AI skills

**The problem.** Every model provider has its own tool-calling conventions,
so "skills" get rewritten per provider — N skills × M providers of
duplicated, drifting work.

**The gap.** Prompt libraries are not portable artifacts: no versioning,
no capability contracts, no governance, no way to measure portability.

**The idea.** Skills become versioned **packages** (manifest + instruction
template + capability-referencing workflow + executable eval cases) in a
**registry** with semver resolution. A **capability broker** binds
capability names to server implementations MCP-style. **Model adapters**
translate portable tool steps into provider conventions. A **policy
engine** enforces approved-tool allowlists, high-sensitivity approval
gates, and deprecated-version refusal — denials are returned, not thrown,
so they can be audited.

**Key result.** Cross-model variance more than halved (std 0.042 vs 0.095);
the framework pays for itself from the second model on; 3/3 adversarial
runs denied, 20/20 clean runs allowed.

**Try it:**

```python
from agentic_systems.skillbridge import (
    PolicyEngine, SkillRuntime, build_catalog, default_adapters)

registry, broker = build_catalog()
runtime = SkillRuntime(registry, broker, PolicyEngine())
adapter = default_adapters(seed=3)[0]
r = runtime.run("invoice-extractor", adapter,
                {"document": "Vendor: Acme\nAmount: $9.99\nDate: 2026-01-01"})
print(r.allowed, r.outputs["text.extract"])
```

**When to use it.** Multi-provider agent platforms, internal tool
marketplaces, any team maintaining agent capabilities across model
generations.

---

## 5. Collective Memory Fabric — governed shared beliefs

**The problem.** Agents that share memory share failure modes: one
compromised or confused agent can poison every other agent's beliefs.

**The gap.** Shared vector stores are last-write-wins — whoever writes
last (or loudest) wins. Majority voting is Sybil-vulnerable: sock-puppet
agents outvote the truth.

**The idea.** Beliefs are **versioned claims** with evidence. Admission
merges corroborating claims (refreshing recency) instead of forking.
Conflicting claims go through **quorum reconciliation** scored by
`confidence × recency × (1 + 0.25 × distinct agents)` — counting *sources*,
not claims, which is what defeats Sybil attacks. Claims expire (TTL) and
can be revoked by quorum.

**Key result.** Under sustained misinformation injection: 98.0% task
success during the attack, 0.0% wrong-answer rate on the targeted fact,
0.6-tick recovery. The weakest model family improves from 69.1% to 94.5%.

**Try it:**

```python
from agentic_systems.memory_fabric import MemoryFabric

mem = MemoryFabric()
for a in ("a0", "a1"):
    mem.admit(a, "alpha", "fact-0", "state", "v1", 0.9, [(a, 0)], 0)
    mem.admit(a, "alpha", "fact-0", "state", "v1", 0.9, [(a, 5)], 5)
status, _ = mem.admit("a3", "alpha", "fact-0", "state", "LIE",
                      0.99, [("a3", 6)], 6)
print(status)   # rejected_by_reconciliation
```

**When to use it.** Multi-agent systems with shared world models,
retrieval layers that must resist prompt-injection poisoning, federated
knowledge bases.

---

## 6. HealFlow — self-healing workflows

**The problem.** Production agent workflows break: tools go down, schemas
change, intermediates corrupt. Naive retry loops either give up or —
worse — repeat side effects like charging a customer twice.

**The gap.** Most "agentic" error handling is retry-or-abort. There is no
causal diagnosis (transient vs permanent vs schema vs corruption), no
repair ladder, no verification that the repair actually worked, and no
memory of what worked last time.

**The idea.** Workflows declare **contracts** (pre/postconditions) and
**checkpoints**. On failure, a **diagnoser** walks back causally to
classify the fault, then climbs a **repair ladder**: retry → substitute →
rollback → compensate+abort → escalate — always the smallest viable
repair. A **verification gate** re-checks contracts after repair, and a
**repair memory** keyed by failure shape makes the second occurrence heal
in one step instead of two.

**Key result.** 6/6 safe outcomes on the fault battery (5 recovered, 1
graceful compensated abort), 0 side effects — where naive replanning
triple-charges a payment workflow. Diagnosis correct 6/6.

**Try it:**

```python
from agentic_systems.healflow import (
    PREDS, SUBSTITUTES, HealFlowRuntime, build_injector, etl_flow)

rt = HealFlowRuntime(build_injector(), PREDS, SUBSTITUTES)
rt.injector.add_fault("extract", "outage", n=2)   # transient outage, twice
rep = rt.run(etl_flow(), expected_cause="transient_outage")
print(rep.success, rep.side_effects, rep.repairs)  # True 0 ['retry', 'retry']
```

**When to use it.** Any multi-step agent workflow with external side
effects: payments, provisioning, data pipelines, customer-facing
automation.

---

## Reproducibility

Every system's headline numbers come from a seeded experiment runner you
can re-execute:

```bash
cd 01-meridian-orchestration && python3 experiments/run_experiments.py
```

All randomness uses stable seeds (no salted builtin `hash()`), so
re-running on any machine reproduces `results/results.md` exactly. The
only non-reproducible figures are wall-clock timings (ms/decision,
ms/tick), which measure your machine, not the architecture.

## Project layout

```
src/agentic_systems/      # the installable library
  meridian/               # 01 · learned multi-agent orchestration
  sentinel/               # 02 · tamper-evident evidence ledger
  forge/                  # 03 · LLM inference serving simulator
  skillbridge/            # 04 · portable, governed AI skills
  memory_fabric/          # 05 · governed collective memory
  healflow/               # 06 · self-healing workflows
  intent_inference/       # 07 · intent classification vs inference
examples/                 # one runnable quickstart per system
docs/                     # GitHub Pages site + this guide
01-meridian-orchestration/  # per-system: README, experiments/, results/, tests/
...
```

## License

MIT — see LICENSE.
