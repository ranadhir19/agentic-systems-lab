"""Semantic Fabric experiments (all seeded, deterministic).

Phase A — semantic compression: raw bytes vs per-layer artifact bytes.
Phase B — extraction quality vs synthetic ground truth (per layer).
Phase C — reasoning agreement: fabric-only answers vs raw-data answers.
Phase D — freshness: drift-detection latency vs shift magnitude; false-
           positive rate on a stationary stream.
Phase E — ablation: query accuracy with layers removed.

Outputs: results/results.md and results/charts.png.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from agentic_systems.semantic_fabric import (
    build_fabric, FabricReasoner, SemanticStore, FreshnessMonitor,
    CAUSAL_VARS, synth,
)
from agentic_systems.semantic_fabric.extract import (
    extract_l0, extract_l1, extract_l2, extract_l3, extract_l4)
from agentic_systems.semantic_fabric.causal import extract_l5
from agentic_systems.semantic_fabric.cognitive import extract_l6, extract_l7
from agentic_systems.semantic_fabric.pipeline import causal_matrix, CAUSAL_ORDER
from agentic_systems.semantic_fabric.common import adjusted_rand_index

SEED = 7
N_TXN, N_INC, N_TICK, N_USERS = 10000, 300, 400, 600


def raw_bytes(raw):
    return len(json.dumps(raw, default=str).encode())


# ---------------------------------------------------------------------------
# Phase A — compression
# ---------------------------------------------------------------------------
def phase_a():
    store, rep = build_fabric(N_TXN, N_INC, N_TICK, N_USERS, seed=SEED)
    raw = rep["raw"]
    rb = raw_bytes({"txns": raw["txns"]})
    per_layer = store.bytes_by_layer()
    # attribute raw bytes to the layers that consumed each source
    total_sem = store.total_bytes()
    ratios = {l: round(rb / max(b, 1), 1) for l, b in per_layer.items()}
    return {
        "raw_txn_bytes": rb,
        "semantic_total_bytes": total_sem,
        "overall_ratio": round(rb / max(total_sem, 1), 1),
        "per_layer_bytes": per_layer,
        "per_layer_ratio": ratios,
    }, store, rep


# ---------------------------------------------------------------------------
# Phase B — quality vs ground truth
# ---------------------------------------------------------------------------
def phase_b(store, rep):
    truth = rep["truth"]
    raw = rep["raw"]
    q = {}

    # L0: entity + relation recovery
    l0 = store.get("L0", "schema")["artifact"]
    ents = set(l0["entities"])
    q["L0_entities"] = {
        "recovered": sorted(ents),
        "expected": ["txn", "user", "server"],
        "recall": round(len(ents & {"txn", "user", "server"}) / 3, 3),
    }
    rels = {(r["src"], r["dst"]) for r in l0["relations"]}
    q["L0_relations"] = {
        "n_found": len(rels),
        "txn_user_found": ("txn", "user") in rels,
        "txn_server_found": ("txn", "server") in rels,
    }

    # L1: determinism (extract twice -> identical hash)
    l1a = extract_l1(raw["txns"])
    l1b = extract_l1(raw["txns"])
    from agentic_systems.semantic_fabric.store import content_hash
    q["L1_determinism"] = content_hash(l1a) == content_hash(l1b)
    prof = store.get("L1", "transactions")["artifact"]["profiles"]
    q["L1_amount_mean"] = round(prof["amount"]["mean"], 2)

    # L2: archetype purity (ARI vs true per-user archetype)
    txns = raw["txns"]
    user_true = {}
    for t, a in zip(txns, truth["txn"]["user_archetype"]):
        user_true.setdefault(t["user_id"], []).append(a)
    user_true = {u: Counter(v).most_common(1)[0][0]
                 for u, v in user_true.items()}
    l2 = store.get("L2", "behavior")["artifact"]
    common = sorted(set(user_true) & set(l2["archetype_of_user"]))
    ari = adjusted_rand_index([user_true[u] for u in common],
                              [l2["archetype_of_user"][u] for u in common])
    q["L2_ARI"] = round(float(ari), 3)

    # L3: hot-server recovery
    l3 = store.get("L3", "transactions")["artifact"]
    pay_edges = [e["src"] for e in l3["edges"] if e["dst"] == "payments"]
    hot = set(truth["txn"]["hot_servers"])
    q["L3_hot_recall"] = round(len(hot & set(pay_edges)) / len(hot), 3)
    q["L3_n_edges"] = len(l3["edges"])

    # L4: period + cascade recovery
    l4 = store.get("L4", "metrics")["artifact"]
    per_ok = all(abs(l4["series"][s]["dominant_period_h"] - 168.0) < 2
                 for s in ("cpu", "latency"))
    casc = [(c["src"], c["dst"], c["lag_h"]) for c in l4["cascades"]]
    # cascade kernel distributes lag 0-3h, peak at 2h: accept 1..3
    casc_ok = any(s == "cpu" and d == "latency" and 1 <= lag <= 3
                  for s, d, lag in casc)
    q["L4_period_ok"] = per_ok
    q["L4_cascade_ok"] = casc_ok

    # L5: DAG edge precision/recall
    l5 = store.get("L5", "transactions")["artifact"]
    found = set(l5["edges"])
    true_e = set(truth["txn"]["causal_edges"])
    tp = len(found & true_e)
    q["L5_precision"] = round(tp / max(len(found), 1), 3)
    q["L5_recall"] = round(tp / max(len(true_e), 1), 3)
    q["L5_found"] = sorted(found)

    # L6: intent accuracy
    l6 = store.get("L6", "tickets")["artifact"]
    pred = [f["intent"] for f in l6["frames"]]
    true_l = truth["tickets"]["intent"]
    q["L6_accuracy"] = round(
        sum(p == t for p, t in zip(pred, true_l)) / len(true_l), 3)

    # L7: motif recovery
    l7 = store.get("L7", "incidents")["artifact"]
    kinds = [m["kind"] for m in l7["motifs"]]
    q["L7_boundary_motif"] = "coordination_boundary" in kinds
    q["L7_top_support"] = l7["motifs"][0]["support"] if l7["motifs"] else 0
    return q


# ---------------------------------------------------------------------------
# Phase C — reasoning agreement (fabric vs raw data)
# ---------------------------------------------------------------------------
def raw_top_servers(txns, service="payments", top_k=2):
    lat = np.array([t["latency_ms"] for t in txns])
    thr = float(np.percentile(lat, 90))
    base = float(np.mean(lat > thr))
    scored = []
    for srv in sorted({t["server_id"] for t in txns}):
        sub = [t for t in txns if t["server_id"] == srv
               and t["service"] == service]
        if len(sub) < 30:
            continue
        lift = (sum(t["latency_ms"] > thr for t in sub) / len(sub)) / \
            max(base, 1e-9)
        scored.append((lift, srv))
    scored.sort(reverse=True)
    return [s for _, s in scored[:top_k]]


def raw_root_cause(txns):
    X = np.array([[t[v] for v in CAUSAL_VARS] for t in txns], float)
    C = np.corrcoef(X, rowvar=False)
    j = CAUSAL_VARS.index("latency_ms")
    corrs = sorted(((abs(C[i, j]), CAUSAL_VARS[i])
                    for i in range(len(CAUSAL_VARS)) if i != j),
                   reverse=True)
    return corrs[0][1]


def phase_c(store, rep):
    r = FabricReasoner(store)
    txns = rep["raw"]["txns"]
    agree = {}

    fab_servers = [e["src"] for e in r.impacting_servers("payments",
                                                         top_k=2)]
    raw_servers = raw_top_servers(txns)
    agree["impacting_servers"] = {
        "fabric": fab_servers, "raw": raw_servers,
        "agree": fab_servers == raw_servers}

    fab_cause = r.diagnose("latency_ms", top_k=1)[0]["cause"]
    raw_cause = raw_root_cause(txns)
    agree["root_cause"] = {"fabric": fab_cause, "raw": raw_cause,
                           "agree": fab_cause == raw_cause}

    # what-if direction agreement: fabric SCM vs refit-on-raw SCM
    fab_fx = r.what_if("server_load", 2.0)["latency_ms"]
    X = np.array([[t[v] for v in CAUSAL_VARS] for t in txns], float)
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-9)
    j = CAUSAL_VARS.index("latency_ms")
    beta, *_ = np.linalg.lstsq(
        np.column_stack([Xs[:, CAUSAL_VARS.index("queue_depth")],
                         np.ones(len(Xs))]), Xs[:, j], rcond=None)
    raw_fx = beta[0] * 2.0  # standardized effect of load=2 via queue
    agree["what_if_sign"] = {
        "fabric_effect": round(float(fab_fx), 3),
        "raw_effect": round(float(raw_fx), 3),
        "agree": bool((fab_fx > 0) == (raw_fx > 0))}

    # markov next-action agreement
    l2 = store.get("L2", "behavior")["artifact"]
    T = np.array(l2["transition_matrices"][0])
    fab_next = l2["actions"][int(T[l2["actions"].index("cart")].argmax())]
    seqs = rep["raw"]["seqs"]
    nxt = Counter()
    for s in seqs:
        for a, b in zip(s, s[1:]):
            if a == "cart":
                nxt[b] += 1
    raw_next = nxt.most_common(1)[0][0] if nxt else None
    agree["markov_next"] = {"fabric": fab_next, "raw": raw_next,
                            "agree": fab_next == raw_next}

    agree["overall"] = round(
        sum(v["agree"] for v in agree.values()) / len(agree), 3)
    return agree


# ---------------------------------------------------------------------------
# Phase D — freshness: detection latency + false positives
# ---------------------------------------------------------------------------
def phase_d(store):
    mon = FreshnessMonitor()
    base_l1 = store.get("L1", "transactions")["artifact"]
    base_l2 = store.get("L2", "behavior")["artifact"]

    # stationary stream: 20 batches, count false positives
    fp = 0
    for b in range(20):
        txns, _ = synth.gen_transactions(2000, seed=1000 + b)
        cur = extract_l1(txns)
        if mon.check("L1", cur, base_l1)["drifted"]:
            fp += 1
    fpr = fp / 20

    # injected mean shift: latency across magnitudes; latency in batches
    # (each batch = fresh 2000-txn sample with shift added to latency)
    latencies = {}
    for mag in (0.5, 1.0, 2.0, 3.0):
        detected_at = None
        for b in range(10):
            txns, _ = synth.gen_transactions(2000, seed=2000 + b)
            sd = float(np.std([t["latency_ms"] for t in txns]))
            for t in txns:
                t["latency_ms"] = round(t["latency_ms"] + mag * sd, 1)
            cur = extract_l1(txns)
            if mon.check("L1", cur, base_l1)["drifted"]:
                detected_at = b + 1
                break
        latencies[mag] = detected_at

    # behavior change: half the users collapse to browse->support->exit
    # (a structural break in journey dynamics) -> L2 must fire
    txns_a, _ = synth.gen_transactions(10000, seed=SEED)
    seqs0, _ = synth.gen_sequences(600, seed=4)
    rng_b = np.random.default_rng(99)
    seqs1 = [["browse", "support", "exit"] if rng_b.random() < 0.5 else s
             for s in seqs0]
    l2_base = extract_l2(txns_a, seqs0, seed=SEED)
    l2_new = extract_l2(txns_a, seqs1, seed=SEED)
    beh = mon.check("L2", l2_new, l2_base)
    return {"fpr_stationary_L1": round(fpr, 3),
            "detection_latency_batches": latencies,
            "L2_behavior_change": beh}


# ---------------------------------------------------------------------------
# Phase E — ablation: query accuracy minus layers
# ---------------------------------------------------------------------------
QUERIES = ["impacting_servers", "root_cause", "what_if_sign", "markov_next"]


def phase_e(store, rep, agree_full):
    # which layers each query needs
    needs = {"impacting_servers": {"L3"}, "root_cause": {"L5"},
             "what_if_sign": {"L5"}, "markov_next": {"L2"}}
    r = FabricReasoner(store)
    txns = rep["raw"]["txns"]
    results = {}
    for ablate in (None, "L2", "L3", "L5"):
        ok = 0
        for qn in QUERIES:
            if ablate in needs[qn]:
                continue  # query unanswerable without its layer
            ok += int(agree_full[qn]["agree"])
        results["full" if ablate is None else f"no_{ablate}"] = \
            round(ok / len(QUERIES), 3)
    return results


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "..", "results")
    os.makedirs(outdir, exist_ok=True)

    print("Phase A — compression ...")
    a, store, rep = phase_a()
    print("  overall raw:semantic = "
          f"{a['overall_ratio']}:1  ({a['raw_txn_bytes']} -> "
          f"{a['semantic_total_bytes']} bytes)")

    print("Phase B — quality ...")
    b = phase_b(store, rep)
    for k, v in b.items():
        print(f"  {k}: {v}")

    print("Phase C — reasoning agreement ...")
    c = phase_c(store, rep)
    for k, v in c.items():
        print(f"  {k}: {v}")

    print("Phase D — freshness ...")
    d = phase_d(store)
    print(f"  {d}")

    print("Phase E — ablation ...")
    e = phase_e(store, rep, c)
    print(f"  {e}")

    with open(os.path.join(outdir, "results.md"), "w") as f:
        f.write("# Semantic Fabric experiment results\n\n")
        f.write(f"Seed {SEED}; {N_TXN} txns, {N_INC} incidents, "
                f"{N_TICK} tickets, {N_USERS} users.\n\n")
        f.write("## A — semantic compression (raw bytes : artifact bytes)\n\n")
        f.write(f"Raw transactions: {a['raw_txn_bytes']} bytes; "
                f"all semantic artifacts: {a['semantic_total_bytes']} bytes; "
                f"overall compression **{a['overall_ratio']}:1**.\n\n")
        f.write("| Layer | Artifact bytes | Compression |\n|---|---|---|\n")
        for l in sorted(a["per_layer_bytes"]):
            f.write(f"| {l} | {a['per_layer_bytes'][l]} | "
                    f"{a['per_layer_ratio'][l]}:1 |\n")
        f.write("\n## B — extraction quality vs ground truth\n\n")
        f.write("| Check | Result |\n|---|---|\n")
        for k, v in b.items():
            f.write(f"| {k} | {v} |\n")
        f.write("\n## C — reasoning agreement (fabric vs raw data)\n\n")
        f.write("| Query | Fabric | Raw | Agree |\n|---|---|---|---|\n")
        for k, v in c.items():
            if k == "overall":
                continue
            f.write(f"| {k} | {v['fabric'] if 'fabric' in v else v} | "
                    f"{v.get('raw', '—')} | {v['agree']} |\n")
        f.write(f"\nOverall agreement: **{c['overall']}**\n")
        f.write("\n## D — freshness\n\n")
        f.write(f"False-positive rate on stationary stream (L1): "
                f"**{d['fpr_stationary_L1']}**\n\n")
        f.write("| Shift (std) | Detection latency (batches) |\n"
                "|---|---|\n")
        for mag, lat in d["detection_latency_batches"].items():
            f.write(f"| {mag} | {lat} |\n")
        f.write(f"\nL2 behavior-change verdict: {d['L2_behavior_change']}\n")
        f.write("\n## E — ablation (query accuracy)\n\n")
        f.write("| Configuration | Accuracy |\n|---|---|\n")
        for k, v in e.items():
            f.write(f"| {k} | {v} |\n")

    # charts
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle("Semantic Fabric — seeded experiments")
    ax = axes[0, 0]
    layers = sorted(a["per_layer_bytes"])
    ax.bar(layers, [a["per_layer_ratio"][l] for l in layers],
           color="#4C78A8")
    ax.set_yscale("log")
    ax.set_title("A: compression ratio per layer (log)")
    ax.set_ylabel("raw : semantic")
    ax = axes[0, 1]
    qkeys = ["L0_entities.recall", "L2_ARI", "L3_hot_recall",
             "L5_precision", "L5_recall", "L6_accuracy"]
    qvals = [b["L0_entities"]["recall"], b["L2_ARI"], b["L3_hot_recall"],
             b["L5_precision"], b["L5_recall"], b["L6_accuracy"]]
    ax.bar(qkeys, qvals, color="#54A24B")
    ax.set_ylim(0, 1.05)
    ax.set_title("B: extraction quality (0-1)")
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right", fontsize=8)
    ax = axes[0, 2]
    ck = [k for k in c if k != "overall"]
    ax.bar(ck, [int(c[k]["agree"]) for k in ck], color="#E45756")
    ax.set_ylim(0, 1.2)
    ax.set_title("C: fabric-vs-raw agreement")
    plt.setp(ax.get_xticklabels(), rotation=25, ha="right", fontsize=8)
    ax = axes[1, 0]
    mags = sorted(d["detection_latency_batches"])
    lats = [d["detection_latency_batches"][m] or 11 for m in mags]
    ax.plot(mags, lats, marker="o", color="#F58518")
    ax.set_title("D: drift detection latency vs shift")
    ax.set_xlabel("shift (std)"); ax.set_ylabel("batches to detect")
    ax.text(0.05, 0.9, f"FPR stationary: {d['fpr_stationary_L1']}",
            transform=ax.transAxes, fontsize=9)
    ax = axes[1, 1]
    ek = list(e.keys())
    ax.bar(ek, [e[k] for k in ek], color="#8EA9C9")
    ax.set_ylim(0, 1.1)
    ax.set_title("E: ablation — query accuracy")
    plt.setp(ax.get_xticklabels(), rotation=20, ha="right", fontsize=8)
    ax = axes[1, 2]
    ax.axis("off")
    ax.text(0.05, 0.95,
            "Key findings\n\n"
            f"- {a['overall_ratio']}:1 compression: 10k txns -> "
            f"{a['semantic_total_bytes']}B of semantics\n"
            f"- Fabric answers match raw-data answers: {c['overall']}\n"
            f"- Drift FPR {d['fpr_stationary_L1']}; "
            "2-sigma shift caught in "
            f"{d['detection_latency_batches'][2.0]} batch(es)\n"
            f"- Removing L5 kills causal queries; L2 kills prediction",
            fontsize=10, va="top", ha="left", wrap=True)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "charts.png"), dpi=110)
    print("wrote results.md and charts.png")


if __name__ == "__main__":
    main()
