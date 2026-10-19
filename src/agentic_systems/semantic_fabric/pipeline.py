"""End-to-end semantic extraction pipeline.

Raw Reality -> Semantic Extraction (L0..L7) -> Contextual Compression ->
Semantic Persistence (versioned store) -> Reasoning + Retrieval +
Simulation. Raw data is discardable once artifacts are persisted.
"""
from __future__ import annotations

import numpy as np

from . import synth
from .extract import (extract_l0, extract_l1, extract_l2, extract_l3,
                      extract_l4)
from .causal import extract_l5
from .cognitive import extract_l6, extract_l7
from .store import SemanticStore

CAUSAL_VARS = ["server_load", "queue_depth", "latency_ms", "error"]
# causes precede effects: load -> queue -> latency -> error
CAUSAL_ORDER = {"server_load": 0, "queue_depth": 1, "latency_ms": 2,
                "error": 3}


def causal_matrix(txns):
    X = np.array([[r[v] for v in CAUSAL_VARS] for r in txns], float)
    # standardize for stable discovery
    return (X - X.mean(0)) / (X.std(0) + 1e-9)


def build_fabric(n_txns=10000, n_incidents=300, n_tickets=400,
                 n_users=600, seed=0, store=None):
    """Run the full extraction pipeline; persist every artifact.

    Returns (store, report) where report holds per-layer byte sizes and
    the ground-truth bundle for scoring.
    """
    store = store or SemanticStore()
    txns, txn_truth = synth.gen_transactions(n_txns, seed=seed)
    metrics, met_truth = synth.gen_metrics(seed=seed + 1)
    incidents, inc_truth = synth.gen_incidents(n_incidents, seed=seed + 2)
    tickets, tick_truth = synth.gen_tickets(n_tickets, seed=seed + 3)
    seqs, seq_truth = synth.gen_sequences(n_users, seed=seed + 4)

    artifacts = {
        "L0": ("schema", extract_l0(txns)),
        "L1": ("transactions", extract_l1(txns)),
        "L2": ("behavior", extract_l2(txns, seqs, seed=seed)),
        "L3": ("transactions", extract_l3(txns)),
        "L4": ("metrics", extract_l4(metrics)),
        "L5": ("transactions", extract_l5(
            causal_matrix(txns), CAUSAL_VARS, CAUSAL_ORDER)),
        "L6": ("tickets", extract_l6(tickets)),
        "L7": ("incidents", extract_l7(incidents, seed=seed)),
    }
    versions = {}
    for layer, (source, art) in artifacts.items():
        versions[layer] = store.put(layer, source, art,
                                    meta={"seed": seed})
    truth = {"txn": txn_truth, "metrics": met_truth,
             "incidents": inc_truth, "tickets": tick_truth,
             "sequences": seq_truth}
    raw = {"txns": txns, "metrics": metrics, "incidents": incidents,
           "tickets": tickets, "seqs": seqs}
    return store, {"versions": versions, "truth": truth, "raw": raw}
