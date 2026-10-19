"""Behavioral regression experiments (all seeded; every number measured).

(a) Battery sensitivity: single-category regressions at several severities
    -> detection rate per category; benign shifts -> false-positive rate.
(b) Canary detection latency: tasks-to-flag for v3 (strong) and v5 (mixed).
(c) Severity scoring: rank the five versions; the silent tool-format break
    must outrank a verbosity change.
(d) Policy accuracy: pin / auto-adopt / rollback vs ground truth.
(e) Suite-size ablation: detection power vs battery size.

Outputs: results/results.md and results/charts.png.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from agentic_systems.behavioral_regression import (
    CATEGORIES,
    GROUND_TRUTH_POLICY,
    VERSIONS,
    BatteryResult,
    CanaryAnalyzer,
    DriftDetector,
    ModelVersion,
    PolicyEngine,
    SimulatedAgent,
    build_battery,
    run_battery,
)

SEEDS = [7, 11, 42, 0, 99]
N_TASKS = 120
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")


def _runs(version: ModelVersion, battery, seeds) -> list[BatteryResult]:
    agent = SimulatedAgent(version)
    return [run_battery(agent, battery, s) for s in seeds]


def exp_a_sensitivity():
    """Detection rate per injected severity; FPR on benign shifts."""
    det = DriftDetector()
    severities = [0.02, 0.05, 0.10, 0.20]
    det_rates: dict[str, list[float]] = {c: [] for c in CATEGORIES}
    for cat in CATEGORIES:
        for sev in severities:
            hits = 0
            for s in SEEDS:
                bat = build_battery(N_TASKS)
                base = _runs(VERSIONS["v1"], bat, [s])
                v = ModelVersion(name=f"inj-{cat}-{sev}",
                                 success_delta={cat: -sev})
                cand = _runs(v, bat, [s])
                # one seed -> McNemar still valid on 120 paired tasks
                rep = det.compare(base, cand, v.name)
                flagged = [d.metric for d in rep.correctness_regressions()]
                if f"pass_{cat}" in flagged:
                    hits += 1
            det_rates[cat].append(hits / len(SEEDS))

    benign = {
        "verbosity x1.5": ModelVersion(name="benign-verb", verbosity=1.5),
        "latency x1.8": ModelVersion(name="benign-lat", latency_mult=1.8),
        "cost x1.4": ModelVersion(name="benign-cost", cost_mult=1.4),
        "improve +0.02": ModelVersion(
            name="benign-imp",
            success_delta={c: 0.02 for c in CATEGORIES}),
    }
    fpr: dict[str, float] = {}
    for label, v in benign.items():
        fps = 0
        for s in SEEDS:
            bat = build_battery(N_TASKS)
            base = _runs(VERSIONS["v1"], bat, [s])
            cand = _runs(v, bat, [s])
            rep = det.compare(base, cand, v.name)
            if rep.correctness_regressions():
                fps += 1
        fpr[label] = fps / len(SEEDS)
    return severities, det_rates, fpr


def exp_b_canary():
    """Tasks-to-flag at canary stages for v3 and v5."""
    an = CanaryAnalyzer()
    out: dict[str, list] = {}
    for vn in ("v3", "v5"):
        rows = []
        for s in SEEDS:
            bat = build_battery(N_TASKS)
            rep = an.analyze(bat, VERSIONS["v1"], VERSIONS[vn], seed=s)
            rows.append((rep.stopped, rep.tasks_to_flag,
                         rep.stages[-1].decision if rep.stages else None))
        out[vn] = rows
    return out


def exp_c_severity():
    det = DriftDetector()
    bat = build_battery(N_TASKS)
    base = _runs(VERSIONS["v1"], bat, SEEDS)
    scores = {}
    for vn in ("v1", "v2", "v3", "v4", "v5"):
        cand = _runs(VERSIONS[vn], bat, SEEDS)
        rep = det.compare(base, cand, vn)
        scores[vn] = (rep.severity,
                      [(d.metric, round(d.diff, 3)) for d in rep.regressions])
    return scores


def exp_d_policy():
    det = DriftDetector()
    pol = PolicyEngine()
    an = CanaryAnalyzer()
    bat = build_battery(N_TASKS)
    base = _runs(VERSIONS["v1"], bat, SEEDS)
    rows = []
    for vn in ("v2", "v3", "v4", "v5"):
        cand = _runs(VERSIONS[vn], bat, SEEDS)
        rep = det.compare(base, cand, vn)
        can = an.analyze(bat, VERSIONS["v1"], VERSIONS[vn], seed=SEEDS[0])
        dec = pol.decide(rep, can)
        truth = GROUND_TRUTH_POLICY[vn]
        rows.append((vn, dec.decision, truth, dec.decision == truth,
                     "; ".join(dec.rationale)))
    acc = sum(r[3] for r in rows) / len(rows)
    return rows, acc


def exp_e_ablation():
    det = DriftDetector()
    sizes = [12, 30, 60, 120, 240]
    power = {"v3": [], "v5": []}
    for n in sizes:
        for vn in ("v3", "v5"):
            hits = 0
            for s in SEEDS:
                bat = build_battery(n)
                base = _runs(VERSIONS["v1"], bat, [s])
                cand = _runs(VERSIONS[vn], bat, [s])
                rep = det.compare(base, cand, vn)
                if rep.correctness_regressions():
                    hits += 1
            power[vn].append(hits / len(SEEDS))
    return sizes, power


def write_results(a, b, c, d_rows, d_acc, e_sizes, e_power):
    severities, det_rates, fpr = a
    os.makedirs(RESULTS, exist_ok=True)
    lines = ["# Behavioral Regression — experiment results",
             "",
             f"Seeds: {SEEDS}. Battery: {N_TASKS} tasks (30/category). Every number measured.",
             "",
             "## (a) Battery sensitivity: detection rate by injected severity",
             ""]
    for cat in CATEGORIES:
        lines.append(f"{cat}: " + ", ".join(
            f"{s:.2f}->{r:.2f}" for s, r in zip(severities, det_rates[cat])))
    lines += ["",
              "False-positive rate on benign shifts (fraction of seeds with "
              "any correctness regression flagged):"]
    for label, rate in fpr.items():
        lines.append(f"- {label}: {rate:.2f}")
    lines += ["",
              "## (b) Canary detection latency",
              ""]
    for vn, rows in b.items():
        flagged = [r[1] for r in rows if r[0]]
        stopped_frac = sum(r[0] for r in rows) / len(rows)
        lines.append(
            f"{vn}: stopped in {stopped_frac:.0%} of seeds; "
            f"tasks-to-flag (when stopped): {flagged}")
    lines += ["", "## (c) Severity scores (v1..v5)", ""]
    for vn in ("v1", "v2", "v3", "v4", "v5"):
        sev, regs = c[vn]
        lines.append(f"{vn}: severity={sev:.3f} regressions={regs}")
    order = sorted(c, key=lambda v: c[v][0], reverse=True)
    lines.append(f"Severity ranking: {' > '.join(order)}")
    lines += ["", "## (d) Policy decisions vs ground truth", ""]
    for vn, dec, truth, ok, why in d_rows:
        lines.append(f"{vn}: policy={dec} truth={truth} "
                     f"{'MATCH' if ok else 'MISS'} | {why}")
    lines.append(f"Policy accuracy: {d_acc:.2f}")
    lines += ["", "## (e) Suite-size ablation: detection power vs battery size",
              ""]
    for vn in ("v3", "v5"):
        lines.append(f"{vn}: " + ", ".join(
            f"n={n}: {p:.2f}" for n, p in zip(e_sizes, e_power[vn])))
    with open(os.path.join(RESULTS, "results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")
    print("wrote results/results.md")


def write_charts(a, b, c, e_sizes, e_power):
    severities, det_rates, fpr = a
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Behavioral Regression — experiment results", fontsize=14)

    ax = axes[0, 0]
    for cat in CATEGORIES:
        ax.plot(severities, det_rates[cat], marker="o", label=cat)
    ax.set_xlabel("injected per-category success delta")
    ax.set_ylabel("detection rate (fraction of seeds)")
    ax.set_title("(a) Sensitivity: detection rate vs severity")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fpr_txt = "\n".join(f"{k}: FPR {v:.2f}" for k, v in fpr.items())
    ax.text(0.98, 0.35, f"benign-shift FPR:\n{fpr_txt}", transform=ax.transAxes,
            ha="right", va="top", fontsize=8,
            bbox=dict(facecolor="white", alpha=0.8))

    ax = axes[0, 1]
    labels, means = [], []
    for vn, rows in b.items():
        flagged = [r[1] for r in rows if r[1] is not None]
        labels.append(f"{vn}\n({len(flagged)}/{len(rows)} stopped)")
        means.append(float(np.mean(flagged)) if flagged else 0)
    ax.bar(labels, means, color=["#c0392b", "#e67e22"])
    ax.set_ylabel("mean tasks-to-flag")
    ax.set_title("(b) Canary: tasks to flag a regression")

    ax = axes[1, 0]
    vns = ["v1", "v2", "v3", "v4", "v5"]
    sevs = [c[v][0] for v in vns]
    colors = ["#2ecc71" if s == 0 else "#e74c3c" for s in sevs]
    ax.bar(vns, sevs, color=colors)
    ax.set_ylabel("severity score")
    ax.set_title("(c) Severity ranking: silent break >> verbosity")

    ax = axes[1, 1]
    for vn in ("v3", "v5"):
        ax.plot(e_sizes, e_power[vn], marker="o", label=f"{vn} detection power")
    ax.set_xscale("log")
    ax.set_xlabel("battery size (tasks)")
    ax.set_ylabel("detection power (fraction of seeds)")
    ax.set_title("(e) Ablation: detection power vs suite size")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    ax.set_xticks(e_sizes)
    ax.set_xticklabels([str(n) for n in e_sizes])

    fig.tight_layout()
    out = os.path.join(RESULTS, "charts.png")
    fig.savefig(out, dpi=110)
    plt.close(fig)
    print("wrote results/charts.png")


def main():
    a = exp_a_sensitivity()
    b = exp_b_canary()
    c = exp_c_severity()
    d_rows, d_acc = exp_d_policy()
    e_sizes, e_power = exp_e_ablation()
    write_results(a, b, c, d_rows, d_acc, e_sizes, e_power)
    write_charts(a, b, c, e_sizes, e_power)


if __name__ == "__main__":
    main()
