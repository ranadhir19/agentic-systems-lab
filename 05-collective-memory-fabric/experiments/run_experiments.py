"""CMF experiments.

Compares 4 memory systems on the same seeded observation schedule
(200 ticks, 8 heterogeneous agents, 10 flipping facts, misinformation
injected ticks 80-120):

  1. independent        — no sharing
  2. vector-db          — shared, last-write-wins
  3. provenance         — versioned, majority vote in recency window
  4. cmf (full fabric)  — admission + merge + quorum reconciliation
                          + expiry + revocation

Metrics: task success over time, error propagation on the targeted fact,
recovery time after injection, contradiction rate, per-family success
(cross-model transfer), op latency, admission counts.

Outputs: results/results.md and results/charts.png.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agentic_systems.memory_fabric import (
    MemoryFabric, IndependentMemory, NaiveSharedMemory, ProvenanceMemory,
    build_agents, run)
from agentic_systems.memory_fabric.simulation import (
    INJECT_END, INJECT_START, TICKS, N_SEEDS)

SYSTEMS = [
    ("independent", IndependentMemory),
    ("vector-db", NaiveSharedMemory),
    ("provenance", ProvenanceMemory),
    ("cmf", MemoryFabric),
]


def avg_runs(factory, seeds):
    """Average scalar metrics and time series over seeds."""
    runs = [run(factory(), seed=s) for s in seeds]
    out = {}
    for k in runs[0]:
        v = runs[0][k]
        if isinstance(v, list) and v and isinstance(v[0], (int, float)):
            out[k] = [sum(r[k][i] for r in runs) / len(runs)
                      for i in range(len(v))]
        elif isinstance(v, dict):
            out[k] = {kk: sum(r[k][kk] for r in runs) / len(runs) for kk in v}
        elif isinstance(v, (int, float)):
            out[k] = sum(r[k] for r in runs) / len(runs)
        else:
            out[k] = v
    return out


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "..", "results")
    os.makedirs(outdir, exist_ok=True)
    seeds = list(range(N_SEEDS))

    results = {}
    for name, cls in SYSTEMS:
        results[name] = avg_runs(cls, seeds)
        r = results[name]
        print(f"{name:12s} mean_success={r['mean_success']:.1%} "
              f"inj_success={r['inj_success']:.1%} "
              f"inj_target_wrong={r['inj_target_wrong']:.1%} "
              f"recovery={r['recovery_ticks']:.1f} ticks "
              f"op={r['mean_op_ms_per_tick']:.2f}ms/tick")

    with open(os.path.join(outdir, "results.md"), "w") as f:
        f.write("# Collective Memory Fabric — experiment results\n\n")
        f.write(f"{TICKS} ticks, 8 agents (3 model families), 10 flipping "
                f"facts; misinformation injected ticks {INJECT_START}-"
                f"{INJECT_END} against a flip-free fact. "
                f"Averages over {N_SEEDS} seeds.\n\n")
        f.write("| System | Mean task success | Success during injection | "
                "Targeted-fact wrong rate (injection) | Recovery (ticks) | "
                "Contradictions | Op ms/tick | Admissions |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for name, _ in SYSTEMS:
            r = results[name]
            f.write(f"| {name} | {r['mean_success']:.1%} | "
                    f"{r['inj_success']:.1%} | {r['inj_target_wrong']:.1%} | "
                    f"{r['recovery_ticks']} | {r['contradiction_rate']:.3f} | "
                    f"{r['mean_op_ms_per_tick']:.2f} | {r['admissions']} |\n")
        f.write("\n## Cross-model transfer (per-family task success)\n\n")
        f.write("| System | alpha (0.95) | beta (0.85) | gamma (0.72) |\n"
                "|---|---|---|---|\n")
        for name in ("independent", "cmf"):
            p = results[name]["per_family"]
            f.write(f"| {name} | {p['alpha']:.1%} | {p['beta']:.1%} | "
                    f"{p['gamma']:.1%} |\n")
        cmf = results["cmf"]
        f.write(f"\nCMF internals: {cmf['merges']} merges, "
                f"{cmf['reconciliations']} reconciliations, "
                f"{cmf['rejections']} rejections.\n")

    colors = {"independent": "#8C8C8C", "vector-db": "#E45756",
              "provenance": "#F58518", "cmf": "#4C78A8"}
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f"Collective Memory Fabric — 200-tick benchmark "
                 f"({N_SEEDS}-seed average)")

    ax = axes[0, 0]
    for name, _ in SYSTEMS:
        ax.plot(results[name]["success_ts"], label=name, color=colors[name],
                lw=1.5)
    ax.axvspan(INJECT_START, INJECT_END, color="#E45756", alpha=0.12,
               label="injection")
    ax.set_title("Task success over time")
    ax.set_xlabel("tick")
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    for name, _ in SYSTEMS:
        ax.plot(results[name]["target_wrong_ts"], label=name,
                color=colors[name], lw=1.5)
    ax.axvspan(INJECT_START, INJECT_END, color="#E45756", alpha=0.12)
    ax.set_title("Error propagation: wrong-answer rate (targeted fact)")
    ax.set_xlabel("tick")
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    rec = [results[n]["recovery_ticks"] if results[n]["recovery_ticks"] is not None else -1
           for n, _ in SYSTEMS]
    ax.bar([n for n, _ in SYSTEMS], rec,
           color=[colors[n] for n, _ in SYSTEMS])
    ax.set_title("Recovery ticks after injection ends")

    ax = axes[1, 1]
    fams = ["alpha", "beta", "gamma"]
    x = range(len(fams))
    ax.bar([i - 0.2 for i in x],
           [results["independent"]["per_family"][f] for f in fams],
           0.4, label="independent", color="#8C8C8C")
    ax.bar([i + 0.2 for i in x],
           [results["cmf"]["per_family"][f] for f in fams],
           0.4, label="cmf", color="#4C78A8")
    ax.set_xticks(list(x))
    ax.set_xticklabels(fams)
    ax.set_title("Cross-model transfer: per-family success")
    ax.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "charts.png"), dpi=110)
    print("wrote results.md and charts.png")


if __name__ == "__main__":
    main()
