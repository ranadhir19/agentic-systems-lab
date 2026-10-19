"""Deterministic simulated agent for Sentinel experiments.

`SimulatedAgent.execute(record, cassette)` derives its output *only* from:
the inputs hash, the recorded seed, the policy version, and the tool
cassette. Same inputs -> same output hash, always. Faults are injected by
perturbing one of those determinants, which is exactly how real
nondeterminism (lost seed, drifting tool, edited record) manifests.
"""
from __future__ import annotations

import hashlib
import random

from .ledger import DecisionRecord


def _h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


class SimulatedAgent:
    STEPS = ("plan", "tool:search", "tool:lookup", "synthesize", "finalize")

    def execute(self, record: DecisionRecord, cassette: dict) -> str:
        seed = record.model_params["seed"]
        step_hashes = []
        for step in self.STEPS:
            rng = random.Random(f"{seed}|{record.inputs_hash}|"
                                f"{record.policy_version}|{step}")
            tool_bit = cassette.get(step, "no-tool")
            step_hashes.append(_h(f"{step}|{tool_bit}|{rng.getrandbits(64)}"))
        return _h("|".join(step_hashes))

    def stepwise(self, record: DecisionRecord, cassette: dict):
        """Yield (replayed_step_hash, recorded_step_hash) pairs.

        The recorded hashes are smuggled in model_params['_steps'] by the
        experiment harness (a real system would store per-step hashes in
        the ledger entry).
        """
        seed = record.model_params["seed"]
        recorded = record.model_params.get("_steps", [])
        for i, step in enumerate(self.STEPS):
            rng = random.Random(f"{seed}|{record.inputs_hash}|"
                                f"{record.policy_version}|{step}")
            tool_bit = cassette.get(step, "no-tool")
            replayed = _h(f"{step}|{tool_bit}|{rng.getrandbits(64)}")
            expected = recorded[i] if i < len(recorded) else None
            yield replayed, expected


def record_decision(agent: SimulatedAgent, ledger, decision_id: str,
                    inputs: str, policy: str, seed: int,
                    tools: list[tuple[str, str, str]]) -> DecisionRecord:
    """Run the agent once and append the sealed record to the ledger."""
    from .ledger import ToolCall
    tool_calls = [ToolCall(n, _h(a), _h(r)) for n, a, r in tools]
    tmp = DecisionRecord(decision_id, _h(inputs), policy,
                         {"seed": seed, "temperature": 0.0}, tool_calls, "")
    cassette = {t.name: t.result_hash for t in tool_calls}
    out = agent.execute(tmp, cassette)
    steps = [h for h, _ in agent.stepwise(tmp, cassette)]
    tmp.model_params["_steps"] = steps
    tmp.output_hash = out
    return ledger.append(tmp)
