"""Sentinel quickstart: tamper-evident ledger + deterministic replay.

Records 5 agent decisions to a hash-chained ledger, replays one (MATCH),
then shows two failure modes: a mutated tool result (DIVERGED, with the
diverging step located) and a forged ledger entry (chain verify fails).

Run:  python3 examples/02_sentinel_quickstart.py
"""
from __future__ import annotations

import copy

from agentic_systems.sentinel import (
    EvidenceLedger,
    ReplayEngine,
    SimulatedAgent,
    record_decision,
)


def main() -> None:
    ledger = EvidenceLedger()
    agent = SimulatedAgent()
    records = []
    for i in range(5):
        tools = [("tool:search", f"args-{i}", f"result-{i}")]
        rec = record_decision(agent, ledger, f"demo-{i}",
                              inputs=f"query {i}", policy="demo-policy",
                              seed=1000 + i, tools=tools)
        records.append(rec)

    engine = ReplayEngine(agent.execute)

    # 1. Clean replay of the first decision
    v = engine.replay(records[0])
    print(f"clean replay        -> {v.verdict}")
    assert v.verdict == "MATCH"

    # 2. Tool-result drift: replay must DIVERGE and locate the step
    bad = copy.deepcopy(records[1])
    bad.tool_calls[0].result_hash = "tampered-result"
    v = engine.replay(bad)
    print(f"mutated tool result -> {v.verdict} (first divergence: "
          f"{v.first_divergence})")
    assert v.verdict == "DIVERGED"

    # 3. Ledger tampering: chain verification must fail and point at the entry
    records[3].output_hash = "forged"
    ok, idx = ledger.verify_chain()
    print(f"forged ledger entry -> chain valid: {ok}, detected at index {idx}")
    assert not ok and idx == 3

    print("All Sentinel checks passed.")


if __name__ == "__main__":
    main()
