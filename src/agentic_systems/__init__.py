"""Agentic Systems Lab — a library of six original agentic-AI systems.

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

All systems are simulation-based with seeded RNG: the benchmarks measure
architectural and protocol tradeoffs, not production model behavior.
"""

from __future__ import annotations

__version__ = "0.1.0"
__author__ = "Ranadhir Ghosh"

from agentic_systems import forge, healflow, memory_fabric, meridian, sentinel, skillbridge

__all__ = [
    "__version__",
    "meridian",
    "sentinel",
    "forge",
    "skillbridge",
    "memory_fabric",
    "healflow",
]
