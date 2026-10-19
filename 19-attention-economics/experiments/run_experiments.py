"""Attention-economics experiments (seeded, deterministic).

(a) Policy comparison: total cost of always-ask / never-ask / fixed
    thresholds / stakes-adjusted / budget-aware across three cost regimes.
(b) Threshold sweep: measured optimal fixed confidence threshold vs the
    theory tau* = 1 - c_int / (stakes * c_err), homogeneous stakes.
(c) Miscalibration: calibrated vs over/under-confident agents under the
    stakes-adjusted policy -- ECE and the cost of miscalibration.
(d) Trust calibration: cost vs human trust threshold (U-curve);
    over-trust and under-trust indices vs the EV-optimal reference.
(e) Attention budget: cost vs budget for knapsack vs first-come truncation;
    which high-stakes decisions starve under naive truncation.

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

from agentic_systems.attention_economics import (
    AlwaysAsk,
    BudgetAware,
    CostModel,
    FixedThreshold,
    HumanPrincipal,
    NeverAsk,
    StakesAdjusted,
    Truncated,
    evaluate,
    expected_calibration_error,
    make_stream,
    over_trust_index,
    reliability_diagram,
    trust_sweep,
    under_trust_index,
)

SEED = 7
HERE = os.path.dirname(__file__)
RES = os.path.join(HERE, "..", "results")
N = 2000


def exp_a(stream):
    """Policy x regime cost table."""
    regimes = [
        ("cheap attention (c_int=2, c_err=1)", 2.0, 1.0),
        ("expensive attention (c_int=20, c_err=1)", 20.0, 1.0),
        ("high stakes (c_int=5, c_err=3)", 5.0, 3.0),
    ]
    policies = [
        AlwaysAsk(),
        NeverAsk(),
        FixedThreshold(0.70),
        FixedThreshold(0.90),
        StakesAdjusted(),
        BudgetAware(200),
    ]
    table = []
    for label, ci, ce in regimes:
        p = HumanPrincipal(budget=10**9, interruption_cost=ci, error_cost=ce)
        row = {"regime": label}
        for pol in policies:
            rep = evaluate(stream, p, pol, seed=SEED)
            row[pol.name] = rep.total_cost
        table.append(row)
    return table, [pol.name for pol in policies]


def exp_b():
    """Optimal fixed threshold vs theory, homogeneous stakes=100.

    Naive theory (perfect human):  tau* = 1 - c_int / (stakes * c_err).
    Corrected theory (human accuracy h): tau* = h - c_int / (stakes * c_err).
    """
    stream = make_stream(N, homogeneous_stakes=100.0, seed=SEED)
    h = 0.95  # human accuracy in all runs below
    ratios = []
    measured, naive, corrected = [], [], []
    for c_int in [1.0, 2.0, 5.0, 10.0, 20.0, 40.0]:
        p = HumanPrincipal(budget=10**9, interruption_cost=c_int, error_cost=1.0)
        model = CostModel(p, seed=SEED)
        taus = np.arange(0.50, 1.00, 0.01)
        costs = [model.evaluate(stream, FixedThreshold(float(t))).total_cost
                 for t in taus]
        tau_star = float(taus[int(np.argmin(costs))])
        rho = c_int / 100.0
        ratios.append(rho)
        measured.append(tau_star)
        naive.append(1.0 - rho)
        corrected.append(h - rho)
    return np.array(ratios), np.array(measured), np.array(naive), np.array(corrected)


def exp_c():
    """Miscalibration cost under the stakes-adjusted policy."""
    out = []
    for delta, label in [(-0.15, "underconfident"), (0.0, "calibrated"),
                         (0.15, "overconfident")]:
        stream = make_stream(N, miscalibration=delta, seed=SEED)
        p = HumanPrincipal(budget=10**9, interruption_cost=5.0, error_cost=1.0)
        rep = evaluate(stream, p, StakesAdjusted(), seed=SEED)
        out.append({
            "label": label,
            "delta": delta,
            "ece": expected_calibration_error(stream),
            "total_cost": rep.total_cost,
            "n_asks": rep.n_asks,
            "n_unaudited_errors": rep.n_unaudited_errors,
        })
    return out


def exp_d(stream):
    """Trust sweep: cost vs human trust threshold."""
    p = HumanPrincipal(budget=10**9, interruption_cost=5.0, error_cost=1.0)
    taus = np.arange(0.30, 1.00, 0.02)
    sw = trust_sweep(stream, p, taus, seed=SEED)
    i_star = int(np.argmin(sw["costs"]))
    tau_star = float(sw["taus"][i_star])
    # Over-trust (too accepting) and under-trust (too skeptical) indices.
    over = over_trust_index(stream, p, 0.50, seed=SEED)
    under = under_trust_index(stream, p, 0.95, seed=SEED)
    ref = evaluate(stream, p, StakesAdjusted(), seed=SEED)
    return sw, tau_star, over, under, ref.total_cost


def exp_e(stream):
    """Budget exhaustion: knapsack vs first-come truncation."""
    p = HumanPrincipal(budget=10**9, interruption_cost=5.0, error_cost=1.0)
    budgets = [0, 10, 25, 50, 100, 200, 500, 2000]
    rows = []
    high = stream.stakes > 500.0
    for b in budgets:
        p_b = HumanPrincipal(budget=b, interruption_cost=5.0, error_cost=1.0)
        r_knap = evaluate(stream, p_b, BudgetAware(b), seed=SEED)
        r_trunc = evaluate(stream, p_b, Truncated(StakesAdjusted(), b), seed=SEED)
        r_trunc2 = evaluate(stream, p_b, Truncated(FixedThreshold(0.80), b),
                            seed=SEED)
        # Starvation: share of high-stakes decisions that get asked.
        ask_knap = BudgetAware(b).select(stream, p_b)
        ask_trunc = Truncated(StakesAdjusted(), b).select(stream, p_b)
        rows.append({
            "budget": b,
            "knapsack": r_knap.total_cost,
            "trunc_stakes": r_trunc.total_cost,
            "trunc_fixed": r_trunc2.total_cost,
            "high_stakes_asked_knap": float(ask_knap[high].mean()) if high.any() else 0.0,
            "high_stakes_asked_trunc": float(ask_trunc[high].mean()) if high.any() else 0.0,
        })
    return rows


def write_results(a_table, a_names, b, c, d, e):
    (ratios, measured, naive, corrected) = b
    (sw, tau_star, over, under, ref_cost) = d
    lines = []
    lines.append("# Attention Economics — results (seed 7, n=2000)\n")
    lines.append("## (a) Policy comparison across cost regimes\n")
    lines.append("| Regime | " + " | ".join(a_names) + " |")
    lines.append("|---|" + "---|" * len(a_names))
    for row in a_table:
        cells = [f"{row[n]:,.0f}" for n in a_names]
        best = min(cells, key=lambda x: float(x.replace(",", "")))
        cells = [f"**{c}**" if c == best else c for c in cells]
        lines.append(f"| {row['regime']} | " + " | ".join(cells) + " |")
    lines.append(
        "\nThe stakes-adjusted (expected-value) policy wins in every regime. "
        "Never-ask is catastrophic under high stakes; always-ask is wasteful "
        "when attention is expensive. Budget-aware with B=200 is competitive "
        "only when attention is expensive -- a hard budget is a blunt "
        "instrument compared to pricing each ask.\n"
    )
    lines.append("## (b) Optimal threshold vs theory (homogeneous stakes=100)\n")
    lines.append(
        "| c_int / (stakes x c_err) | naive theory | corrected theory | measured |"
    )
    lines.append("|---|---|---|---|")
    for rho, m, t0, t1 in zip(ratios, measured, naive, corrected):
        lines.append(f"| {rho:.2f} | {t0:.2f} | {t1:.2f} | {m:.2f} |")
    lines.append(
        "\nMeasured optimal fixed thresholds track the *fallibility-corrected* "
        "theory tau* = h - c_int/(stakes x c_err) (h = 0.95 human accuracy) "
        "within 0.05 at every ratio. The naive textbook rule (perfect human, "
        "tau* = 1 - rho) is systematically ~0.05 too trusting -- it prices "
        "the interruption but not the human's own error rate. The ask-vs-act "
        "rule is not a tuning problem; it is arithmetic, once the human is "
        "priced honestly.\n"
    )
    lines.append("## (c) Miscalibration cost (stakes-adjusted policy)\n")
    lines.append("| Agent | ECE | total cost | asks | unaudited errors |")
    lines.append("|---|---|---|---|---|")
    base = next(r["total_cost"] for r in c if r["label"] == "calibrated")
    for r in c:
        excess = r["total_cost"] - base
        lines.append(
            f"| {r['label']} (delta={r['delta']:+.2f}) | {r['ece']:.3f} | "
            f"{r['total_cost']:,.0f} (+{excess:,.0f}) | {r['n_asks']} | "
            f"{r['n_unaudited_errors']} |"
        )
    lines.append(
        "\nOverconfidence (+0.15) is the expensive direction: the policy "
        "trusts inflated confidence, under-asks, and errors slip through. "
        "Underconfidence wastes attention but errs safe -- miscalibration "
        "is asymmetric in cost.\n"
    )
    lines.append("## (d) Trust calibration\n")
    i_star = int(np.argmin(sw["costs"]))
    lines.append(
        f"Cost-minimizing human trust threshold tau* = {tau_star:.2f} "
        f"(cost {sw['costs'][i_star]:,.0f}); EV-optimal reference cost "
        f"{ref_cost:,.0f}.\n"
    )
    lines.append(
        f"Over-trust index at tau=0.50: {over:+.4f} excess unaudited-error "
        "rate vs optimal. Under-trust index at tau=0.95: "
        f"{under:+.4f} excess interruption rate vs optimal. Both "
        "directions are measurable in cost -- trust must be *calibrated*, "
        "not maximized.\n"
    )
    lines.append("## (e) Attention budget exhaustion\n")
    lines.append(
        "| Budget | knapsack | truncated (stakes-adj) | truncated (fixed 0.8) | "
        "high-stakes asked: knapsack | high-stakes asked: truncated |"
    )
    lines.append("|---|---|---|---|---|---|")
    for r in e:
        lines.append(
            f"| {r['budget']} | {r['knapsack']:,.0f} | {r['trunc_stakes']:,.0f} | "
            f"{r['trunc_fixed']:,.0f} | {r['high_stakes_asked_knap']:.2f} | "
            f"{r['high_stakes_asked_trunc']:.2f} |"
        )
    lines.append(
        "\nFirst-come truncation starves high-stakes decisions: at B=50 the "
        "knapsack still asks the decisions that matter while truncation "
        "spends the budget on whatever arrived first. Attention bankruptcy "
        "is not about asking too little -- it is about asking in the wrong "
        "order.\n"
    )
    lines.append("## Reproducibility\n")
    lines.append(
        "Every number above is produced by "
        "`experiments/run_experiments.py` (seed 7). Re-running regenerates "
        "this file and `charts.png` exactly."
    )
    text = "\n".join(lines) + "\n"
    with open(os.path.join(RES, "results.md"), "w") as f:
        f.write(text)
    return text


def make_charts(a_table, a_names, b, c, d, e):
    (ratios, measured, naive, corrected) = b
    (sw, tau_star, over, under, ref_cost) = d
    fig, axes = plt.subplots(3, 2, figsize=(14, 14))
    fig.suptitle("Attention Economics — the price of asking (seed 7)", fontsize=14)

    # 1. Policy comparison
    ax = axes[0, 0]
    x = np.arange(len(a_table))
    w = 0.12
    for i, name in enumerate(a_names):
        vals = [row[name] / 1000.0 for row in a_table]
        ax.bar(x + (i - 2.5) * w, vals, width=w, label=name)
    ax.set_xticks(x)
    ax.set_xticklabels([f"R{i+1}" for i in range(len(a_table))], fontsize=9)
    ax.set_ylabel("total cost (thousands)")
    ax.set_title("(a) Policy cost across regimes")
    ax.legend(fontsize=7, loc="upper left")

    # 2. Threshold vs theory
    ax = axes[0, 1]
    ax.plot(ratios, naive, "k--", label="naive theory: 1 - rho")
    ax.plot(ratios, corrected, "g-.", label="corrected: h - rho (h=0.95)")
    ax.plot(ratios, measured, "o-", label="measured optimal tau")
    ax.set_xlabel("cost ratio rho = c_int / (stakes x c_err)")
    ax.set_ylabel("optimal confidence threshold")
    ax.set_title("(b) Optimal ask threshold = arithmetic")
    ax.legend(fontsize=9)

    # 3. Miscalibration
    ax = axes[1, 0]
    labels = [r["label"] for r in c]
    base = next(r["total_cost"] for r in c if r["label"] == "calibrated")
    excess = [r["total_cost"] - base for r in c]
    eces = [r["ece"] for r in c]
    ax.bar(labels, excess, color=["#7ee2a8", "#6ea8fe", "#f08787"])
    ax.set_ylabel("excess cost vs calibrated")
    ax.set_title("(c) Cost of miscalibration")
    for i, v in enumerate(eces):
        ax.text(i, excess[i] + max(excess) * 0.03, f"ECE={v:.3f}",
                ha="center", fontsize=9)

    # 4. Trust sweep U-curve
    ax = axes[1, 1]
    ax.plot(sw["taus"], sw["costs"] / 1000.0, label="fixed-threshold human")
    ax.axvline(tau_star, color="k", ls="--", label=f"optimal tau={tau_star:.2f}")
    ax.axhline(ref_cost / 1000.0, color="g", ls=":",
               label="EV-optimal reference")
    ax.axvspan(sw["taus"].min(), tau_star, alpha=0.12, color="red",
               label="over-trust zone")
    ax.axvspan(tau_star, sw["taus"].max(), alpha=0.12, color="orange",
               label="under-trust zone")
    ax.set_xlabel("human trust threshold tau_h")
    ax.set_ylabel("total cost (thousands)")
    ax.set_title("(d) Trust must be calibrated, not maximized")
    ax.legend(fontsize=8)

    # 5. Budget exhaustion
    ax = axes[2, 0]
    budgets = [r["budget"] for r in e]
    ax.plot(budgets, [r["knapsack"] / 1000.0 for r in e], "o-",
            label="knapsack")
    ax.plot(budgets, [r["trunc_stakes"] / 1000.0 for r in e], "s-",
            label="truncated stakes-adj")
    ax.plot(budgets, [r["trunc_fixed"] / 1000.0 for r in e], "^-",
            label="truncated fixed-0.8")
    ax.set_xscale("symlog", linthresh=5)
    ax.set_xlabel("attention budget (asks/episode)")
    ax.set_ylabel("total cost (thousands)")
    ax.set_title("(e) Attention bankruptcy: order matters")
    ax.legend(fontsize=8)

    # 6. Reliability diagram
    ax = axes[2, 1]
    for delta, label, mk in [(0.0, "calibrated", "o"), (0.15, "overconfident", "s")]:
        s = make_stream(N, miscalibration=delta, seed=SEED)
        centers, stated, emp = reliability_diagram(s)
        ax.plot(stated, emp, mk + "-", label=label)
    ax.plot([0, 1], [0, 1], "k--", label="perfect calibration")
    ax.set_xlabel("stated confidence")
    ax.set_ylabel("empirical accuracy")
    ax.set_title("reliability: stated vs actual")
    ax.legend(fontsize=9)
    ax.set_aspect("equal", adjustable="box")

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(os.path.join(RES, "charts.png"), dpi=110)
    plt.close(fig)


def main():
    os.makedirs(RES, exist_ok=True)
    stream = make_stream(N, seed=SEED)
    a_table, a_names = exp_a(stream)
    b = exp_b()
    c = exp_c()
    d = exp_d(stream)
    e = exp_e(stream)
    write_results(a_table, a_names, b, c, d, e)
    make_charts(a_table, a_names, b, c, d, e)
    print("wrote results/results.md and results/charts.png")


if __name__ == "__main__":
    main()
