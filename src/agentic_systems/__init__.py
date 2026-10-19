"""Agentic Systems Lab — a library of sixteen original agentic-AI systems.

Each subpackage is a self-contained, seeded, reproducible system:

- ``meridian``       — multi-orchestrator multi-agent routing with online
  decision optimization (contextual Thompson sampling)
- ``sentinel``       — hash-chained evidence ledger + deterministic replay
  engine for agent decisions
- ``forge``          — discrete-event simulator of LLM inference serving
  (static vs continuous vs SRPT scheduling)
- ``skillbridge``    — model-agnostic framework for reusable, portable,
  governed AI skills
- ``memory_fabric``  — governed collective-memory protocol with
  evidence-weighted quorum reconciliation
- ``healflow``       — self-healing workflow runtime: contracts, causal
  diagnosis, smallest-viable repair, verified recovery
- ``intent_inference`` — intent classification vs intent inference:
  traditional TF-IDF/softmax baseline head-to-head against a
  ChatGPT-style goal-inference pipeline (memory → understanding →
  goals → planner → orchestrator)
- ``semantic_fabric``   — 8-layer semantic extraction pipeline:
  store meaning, not data; versioned semantic store, freshness monitor
- ``decision_partition`` — decision complexity scoring + optimal agent
  partitioning (dedicated / shared / grouped), dynamic re-scoring
- ``sre_observability`` — MAS-based unified observability: boundary-gap
  assessment, unified incident response, strategy bridge
- ``emergent_goals``    — intrinsic motivation testbed: curiosity,
  empowerment, communication, goal imagination (pre-registered hypotheses)
- ``ai_risk_twin``      — architecture-first CISO pre-check: use-case twin,
  28-rule engine, dynamic question funnel, L0-L5 evidence
- ``ideology_mirror``   — value-alignment governance: red-team battery,
  AI constitution, vendor grades, CI drift gate
- ``sre_learning``      — data-first SRE: change-risk, causality, similarity,
  resolution agents trained on incident history + learning loop
- ``leadership_insights`` — join Jira/GitHub/ServiceNow/Workday/Planview:
  entity resolution + four leadership lenses
- ``enriched_observability`` — raw → processed → analytic enrichment
  across 5 layers; chain reconstruction; role views

All systems are simulation-based with seeded RNG: the benchmarks measure
architectural and protocol tradeoffs, not production model behavior.
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Ranadhir Ghosh"

from agentic_systems import (ai_risk_twin, decision_partition, enriched_observability, forge, healflow, ideology_mirror, intent_inference, leadership_insights, memory_fabric, meridian, semantic_fabric, sentinel, skillbridge, sre_learning, sre_observability, emergent_goals)

__all__ = [
    "__version__",
    "meridian",
    "sentinel",
    "forge",
    "skillbridge",
    "memory_fabric",
    "healflow",
    "intent_inference",
    "semantic_fabric",
    "decision_partition",
    "sre_observability",
    "emergent_goals",
    "ai_risk_twin",
    "ideology_mirror",
    "sre_learning",
    "leadership_insights",
    "enriched_observability",
    "delegation_integrity",
    "horizon_scaling",
    "attention_economics",
    "injection_containment",
    "behavioral_regression",
]
