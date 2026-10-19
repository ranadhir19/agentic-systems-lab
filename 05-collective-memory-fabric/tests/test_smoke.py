"""Smoke tests for the Collective Memory Fabric."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.memory import MemoryFabric


def _admit(mem, agent, value, conf=0.9, ts=0, pred="state", subj="fact-0"):
    return mem.admit(agent, "alpha", subj, pred, value, conf,
                     [(agent, ts)], ts)


def test_admit_and_query():
    mem = MemoryFabric()
    _admit(mem, "a0", "v1", ts=0)
    c = mem.query("a0", "fact-0", "state", 5)
    assert c is not None and c.value == "v1"


def test_merge_strengthens():
    mem = MemoryFabric()
    _admit(mem, "a0", "v1", ts=0)
    status, c = _admit(mem, "a1", "v1", ts=1)
    assert status == "merged"
    assert len(c.evidence) == 2


def test_conflict_reconciliation_quorum():
    mem = MemoryFabric(ttl=100, quorum_window=10)
    _admit(mem, "a0", "v_true", conf=0.9, ts=0)
    _admit(mem, "a1", "v_true", conf=0.9, ts=1)
    _admit(mem, "a2", "v_true", conf=0.9, ts=2)
    # lone attacker, high confidence, triple-counted single-source evidence
    status, c = mem.admit("evil", "beta", "fact-0", "state", "v_false",
                          0.99, [("evil", 3)] * 5, 3)
    assert status == "rejected_by_reconciliation", status
    q = mem.query("a0", "fact-0", "state", 3)
    assert q.value == "v_true"


def test_fact_flip_converges():
    mem = MemoryFabric(ttl=100, quorum_window=6)
    for t, ag in enumerate(["a0", "a1", "a2"]):
        _admit(mem, ag, "v_old", conf=0.9, ts=t)
    # new value observed by several agents over ticks
    for t in range(10, 16):
        _admit(mem, f"b{t}", "v_new", conf=0.9, ts=t)
    q = mem.query("a0", "fact-0", "state", 15)
    assert q.value == "v_new", q.value


def test_revoke_quorum():
    mem = MemoryFabric()
    _, c = _admit(mem, "a0", "v1", ts=0)
    assert mem.revoke(c.id, "a1", [("a1", 1), ("a2", 1)], 1) is True
    assert mem.query("a0", "fact-0", "state", 1) is None


def test_revoke_single_non_author_fails():
    mem = MemoryFabric()
    _, c = _admit(mem, "a0", "v1", ts=0)
    assert mem.revoke(c.id, "a1", [("a1", 1)], 1) is False


def test_expiry():
    mem = MemoryFabric(ttl=5)
    _admit(mem, "a0", "v1", ts=0)
    assert mem.sweep(10) == 1
    assert mem.query("a0", "fact-0", "state", 10) is None


def test_mcp_serialization():
    import json
    mem = MemoryFabric()
    _, c = _admit(mem, "a0", "v1", ts=0)
    r = c.to_mcp_resource()
    assert r["uri"].startswith("cmf://claims/")
    body = json.loads(r["text"])
    assert body["value"] == "v1" and body["provenance"]["agent"] == "a0"
