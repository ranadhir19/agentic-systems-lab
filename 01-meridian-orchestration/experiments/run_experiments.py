"""Meridian ablation experiments.

Compares four architectures over the same 240-task benchmark (seeded):

    A  single                — one orchestrator, fixed worker mapping
    B  vertical              — meta + domain orchestrators, fixed mapping
    C  vertical+horizontal   — B + blackboard peer coordination
    C+ hand-tuned tiers      — C + hand-written difficulty-aware tier rule
    D  meridian (full)       — C + Thompson-sampling router + planner

Metrics: success rate (quality >= 0.70), mean quality, mean cost (USD),
mean latency (simulated seconds), mean worker calls, peer resolutions and
escalations (horizontal layer only), plus the optimizer's learning curve.

Outputs: results/results.md (tables) and results/charts.png.
"""
from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.optimizer import scalar_reward, COST_NORM, LAT_NORM
from src.orchestrators import MeridianSystem, RunConfig
from src.tasks import TaskGenerator

N_TASKS = 240
SEED = 7

CONFIGS = [
    RunConfig("A: single"),
    RunConfig("B: vertical", vertical=True),
    RunConfig("C: vertical+horizontal", vertical=True, horizontal=True),
    RunConfig("C+: +hand-tuned tiers", vertical=True, horizontal=True,
              smart_fixed=True),
    RunConfig("D: meridian (full)", vertical=True, horizontal=True, optimized=True),
]


def mean(xs):
    return sum(xs) / len(xs)


def ci95(xs):
    # normal-approx 95% CI of the mean
    n = len(xs)
    m = mean(xs)
    var = sum((x - m) ** 2 for x in xs) / max(1, n - 1)
    h = 1.96 * math.sqrt(var / n)
    return m - h, m + h


def run_all():
    tasks = TaskGenerator(SEED).generate(N_TASKS)
    rows = []
    learning_curve = None
    for cfg in CONFIGS:
        system = MeridianSystem(cfg, seed=SEED)
        results = [system.run(t) for t in tasks]
        succ = [1.0 if r.success else 0.0 for r in results]
        lo, hi = ci95(succ)
        rows.append({
            "config": cfg.name,
            "success_rate": mean(succ),
            "ci": (lo, hi),
            "quality": mean([r.quality for r in results]),
            "cost": mean([r.cost for r in results]),
            "latency": mean([r.latency for r in results]),
            "calls": mean([r.n_calls for r in results]),
            "peer_res": sum(r.peer_resolutions for r in results),
            "escalations": sum(r.escalations for r in results),
            "objective": mean([scalar_reward(r.quality, r.cost, r.latency)
                               for r in results]),
        })
        if cfg.optimized:
            learning_curve = _learning_trace(system, tasks)
    return rows, learning_curve


def _learning_trace(system, tasks):
    """Replay-free trace: cumulative success rate over the task sequence."""
    sys2 = MeridianSystem(RunConfig("D", vertical=True, horizontal=True,
                                    optimized=True), seed=SEED)
    trace, wins, n = [], 0, 0
    for t in tasks:
        r = sys2.run(t)
        n += 1
        wins += 1 if r.success else 0
        if n % 12 == 0:
            trace.append(wins / n)
    return trace


def write_markdown(rows, path):
    with open(path, "w") as f:
        f.write("# Meridian ablation results\n\n")
        f.write(f"Benchmark: {N_TASKS} tasks, seed {SEED}. "
                "Success = final quality >= 0.70. Cost in USD, latency in "
                "simulated seconds. 95% CIs are normal approximations.\n\n")
        f.write("| Config | Success rate (95% CI) | Mean quality | "
                "Mean cost/task | Mean latency/task | Mean calls | "
                "Scalarized objective | Peer resolutions | Escalations |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            lo, hi = r["ci"]
            f.write(f"| {r['config']} | {r['success_rate']:.1%} "
                    f"({lo:.1%}–{hi:.1%}) | {r['quality']:.3f} | "
                    f"${r['cost']:.4f} | {r['latency']:.1f}s | "
                    f"{r['calls']:.1f} | {r['objective']:.3f} | "
                    f"{r['peer_res']} | {r['escalations']} |\n")
        base = rows[0]
        full = rows[-1]
        f.write("\n## Headline deltas (D vs A)\n\n")
        f.write(f"- Success rate: {base['success_rate']:.1%} -> "
                f"{full['success_rate']:.1%} "
                f"({(full['success_rate'] - base['success_rate']) * 100:+.1f} pp)\n")
        f.write(f"- Mean cost/task: ${base['cost']:.4f} -> ${full['cost']:.4f} "
                f"({(full['cost'] / base['cost'] - 1) * 100:+.1f}%)\n")
        f.write(f"- Mean latency/task: {base['latency']:.1f}s -> "
                f"{full['latency']:.1f}s "
                f"({(full['latency'] / base['latency'] - 1) * 100:+.1f}%)\n")


def write_charts(rows, learning_curve, path):
    labels = [r["config"].split(":")[0] for r in rows]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    fig.suptitle("Meridian ablations — 240-task benchmark (seeded simulation)")

    ax = axes[0, 0]
    vals = [r["success_rate"] for r in rows]
    errs = [(r["success_rate"] - r["ci"][0]) for r in rows]
    ax.bar(labels, vals, yerr=errs, capsize=4, color="#4C78A8")
    ax.set_title("Success rate (95% CI)")
    ax.set_ylim(0, 1)

    ax = axes[0, 1]
    ax.bar(labels, [r["cost"] for r in rows], color="#F58518")
    ax.set_title("Mean cost per task (USD)")

    ax = axes[1, 0]
    ax.bar(labels, [r["latency"] for r in rows], color="#54A24B")
    ax.set_title("Mean latency per task (sim s)")

    ax = axes[1, 1]
    xs = [(i + 1) * 12 for i in range(len(learning_curve))]
    ax.plot(xs, learning_curve, marker="o", ms=3, color="#B279A2")
    ax.set_title("Config D: cumulative success rate (optimizer learning)")
    ax.set_xlabel("tasks seen")
    ax.set_ylim(0, 1)

    fig.tight_layout()
    fig.savefig(path, dpi=110)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "..", "results")
    os.makedirs(outdir, exist_ok=True)
    rows, learning_curve = run_all()
    write_markdown(rows, os.path.join(outdir, "results.md"))
    write_charts(rows, learning_curve, os.path.join(outdir, "charts.png"))
    for r in rows:
        print(f"{r['config']:28s} success={r['success_rate']:.1%} "
              f"quality={r['quality']:.3f} cost=${r['cost']:.4f} "
              f"lat={r['latency']:.1f}s calls={r['calls']:.1f} "
              f"obj={r['objective']:.3f} "
              f"peer={r['peer_res']} esc={r['escalations']}")
    print("wrote results.md and charts.png")


if __name__ == "__main__":
    main()
