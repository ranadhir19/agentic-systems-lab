"""Sentinel: hash-chained evidence ledger + deterministic replay engine.

Problem
-------
Regulated agentic systems must answer "why did the agent do that?" months
later — and the answer must be *reproducible*. Sampling nondeterminism,
tool races, and silent prompt/config drift break naive replay.

Design
------
Every agent decision is recorded as a ledger entry:

    decision_id | inputs_hash | policy_version | model_params (incl. seed)
    | tool_calls[] | output_hash | prev_hash | entry_hash

Entries are SHA-256 hash-chained (tamper-evident: altering any entry breaks
every later link). The ReplayEngine re-executes a recorded decision with
the exact recorded seed/params/tool results and compares output hashes:

    MATCH      — replay reproduces the decision bit-for-bit
    DIVERGED   — output differs; the engine reports the first diverging step
    UNREPLAYABLE — missing seed/tool cassette (a governance finding itself)

A Verifier walks the chain and checks every link in O(n).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json


def _h(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()


@dataclass
class ToolCall:
    name: str
    args_hash: str
    result_hash: str


@dataclass
class DecisionRecord:
    decision_id: str
    inputs_hash: str
    policy_version: str
    model_params: dict       # must include "seed" for replayability
    tool_calls: list[ToolCall]
    output_hash: str
    prev_hash: str = "GENESIS"
    entry_hash: str = ""

    def seal(self) -> "DecisionRecord":
        body = {
            "decision_id": self.decision_id,
            "inputs_hash": self.inputs_hash,
            "policy_version": self.policy_version,
            "model_params": self.model_params,
            "tool_calls": [(t.name, t.args_hash, t.result_hash)
                            for t in self.tool_calls],
            "output_hash": self.output_hash,
            "prev_hash": self.prev_hash,
        }
        self.entry_hash = _h(body)
        return self


class EvidenceLedger:
    """Append-only, hash-chained decision log."""

    def __init__(self):
        self.entries: list[DecisionRecord] = []

    def append(self, record: DecisionRecord) -> DecisionRecord:
        record.prev_hash = (self.entries[-1].entry_hash
                            if self.entries else "GENESIS")
        record.seal()
        self.entries.append(record)
        return record

    def verify_chain(self) -> tuple[bool, int]:
        """Return (ok, first_bad_index). O(n)."""
        prev = "GENESIS"
        for i, e in enumerate(self.entries):
            if e.prev_hash != prev:
                return False, i
            probe = DecisionRecord(e.decision_id, e.inputs_hash,
                                   e.policy_version, e.model_params,
                                   e.tool_calls, e.output_hash, e.prev_hash)
            probe.seal()
            if probe.entry_hash != e.entry_hash:
                return False, i
            prev = e.entry_hash
        return True, -1


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------
@dataclass
class ReplayVerdict:
    decision_id: str
    verdict: str              # MATCH | DIVERGED | UNREPLAYABLE
    first_divergence: str = ""
    detail: str = ""


class ReplayEngine:
    """Re-executes recorded decisions deterministically.

    The `executor` is a callable (record, tool_cassette) -> output_hash
    supplied by the host system. The cassette replays recorded tool results
    instead of calling live tools.
    """

    def __init__(self, executor):
        self.executor = executor

    def replay(self, record: DecisionRecord) -> ReplayVerdict:
        if "seed" not in record.model_params:
            return ReplayVerdict(record.decision_id, "UNREPLAYABLE",
                                 detail="no seed recorded")
        cassette = {t.name: t.result_hash for t in record.tool_calls}
        try:
            out_hash = self.executor(record, cassette)
        except Exception as exc:  # noqa: BLE001 — replay must not crash
            return ReplayVerdict(record.decision_id, "DIVERGED",
                                 first_divergence="executor",
                                 detail=f"executor raised: {exc}")
        if out_hash == record.output_hash:
            return ReplayVerdict(record.decision_id, "MATCH")
        # locate first divergence: re-run stepwise if executor supports it
        stepper = getattr(self.executor, "stepwise", None)
        if stepper is not None:
            for step, expected in stepper(record, cassette):
                if step != expected:
                    return ReplayVerdict(record.decision_id, "DIVERGED",
                                         first_divergence=step)
        return ReplayVerdict(record.decision_id, "DIVERGED",
                             first_divergence="output_hash")
