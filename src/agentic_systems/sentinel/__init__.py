"""Sentinel Ledger: tamper-evident evidence ledger + deterministic replay.

Records every agent decision (inputs, model params, tool calls, outputs)
into a SHA-256 hash-chained evidence ledger.  A deterministic replay engine
re-executes decisions from their recorded seeds and tool results, emitting
MATCH / DIVERGED / UNREPLAYABLE verdicts, and pinpoints the first divergent
step when tool outputs drift.  Used to audit agent behavior and detect
replay attacks, model drift, and ledger tampering.
"""

from .ledger import EvidenceLedger, ReplayEngine, DecisionRecord, ToolCall, ReplayVerdict
from .sim_agent import SimulatedAgent, record_decision

__all__ = [
    "EvidenceLedger",
    "ReplayEngine",
    "DecisionRecord",
    "ToolCall",
    "ReplayVerdict",
    "SimulatedAgent",
    "record_decision",
]
