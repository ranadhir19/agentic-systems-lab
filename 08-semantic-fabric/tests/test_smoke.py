"""Smoke tests for the Semantic Fabric."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np

from agentic_systems.semantic_fabric import (
    build_fabric, FabricReasoner, SemanticStore, FreshnessMonitor, synth)
from agentic_systems.semantic_fabric.extract import (
    extract_l0, extract_l1, extract_l2, extract_l3, extract_l4)
from agentic_systems.semantic_fabric.causal import extract_l5
from agentic_systems.semantic_fabric.cognitive import extract_l6, extract_l7
from agentic_systems.semantic_fabric.store import content_hash


def _small():
    return build_fabric(n_txns=1500, n_incidents=60, n_tickets=80,
                        n_users=120, seed=11)


def test_pipeline_builds_all_layers():
    store, rep = _small()
    assert store.layers() == ["L0", "L1", "L2", "L3", "L4", "L5", "L6",
                              "L7"]
    assert store.total_bytes() > 0


def test_store_versioning_and_hash():
    s = SemanticStore()
    v1, h1, ch1 = s.put("L1", "x", {"a": 1})
    v2, h2, ch2 = s.put("L1", "x", {"a": 1})   # identical -> no new version
    v3, h3, ch3 = s.put("L1", "x", {"a": 2})   # changed -> new version
    assert (v1, ch1) == (1, True)
    assert (v2, ch2) == (1, False) and h2 == h1
    assert (v3, ch3) == (2, True) and h3 != h1
    assert s.get("L1", "x", version=1)["artifact"] == {"a": 1}
    assert len(s.history("L1", "x")) == 2


def test_raw_discardable_after_extraction():
    store, rep = _small()
    # reasoning works from the store alone; raw never consulted
    r = FabricReasoner(store)
    assert r.diagnose("latency_ms")
    assert r.impacting_servers("payments")
    assert r.summarize()["causal_edges"]


def test_causal_dag_recovery():
    txns, truth = synth.gen_transactions(4000, seed=21)
    from agentic_systems.semantic_fabric.pipeline import (
        causal_matrix, CAUSAL_ORDER)
    from agentic_systems.semantic_fabric.common import dag_precision_recall
    art = extract_l5(causal_matrix(txns),
                     ["server_load", "queue_depth", "latency_ms", "error"],
                     CAUSAL_ORDER)
    p, rec = dag_precision_recall(art["edges"], truth["causal_edges"])
    assert rec >= 0.66, (p, rec)
    assert p >= 0.5, (p, rec)


def test_hot_servers_found():
    store, _ = _small()
    l3 = store.get("L3", "transactions")["artifact"]
    pay = [e["src"] for e in l3["edges"] if e["dst"] == "payments"]
    assert "srv03" in pay and "srv11" in pay


def test_intent_frames():
    tickets, truth = synth.gen_tickets(120, seed=31)
    frames = extract_l6(tickets)["frames"]
    acc = sum(f["intent"] == t for f, t in
              zip(frames, truth["intent"])) / len(frames)
    assert acc >= 0.9, acc


def test_drift_detector_quiet_stationary_loud_shift():
    mon = FreshnessMonitor()
    txns, _ = synth.gen_transactions(3000, seed=41)
    base = extract_l1(txns)
    txns2, _ = synth.gen_transactions(3000, seed=42)
    assert not mon.check("L1", extract_l1(txns2), base)["drifted"]
    txns3, _ = synth.gen_transactions(3000, seed=43)
    for t in txns3:
        t["latency_ms"] = round(t["latency_ms"] + 3.0 * 50, 1)
    assert mon.check("L1", extract_l1(txns3), base)["drifted"]


def test_reasoning_agreement_spot():
    store, rep = _small()
    r = FabricReasoner(store)
    fab = [e["src"] for e in r.impacting_servers("payments", top_k=2)]
    assert set(fab) == {"srv03", "srv11"}


def test_compression_beats_raw():
    import json
    store, rep = _small()
    raw_b = len(json.dumps(rep["raw"]["txns"], default=str).encode())
    assert store.total_bytes() < raw_b
