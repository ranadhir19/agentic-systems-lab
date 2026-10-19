"""Semantic Fabric quickstart.

Builds the 8-layer semantic fabric from synthetic raw reality,
persists versioned semantic artifacts, discards the raw data, then
reasons — retrieval, simulation, root-cause — from the fabric alone.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agentic_systems.semantic_fabric import (
    build_fabric, FabricReasoner, FreshnessMonitor, synth)
from agentic_systems.semantic_fabric.extract import extract_l1


def main():
    print("== 1. Raw reality -> semantic extraction -> persistence ==")
    store, rep = build_fabric(n_txns=10000, n_incidents=300, n_tickets=400,
                              n_users=600, seed=7)
    print(f"layers persisted: {store.layers()}")
    print(f"semantic bytes: {store.total_bytes()} "
          f"(raw was ~2MB -> compression in play)")

    print("\n== 2. Raw data discarded; reasoning from the fabric alone ==")
    r = FabricReasoner(store)
    print("root cause of latency_ms:",
          r.diagnose("latency_ms", top_k=2))
    print("servers impacting payments:",
          [(e["src"], e["strength"])
           for e in r.impacting_servers("payments")])
    fx = r.what_if("server_load", 2.0)
    print("do(server_load=2.0) -> latency effect:",
          round(fx["latency_ms"], 3))
    print("next action after cart (archetype 0):",
          r.simulate_markov(0, "cart", 4, seed=0))

    print("\n== 3. Semantic freshness: drift between versions ==")
    mon = FreshnessMonitor()
    base = store.get("L1", "transactions")["artifact"]
    txns, _ = synth.gen_transactions(2000, seed=123)
    print("stationary batch:",
          mon.check("L1", extract_l1(txns), base)["drifted"])
    for t in txns:  # inject a 2-sigma latency shift
        t["latency_ms"] = round(t["latency_ms"] + 100.0, 1)
    chk = mon.check("L1", extract_l1(txns), base)
    print(f"shifted batch: drifted={chk['drifted']} "
          f"(score={chk['score']}, threshold={chk['threshold']})")

    print("\n== 4. One-screen semantic summary (no rows, just meaning) ==")
    s = r.summarize()
    print("archetype members:", s["behavioral_archetypes"])
    print("impact edges:", s["impact_edges"])
    print("causal edges:", s["causal_edges"])
    print("top motif:", s["top_motif"])
    print("\nquickstart OK")


if __name__ == "__main__":
    main()
