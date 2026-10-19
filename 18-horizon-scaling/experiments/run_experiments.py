"""Horizon-scaling experiments (all seeded).

Phase (a) -- decay curve: baseline success vs horizon N = 5, 10, 20, 40,
  80; log-linear fit of success(N) = q^N.
Phase (b) -- mitigation curves: checkpoints(k=5), hierarchy(s=10),
  voting(n=3), recovery(k=5) at the same horizons.
Phase (c) -- checkpoint-interval sweep at N=40: k in {2, 5, 10, 20, 40}.
Phase (d) -- cost-per-success table from (b) data: cheapest per horizon.
Phase (e) -- error mix at N=40: corruption-heavy / balanced / fatal-heavy.
Phase (f) -- interaction at N=80: hierarchy vs checkpoints vs both.

Outputs: results/results.md and results/charts.png.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np

matplotlib_use = "Agg"
import matplotlib
matplotlib.use(matplotlib_use)
import matplotlib.pyplot as plt

from agentic_systems.horizon_scaling import (
    default_spec, mix_spec, ERROR_MIXES,
    run_baseline, run_checkpoints, run_hierarchy, run_recovery,
    run_voting, run_hierarchy_checkpoints,
    theoretical_per_step_q, summarize, fit_exponential_decay,
)

SEED = 7
HORIZONS = [5, 10, 20, 40, 80]
TRIALS = 2000

AGENTS = {
    "baseline": lambda spec, rng: run_baseline(spec, rng),
    "checkpoints(k=5)": lambda spec, rng: run_checkpoints(spec, rng, k=5),
    "hierarchy(s=10)": lambda spec, rng: run_hierarchy(spec, rng, subtask_size=10),
    "voting(n=3)": lambda spec, rng: run_voting(spec, rng, n=3),
    "recovery(k=5)": lambda spec, rng: run_recovery(spec, rng, k=5),
}


def run_grid(agent_fn, horizons, trials, seed_base, spec_fn=default_spec):
    out = {}
    for n in horizons:
        spec = spec_fn(n)
        reps = [agent_fn(spec, np.random.default_rng(seed_base + i))
                for i in range(trials)]
        out[n] = summarize(reps)
    return out


def phase_ab():
    print("== (a,b) decay curves ==")
    curves = {}
    seed_base = SEED * 1000
    for name, fn in AGENTS.items():
        curves[name] = run_grid(fn, HORIZONS, TRIALS, seed_base)
        seed_base += 100_000
        row = " ".join(f"N={n}:{curves[name][n]['success_rate']:.3f}"
                       for n in HORIZONS)
        print(f"{name:18s} {row}")
    return curves


def phase_c():
    print("== (c) checkpoint-interval sweep, N=40 ==")
    out = {}
    for k in [2, 5, 10, 20, 40]:
        spec = default_spec(40)
        reps = [run_checkpoints(spec, np.random.default_rng(900_000 + i), k=k)
                for i in range(TRIALS)]
        out[k] = summarize(reps)
        print(f"k={k:2d} success={out[k]['success_rate']:.3f} "
              f"cps={out[k]['cost_per_success']:.1f}")
    return out


def phase_e():
    print("== (e) error mix, N=40 ==")
    out = {}
    for mix in ERROR_MIXES:
        out[mix] = {}
        for name, fn in AGENTS.items():
            spec = mix_spec(40, mix)
            reps = [fn(spec, np.random.default_rng(700_000 + i))
                    for i in range(TRIALS)]
            out[mix][name] = summarize(reps)
        row = " ".join(f"{n}:{out[mix][n]['success_rate']:.3f}"
                       for n in AGENTS)
        print(f"{mix:16s} {row}")
    return out


def phase_f():
    print("== (f) interaction, N=80 ==")
    spec = default_spec(80)
    cfgs = {
        "checkpoints(k=5)": lambda s, r: run_checkpoints(s, r, k=5),
        "hierarchy(s=10)": lambda s, r: run_hierarchy(s, r, subtask_size=10),
        "both": lambda s, r: run_hierarchy_checkpoints(s, r, subtask_size=10, k=5),
    }
    out = {}
    for name, fn in cfgs.items():
        reps = [fn(spec, np.random.default_rng(500_000 + i))
                for i in range(TRIALS)]
        out[name] = summarize(reps)
        print(f"{name:18s} success={out[name]['success_rate']:.3f} "
              f"cps={out[name]['cost_per_success']:.1f}")
    return out


def write_results(outdir, curves, sweep, mixes, inter):
    lines = ["# Horizon-scaling experiment results",
             "",
             f"Seed {SEED}; {TRIALS} trials per cell; "
             "default task family p_fatal=0.01, p_err=0.03, cascade=2.0, "
             "detect_check=0.8.",
             "",
             "## (a,b) Decay curves: success rate vs horizon",
             "",
             "| Agent | " + " | ".join(f"N={n}" for n in HORIZONS) + " |",
             "|---|---|---|---|---|---|",
             ]
    for name in AGENTS:
        row = " | ".join(f"{curves[name][n]['success_rate']:.4f}"
                         for n in HORIZONS)
        lines.append(f"| {name} | {row} |")
    lines += ["",
              "Exponential fit success(N) = q^N (log-linear regression):",
              "",
              "| Agent | q_hat (per-step) | R^2 |",
              "|---|---|---|"]
    for name in AGENTS:
        sr = [curves[name][n]["success_rate"] for n in HORIZONS]
        q, r2 = fit_exponential_decay(HORIZONS, sr)
        lines.append(f"| {name} | {q:.5f} | {r2:.4f} |")
    q_theory = theoretical_per_step_q(default_spec(10))
    lines += ["",
              f"Theoretical baseline per-step q = (1-pf)(1-pe) = {q_theory:.5f}.",
              "",
              "## (d) Cost per successful task",
              "",
              "| Agent | " + " | ".join(f"N={n}" for n in HORIZONS) + " |",
              "|---|---|---|---|---|---|"]
    for name in AGENTS:
        row = " | ".join(f"{curves[name][n]['cost_per_success']:.1f}"
                         for n in HORIZONS)
        lines.append(f"| {name} | {row} |")
    lines += ["",
              "Cheapest per horizon: " +
              ", ".join(
                  f"N={n}: {min(AGENTS, key=lambda a: curves[a][n]['cost_per_success'])}"
                  f" ({min(curves[a][n]['cost_per_success'] for a in AGENTS):.1f})"
                  for n in HORIZONS) + ".",
              "",
              "## (c) Checkpoint-interval sweep (N=40)",
              "",
              "| k | Success | Mean cost | Cost/success |",
              "|---|---|---|---|"]
    for k in sorted(sweep):
        s = sweep[k]
        lines.append(f"| {k} | {s['success_rate']:.4f} | {s['mean_cost']:.1f} "
                     f"| {s['cost_per_success']:.1f} |")
    best_k = min(sweep, key=lambda k: sweep[k]["cost_per_success"])
    lines += ["",
              f"Optimal k by cost-per-success: **{best_k}**.",
              "",
              "## (e) Error mix (N=40)",
              "",
              "| Mix (pf, pe) | " + " | ".join(AGENTS) + " |",
              "|---|---|---|---|---|---|"]
    for mix, (pf, pe) in ERROR_MIXES.items():
        row = " | ".join(f"{mixes[mix][n]['success_rate']:.4f}" for n in AGENTS)
        lines.append(f"| {mix} ({pf}, {pe}) | {row} |")
    lines += ["",
              "## (f) Interaction (N=80)",
              "",
              "| Config | Success | Cost/success |",
              "|---|---|---|"]
    for name, s in inter.items():
        lines.append(f"| {name} | {s['success_rate']:.4f} "
                     f"| {s['cost_per_success']:.1f} |")
    with open(os.path.join(outdir, "results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def make_charts(outdir, curves, sweep, mixes, inter):
    colors = {"baseline": "#E45756", "checkpoints(k=5)": "#4C78A8",
              "hierarchy(s=10)": "#72B66F", "voting(n=3)": "#F58518",
              "recovery(k=5)": "#9B72CF"}
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Horizon scaling: success decays with horizon; mitigations flatten it "
                 f"(seed {SEED})")

    ax = axes[0, 0]
    for name in AGENTS:
        sr = [curves[name][n]["success_rate"] for n in HORIZONS]
        ax.semilogy(HORIZONS, sr, "o-", label=name, color=colors[name])
    # baseline theory line
    q = theoretical_per_step_q(default_spec(10))
    ax.semilogy(HORIZONS, [q ** n for n in HORIZONS], "k--", lw=1,
                label="theory q^N")
    ax.set_xlabel("horizon N (steps)")
    ax.set_ylabel("task success rate (log)")
    ax.set_title("(a,b) Decay curves")
    ax.legend(fontsize=8)

    ax = axes[0, 1]
    for name in AGENTS:
        cps = [curves[name][n]["cost_per_success"] for n in HORIZONS]
        ax.semilogy(HORIZONS, cps, "o-", label=name, color=colors[name])
    ax.set_xlabel("horizon N (steps)")
    ax.set_ylabel("cost per successful task (log)")
    ax.set_title("(d) Cost per success")
    ax.legend(fontsize=8)

    ax = axes[1, 0]
    ks = sorted(sweep)
    ax2 = ax.twinx()
    ax.bar([str(k) for k in ks],
           [sweep[k]["success_rate"] for k in ks], color="#4C78A8",
           alpha=0.7, label="success")
    ax2.plot([str(k) for k in ks],
             [sweep[k]["cost_per_success"] for k in ks], "o-",
             color="#E45756", label="cost/success")
    ax.set_xlabel("checkpoint interval k (N=40)")
    ax.set_ylabel("success rate", color="#4C78A8")
    ax2.set_ylabel("cost per success", color="#E45756")
    ax.set_title("(c) Checkpoint-interval sweep")

    ax = axes[1, 1]
    x = np.arange(len(ERROR_MIXES))
    w = 0.15
    for i, name in enumerate(AGENTS):
        ax.bar(x + (i - 2) * w,
               [mixes[m][name]["success_rate"] for m in ERROR_MIXES],
               w, label=name, color=colors[name])
    ax.set_xticks(x)
    ax.set_xticklabels(list(ERROR_MIXES.keys()), fontsize=9)
    ax.set_ylabel("success rate (N=40)")
    ax.set_title("(e) Error mix")
    ax.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "charts.png"), dpi=110)
    print("wrote results.md and charts.png")


def main():
    outdir = os.path.join(os.path.dirname(__file__), "..", "results")
    curves = phase_ab()
    sweep = phase_c()
    mixes = phase_e()
    inter = phase_f()
    write_results(outdir, curves, sweep, mixes, inter)
    make_charts(outdir, curves, sweep, mixes, inter)


if __name__ == "__main__":
    main()
