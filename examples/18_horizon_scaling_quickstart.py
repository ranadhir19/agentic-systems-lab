"""Horizon-scaling quickstart: the decay curve, measured.

Runs the baseline linear executor plus the best mitigation (hierarchy)
at horizons N = 5..80, prints the success/cost table, and saves the
decay-curve plot to /tmp/horizon_scaling_quickstart.png.

Run:  python3 examples/18_horizon_scaling_quickstart.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agentic_systems.horizon_scaling import (
    default_spec, run_baseline, run_hierarchy, summarize,
    theoretical_per_step_q,
)


def main() -> None:
    horizons = [5, 10, 20, 40, 80]
    trials = 1000
    print(f"{'N':>4} {'baseline':>10} {'hierarchy':>10} "
          f"{'cps_base':>9} {'cps_hier':>9}")
    base_sr, hier_sr = [], []
    for n in horizons:
        spec = default_spec(n)
        b = summarize([run_baseline(spec, np.random.default_rng(7 + i))
                       for i in range(trials)])
        h = summarize([run_hierarchy(
            spec, np.random.default_rng(10_007 + i), subtask_size=10)
            for i in range(trials)])
        base_sr.append(b["success_rate"])
        hier_sr.append(h["success_rate"])
        print(f"{n:>4} {b['success_rate']:>10.3f} {h['success_rate']:>10.3f} "
              f"{b['cost_per_success']:>9.1f} {h['cost_per_success']:>9.1f}")

    q = theoretical_per_step_q(default_spec(10))
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.semilogy(horizons, base_sr, "o-", color="#E45756", label="baseline")
    ax.semilogy(horizons, hier_sr, "o-", color="#72B66F",
                label="hierarchy (s=10)")
    ax.semilogy(horizons, [q ** n for n in horizons], "k--", lw=1,
                label="theory q^N")
    ax.set_xlabel("horizon N (steps)")
    ax.set_ylabel("task success rate (log scale)")
    ax.set_title("Horizon scaling: baseline decays exponentially; "
                 "hierarchy flattens the curve")
    ax.legend()
    fig.tight_layout()
    out = "/tmp/horizon_scaling_quickstart.png"
    fig.savefig(out, dpi=110)
    print(f"\nAt N=80: baseline {base_sr[-1]:.3f} vs hierarchy {hier_sr[-1]:.3f}.")
    print(f"Plot saved to {out}")


if __name__ == "__main__":
    main()
