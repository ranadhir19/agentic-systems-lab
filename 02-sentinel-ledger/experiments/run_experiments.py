"""Sentinel experiments.

1. Clean replay: 600 decisions, replay all -> expect 100% MATCH.
2. Fault injection (150 decisions each):
     - seed_perturbed : replay with seed+1            -> DIVERGED
     - tool_drift     : one tool result mutated       -> DIVERGED (+located step)
     - missing_seed   : seed stripped from the record -> UNREPLAYABLE
     - ledger_tamper  : one entry's output edited     -> chain verify fails
3. Chain verification timing vs ledger size.

Outputs: results/results.md and results/charts.png.
"""
from __future__ import annotations

import copy
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agentic_systems.sentinel import EvidenceLedger, ReplayEngine
from agentic_systems.sentinel import SimulatedAgent, record_decision

N_CLEAN = 600
N_FAULT = 150


def build_ledger(n: int, seed_base: int = 1000):
    ledger = EvidenceLedger()
    agent = SimulatedAgent()
    records = []
    for i in range(n):
        tools = [(f"tool:{k}", f"args-{i}-{k}", f"result-{i}-{k}")
                 for k in ("search", "lookup")]
        rec = record_decision(agent, ledger, f"d-{seed_base + i}",
                              f"inputs-{seed_base + i}",
                              "policy-v3", seed_base + i, tools)
        records.append(rec)
    return ledger, agent, records


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "..", "results")
    os.makedirs(outdir, exist_ok=True)

    summary = {}

    # 1. clean replay -----------------------------------------------------
    ledger, agent, records = build_ledger(N_CLEAN)
    engine = ReplayEngine(agent.execute)
    engine.stepwise = agent.stepwise  # enable divergence location
    t0 = time.perf_counter()
    verdicts = [engine.replay(r) for r in records]
    dt = time.perf_counter() - t0
    match = sum(1 for v in verdicts if v.verdict == "MATCH")
    summary["clean_match_rate"] = match / N_CLEAN
    summary["replay_ms_per_decision"] = dt / N_CLEAN * 1000

    # 2a. seed perturbed --------------------------------------------------
    div = 0
    for r in records[:N_FAULT]:
        bad = copy.deepcopy(r)
        bad.model_params["seed"] += 1
        if engine.replay(bad).verdict == "DIVERGED":
            div += 1
    summary["seed_perturb_detected"] = div / N_FAULT

    # 2b. tool drift ------------------------------------------------------
    div, located = 0, 0
    for r in records[:N_FAULT]:
        bad = copy.deepcopy(r)
        bad.tool_calls[0].result_hash = "tampered-result"
        v = engine.replay(bad)
        if v.verdict == "DIVERGED":
            div += 1
            if v.first_divergence:
                located += 1
    summary["tool_drift_detected"] = div / N_FAULT
    summary["tool_drift_located"] = located / max(1, div)

    # 2c. missing seed ----------------------------------------------------
    unr = 0
    for r in records[:N_FAULT]:
        bad = copy.deepcopy(r)
        del bad.model_params["seed"]
        if engine.replay(bad).verdict == "UNREPLAYABLE":
            unr += 1
    summary["missing_seed_flagged"] = unr / N_FAULT

    # 2d. ledger tamper ---------------------------------------------------
    ledger2, _, records2 = build_ledger(200, seed_base=9000)
    records2[100].output_hash = "forged"
    ok, idx = ledger2.verify_chain()
    summary["tamper_detected"] = (not ok)
    summary["tamper_index"] = idx

    # 3. verify timing vs size ---------------------------------------------
    sizes, times = [], []
    for n in (100, 500, 1000, 2000, 4000):
        lg, _, _ = build_ledger(n, seed_base=50000 + n)
        t0 = time.perf_counter()
        lg.verify_chain()
        times.append((time.perf_counter() - t0) * 1000)
        sizes.append(n)
    summary["verify_sizes"] = sizes
    summary["verify_ms"] = times

    # ---- write markdown --------------------------------------------------
    with open(os.path.join(outdir, "results.md"), "w") as f:
        f.write("# Sentinel experiment results\n\n")
        f.write(f"Clean replay: {N_CLEAN} decisions, "
                f"{summary['clean_match_rate']:.1%} MATCH, "
                f"{summary['replay_ms_per_decision']:.2f} ms/decision.\n\n")
        f.write("| Fault injected | n | Detected |\n")
        f.write("|---|---|---|\n")
        f.write(f"| seed perturbed (+1) | {N_FAULT} | "
                f"{summary['seed_perturb_detected']:.1%} DIVERGED |\n")
        f.write(f"| tool result mutated | {N_FAULT} | "
                f"{summary['tool_drift_detected']:.1%} DIVERGED "
                f"({summary['tool_drift_located']:.0%} step-located) |\n")
        f.write(f"| seed stripped | {N_FAULT} | "
                f"{summary['missing_seed_flagged']:.1%} UNREPLAYABLE |\n")
        f.write(f"| ledger entry forged | 1 | "
                f"{'detected at index ' + str(summary['tamper_index']) if summary['tamper_detected'] else 'MISSED'} |\n")
        f.write("\nChain verification is O(n):\n\n")
        f.write("| entries | verify ms |\n|---|---|\n")
        for s, t in zip(sizes, times):
            f.write(f"| {s} | {t:.1f} |\n")

    # ---- charts ----------------------------------------------------------
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle("Sentinel — replay fidelity and ledger verification")
    ax = axes[0]
    ax.bar(["clean\nMATCH", "seed perturb\nDIVERGED", "tool drift\nDIVERGED",
            "missing seed\nUNREPLAYABLE"],
           [summary["clean_match_rate"], summary["seed_perturb_detected"],
            summary["tool_drift_detected"], summary["missing_seed_flagged"]],
           color=["#54A24B", "#E45756", "#F58518", "#4C78A8"])
    ax.set_ylim(0, 1.05)
    ax.set_title("Fault-injection detection rate")
    ax = axes[1]
    ax.plot(sizes, times, marker="o", color="#4C78A8")
    ax.set_title("Chain verification time vs ledger size")
    ax.set_xlabel("entries")
    ax.set_ylabel("ms")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "charts.png"), dpi=110)

    for k, v in summary.items():
        if not isinstance(v, list):
            print(f"{k} = {v}")
    print("wrote results.md and charts.png")


if __name__ == "__main__":
    main()
