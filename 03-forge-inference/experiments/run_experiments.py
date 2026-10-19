"""Forge experiments: scheduling policies x load levels.

Policies: static-fcfs | continuous | continuous-srpt
Loads (Poisson arrivals): 0.8 / 2.0 / 4.0 req/s  (low / medium / high)

1500 requests per cell, seed 42. Outputs results/results.md + charts.png.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agentic_systems.forge import Engine, generate_requests

POLICIES = ["static-fcfs", "continuous", "continuous-srpt"]
LOADS = [(0.0008, "low (0.8 rps)"), (0.002, "medium (2 rps)"), (0.004, "high (4 rps)")]
N = 1500


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "..", "results")
    os.makedirs(outdir, exist_ok=True)

    table = {}
    for lam, label in LOADS:
        reqs = generate_requests(N, lam, seed=42)
        for pol in POLICIES:
            # fresh copies: Engine mutates requests
            import copy
            stats = Engine(pol).run(copy.deepcopy(reqs))
            table[(label, pol)] = stats.report()
            r = table[(label, pol)]
            print(f"{label:16s} {pol:16s} e2e={r['mean_e2e_ms']:8.0f}ms "
                  f"p99={r['p99_e2e_ms']:8.0f}ms ttft={r['mean_ttft_ms']:7.0f}ms "
                  f"thr={r['throughput_rps']:.2f}rps util={r['mean_kv_util']:.0%}")

    with open(os.path.join(outdir, "results.md"), "w") as f:
        f.write("# Forge experiment results\n\n")
        f.write(f"{N} requests per cell, seed 42. Times in ms.\n\n")
        f.write("| Load | Policy | Mean e2e | p99 e2e | Mean TTFT | "
                "Throughput | KV util |\n|---|---|---|---|---|---|---|\n")
        for lam, label in LOADS:
            for pol in POLICIES:
                r = table[(label, pol)]
                f.write(f"| {label} | {pol} | {r['mean_e2e_ms']:.0f} | "
                        f"{r['p99_e2e_ms']:.0f} | {r['mean_ttft_ms']:.0f} | "
                        f"{r['throughput_rps']:.2f} | {r['mean_kv_util']:.0%} |\n")

    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    fig.suptitle("Forge — scheduling policy vs load (seeded simulation)")
    labels = [l for _, l in LOADS]
    xs = range(len(labels))
    width = 0.25
    colors = {"static-fcfs": "#E45756", "continuous": "#4C78A8",
              "continuous-srpt": "#54A24B"}
    for i, pol in enumerate(POLICIES):
        axes[0].bar([x + (i - 1) * width for x in xs],
                    [table[(l, pol)]["mean_e2e_ms"] for _, l in LOADS],
                    width, label=pol, color=colors[pol])
        axes[1].bar([x + (i - 1) * width for x in xs],
                    [table[(l, pol)]["p99_e2e_ms"] for _, l in LOADS],
                    width, label=pol, color=colors[pol])
        axes[2].bar([x + (i - 1) * width for x in xs],
                    [table[(l, pol)]["throughput_rps"] for _, l in LOADS],
                    width, label=pol, color=colors[pol])
    axes[0].set_title("Mean end-to-end latency (ms)")
    axes[1].set_title("p99 end-to-end latency (ms)")
    axes[2].set_title("Throughput (req/s)")
    for ax in axes:
        ax.set_xticks(list(xs))
        ax.set_xticklabels([l.split(" ")[0] for _, l in LOADS])
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "charts.png"), dpi=110)
    print("wrote results.md and charts.png")


if __name__ == "__main__":
    main()
