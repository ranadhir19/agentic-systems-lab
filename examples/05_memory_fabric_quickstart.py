"""Collective Memory Fabric quickstart: quorum beats a loud liar.

Two honest agents corroborate a fact — and keep corroborating it, which
refreshes its recency. A compromised agent then injects the opposite claim
with very high confidence. The evidence-weighted quorum still rejects the
lie: one confident voice cannot overturn continuously corroborated truth.

Run:  python3 examples/05_memory_fabric_quickstart.py
"""
from __future__ import annotations

from agentic_systems.memory_fabric import MemoryFabric


def main() -> None:
    mem = MemoryFabric()

    # Two independent agents corroborate the true value, then confirm it
    # again later. The merge refreshes the claim's recency and validity.
    for agent in ("a0", "a1"):
        mem.admit(agent, "alpha", "fact-0", "state", "v1",
                  0.9, [(agent, 0)], 0)
    for agent in ("a0", "a1"):
        status, _ = mem.admit(agent, "alpha", "fact-0", "state", "v1",
                              0.9, [(agent, 5)], 5)
        assert status == "merged"
    honest = mem.query("reader", "fact-0", "state", 5)
    print(f"before injection: {honest.value!r}")

    # A compromised agent injects the opposite claim, very confidently.
    status, _ = mem.admit("a3", "alpha", "fact-0", "state", "LIE",
                         0.99, [("a3", 6)], 6)
    print(f"injection outcome: {status}")
    assert status == "rejected_by_reconciliation"

    after = mem.query("reader", "fact-0", "state", 10)
    print(f"after injection:  {after.value!r}")
    assert after.value == "v1"

    print("Quorum held: the injected falsehood was not adopted.")


if __name__ == "__main__":
    main()
