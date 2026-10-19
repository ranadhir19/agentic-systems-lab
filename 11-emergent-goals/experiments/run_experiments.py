"""Hypothesis battery for emergent goals.

Runs 6 seeds x 4 ablation conditions x 1500 steps, then writes
results/results.md (tables + effect sizes) and results/charts.png.

Hypotheses (fixed in DESIGN.md before results were generated):
  H1: full > no-comm on self-generated goal count
  H2: link maintenance (away from sources) and caching emerge in full
      but not in ablated controls
  H3: communication couples to goal generation (social goal fraction)
  H4: full agents survive longer than extrinsic-only agents
  H5: goal diversity saturates (predicted negative: no sustained
      open-endedness at this scale)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..",
                                "src"))

import numpy as np

from agentic_systems.emergent_goals import (CONDITIONS, cohens_d,
                                            run_condition)

SEEDS = [11, 22, 33, 44, 55, 66]
ORDER = ["full", "no-comm", "extrinsic-only", "no-goalgen"]
METRICS = ["n_imagined", "adoption_rate", "diversity_cells", "diversity_dist",
           "comm_rate", "link_neighbors", "link_away", "cache_ratio",
           "lifetime", "deposits", "comm_goal_lift", "social_goal_frac",
           "token_entropy"]
LABELS = {
    "n_imagined": "Self-generated goals",
    "adoption_rate": "Goal adoption rate",
    "diversity_cells": "Goal diversity (distinct cells)",
    "diversity_dist": "Goal diversity (mean pairwise dist)",
    "comm_rate": "Tokens / 100 agent-steps",
    "link_neighbors": "Mean neighbours (overall)",
    "link_away": "Mean neighbours (away from sources)",
    "cache_ratio": "Cache ratio (withheld / collected)",
    "lifetime": "Mean lifetime (steps)",
    "deposits": "Deposits (extrinsic return)",
    "comm_goal_lift": "Comm->goal lift (20-step window)",
    "social_goal_frac": "Social goal fraction",
    "token_entropy": "Token context entropy (nats)",
}


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    resdir = os.path.join(here, "..", "results")
    os.makedirs(resdir, exist_ok=True)
    results = {}
    for cond in ORDER:
        print(f"running {cond} ...", flush=True)
        results[cond] = run_condition(cond, SEEDS)

    def arr(cond, key):
        return np.array([r[key] for r in results[cond]], dtype=float)

    # ---- results.md ----
    lines = []
    lines.append("# Emergent Goals — Results\n")
    lines.append(f"Seeds: {SEEDS}; 10 agents; 1500 steps/episode; "
                 f"means +- SD across seeds.\n")
    lines.append("## Per-condition means\n")
    lines.append("| Metric | " + " | ".join(ORDER) + " |")
    lines.append("|---|" + "---|" * len(ORDER))
    for key in METRICS:
        row = []
        for cond in ORDER:
            v = arr(cond, key)
            v = v[~np.isnan(v)]
            row.append(f"{v.mean():.3f} +- {v.std():.3f}" if len(v)
                       else "n/a")
        lines.append(f"| {LABELS[key]} | " + " | ".join(row) + " |")
    lines.append("")
    lines.append("## Effect sizes: full vs each ablation (Cohen's d)\n")
    lines.append("| Metric | full vs no-comm | full vs extrinsic-only "
                 "| full vs no-goalgen |")
    lines.append("|---|---|---|---|")
    for key in METRICS:
        ds = []
        for cond in ORDER[1:]:
            x = arr("full", key)
            y = arr(cond, key)
            x = x[~np.isnan(x)]
            y = y[~np.isnan(y)]
            ds.append(f"{cohens_d(x, y):+.2f}" if len(x) and len(y)
                      else "n/a")
        lines.append(f"| {LABELS[key]} | " + " | ".join(ds) + " |")
    lines.append("")
    lines.append("## Hypothesis verdicts\n")
    fi = arr("full", "n_imagined")
    nc = arr("no-comm", "n_imagined")
    lines.append(f"- H1 (comm catalyzes goal generation): full "
                 f"{fi.mean():.1f} vs no-comm {nc.mean():.1f}, "
                 f"d={cohens_d(fi, nc):+.2f}.")
    la_f, la_n = arr("full", "link_away"), arr("no-comm", "link_away")
    ca_f = arr("full", "cache_ratio")
    lines.append(f"- H2 (continuity behaviors): link-away full "
                 f"{la_f.mean():.2f} vs no-comm {la_n.mean():.2f} "
                 f"(d={cohens_d(la_f, la_n):+.2f}); cache full "
                 f"{ca_f.mean():.3f}.")
    sg = arr("full", "social_goal_frac")
    lines.append(f"- H3 (comm-goal coupling): social goal fraction full "
                 f"{sg.mean():.3f}; comm->goal lift "
                 f"{arr('full', 'comm_goal_lift').mean():.2f}.")
    lf, le = arr("full", "lifetime"), arr("extrinsic-only", "lifetime")
    lines.append(f"- H4 (survival dividend): full {lf.mean():.0f} vs "
                 f"extrinsic-only {le.mean():.0f} steps "
                 f"(d={cohens_d(lf, le):+.2f}).")
    lines.append("- H5 (sustained open-endedness): see saturation chart; "
                 "predicted negative.")
    lines.append("")
    with open(os.path.join(resdir, "results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    # ---- charts ----
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 4, figsize=(16, 8))
    axes = axes.ravel()

    def bar(ax, key, title):
        means = [arr(c, key) for c in ORDER]
        means = [m[~np.isnan(m)] for m in means]
        mu = [m.mean() if len(m) else 0 for m in means]
        sd = [m.std() if len(m) else 0 for m in means]
        ax.bar(ORDER, mu, yerr=sd, capsize=4)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=20)

    bar(axes[0], "n_imagined", "H1: self-generated goals")
    bar(axes[1], "diversity_cells", "Goal diversity (cells)")
    bar(axes[2], "link_away", "H2: neighbours away from sources")
    bar(axes[3], "cache_ratio", "H2: cache ratio")
    bar(axes[4], "lifetime", "H4: mean lifetime")
    bar(axes[5], "social_goal_frac", "H3: social goal fraction")
    # scatter: communication rate vs goal generation
    ax = axes[6]
    for cond in ORDER:
        ax.scatter(arr(cond, "comm_rate"), arr(cond, "n_imagined"),
                   label=cond)
    ax.set_xlabel("tokens / 100 agent-steps")
    ax.set_ylabel("self-generated goals")
    ax.set_title("H1/H3: comm rate vs goal generation")
    ax.legend(fontsize=8)
    # H5: cumulative distinct goal cells over time (full)
    ax = axes[7]
    ck = results["full"][0]["checkpoints"]
    cum = np.array([r["cum_cells"] for r in results["full"]], dtype=float)
    ax.plot(ck, cum.mean(0), label="full mean")
    ax.fill_between(ck, cum.mean(0) - cum.std(0), cum.mean(0) + cum.std(0),
                    alpha=0.3)
    ax.set_xlabel("episode step")
    ax.set_ylabel("cumulative distinct goal cells")
    ax.set_title("H5: diversity over time (saturation?)")
    fig.tight_layout()
    fig.savefig(os.path.join(resdir, "charts.png"), dpi=110)
    print("wrote results.md and charts.png")


if __name__ == "__main__":
    main()
