"""Decision-partition experiments (all seeded, deterministic).

Experiment A -- insurance reproduction: the concept's worked example must
    reproduce scores (3, 10, 8, 10, 4), levels, and the 4-agent partition.
Experiment B -- synthetic scaling: random workflows of 10/25/50 decisions;
    partitioned agent count vs naive 1:1, load balance, coordination overhead.
Experiment C -- sensitivity: how the partition changes as block counts and
    the composite weight vary (assignment churn vs the base partition).
Experiment D -- dynamic re-partition: inject evidence updates into the
    insurance workflow; measure threshold-crossing triggers and stability.
Experiment E -- latency-aware scoring: sweep the latency weight; measure
    agent count and assignment churn as compute cost starts to dominate.

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

from agentic_systems.decision_partition import (
    COMPOSITE,
    SIMPLE,
    Decision,
    DynamicPartitioner,
    Scorer,
    assignment_churn,
    insurance_claim_decisions,
    insurance_demo,
    insurance_namer,
    partition_decisions,
    partition_metrics,
)
from agentic_systems.decision_partition.scoring import CATEGORY_WEIGHTS

DOMAIN_POOL = ("identity", "fraud", "policy", "damage", "settlement",
               "intake", "risk", "compliance")


def make_synthetic(n: int, seed: int) -> list[Decision]:
    rng = np.random.default_rng(seed)
    out = []
    for i in range(n):
        n_blocks = int(rng.integers(2, 8))  # 2..7
        cat = COMPOSITE if rng.random() < 0.5 else SIMPLE
        domains = tuple(rng.choice(DOMAIN_POOL, size=2, replace=False))
        latency = float(np.exp(rng.uniform(np.log(50), np.log(5000))))
        compute = float(rng.uniform(1, 20))
        out.append(Decision(
            name=f"Decision-{i:02d}", category=cat,
            blocks=[f"state-{j}" for j in range(n_blocks)],
            domains=domains, latency_ms=latency, compute_cost=compute))
    return out


def experiment_a():
    scorer = Scorer()
    decisions, partition = insurance_demo(scorer)
    expected = {"Identity validation": (3.0, "low"),
                "Damage assessment": (10.0, "high"),
                "Policy rules compliance": (8.0, "medium"),
                "Fraud detection": (10.0, "high"),
                "Final settlement": (4.0, "low")}
    rows = []
    for d in decisions:
        score, level = scorer.score(d), scorer.level(d)
        exp_score, exp_level = expected[d.name]
        assert abs(score - exp_score) < 1e-9 and level == exp_level
        agent = partition.agent_of(d.name)
        rows.append((d.name, len(d.blocks), CATEGORY_WEIGHTS[d.category],
                     score, level, agent.name if agent else "?"))
    assert len(partition.agents) == 4
    print("A: insurance reproduction OK -- 4 agents, scores (3,10,8,10,4)")
    return rows, partition_metrics(partition, decisions)


def experiment_b():
    out = {}
    for n in (10, 25, 50):
        acc = {"agents": [], "reduction": [], "load_std": [],
               "overhead": [], "naive_overhead": []}
        for seed in range(5):
            decisions = make_synthetic(n, seed)
            p = partition_decisions(decisions)
            m = partition_metrics(p, decisions)
            acc["agents"].append(m["agent_count"])
            acc["reduction"].append(m["agent_reduction"])
            acc["load_std"].append(m["load_std"])
            acc["overhead"].append(m["overhead_estimate"])
            acc["naive_overhead"].append(m["naive_overhead_estimate"])
        out[n] = {k: float(np.mean(v)) for k, v in acc.items()}
        print(f"B: n={n:2d} agents={out[n]['agents']:.1f} "
              f"reduction={out[n]['reduction']:.1%} "
              f"load_std={out[n]['load_std']:.2f} "
              f"overhead={out[n]['overhead']:.1f} vs naive "
              f"{out[n]['naive_overhead']:.1f}")
    return out


def experiment_c():
    base = make_synthetic(12, seed=7)
    scorer = Scorer()
    base_p = partition_decisions(base, scorer=scorer)

    # (i) sweep block count of one decision at a time
    block_churn: dict[int, float] = {}
    for b in range(2, 9):
        churns = []
        for i, d in enumerate(base):
            mod = [Decision(x.name, x.category, list(x.blocks),
                            x.domains, x.compute_cost, x.latency_ms)
                   for x in base]
            mod[i] = Decision(d.name, d.category,
                              [f"state-{j}" for j in range(b)],
                              d.domains, d.compute_cost, d.latency_ms)
            churns.append(assignment_churn(
                base_p, partition_decisions(mod, scorer=scorer)))
        block_churn[b] = float(np.mean(churns))

    # (ii) sweep the composite category weight
    weight_churn: dict[float, float] = {}
    for w in (1.0, 1.5, 2.0, 2.5, 3.0):
        s = Scorer(weights={SIMPLE: 1.0, COMPOSITE: w})
        weight_churn[w] = assignment_churn(
            base_p, partition_decisions(base, scorer=s))

    print("C: block-sweep churn:", {k: round(v, 3) for k, v in block_churn.items()})
    print("C: weight-sweep churn:", {k: round(v, 3) for k, v in weight_churn.items()})
    return block_churn, weight_churn


def experiment_d():
    dyn = DynamicPartitioner(insurance_claim_decisions(), namer=insurance_namer)
    steps = [
        ("Identity validation",
         {"added_blocks": ("Biometric check", "Device binding")}, None),
        ("Final settlement",
         {"added_blocks": ("Escalation path",)}, None),
        ("Policy rules compliance",
         {"added_blocks": ("Rider clause A", "Rider clause B",
                            "Jurisdiction override")}, None),
        ("Identity validation",
         {"removed_blocks": ("Biometric check", "Device binding")}, None),
        ("Fraud detection",
         {"removed_blocks": ("Model abnormality",)}, None),
    ]
    trace = []
    for name, kw, _ in steps:
        ev = dyn.observe(name, **kw)
        rec = dyn.maybe_repartition()
        trace.append({
            "step": ev.step,
            "event": f"{name}: {ev.change}",
            "scores": dict(dyn.scores()),
            "levels": dict(dyn.levels()),
            "crossed": ev.crossed_threshold,
            "trigger": rec.triggers if rec else [],
            "agents": len(rec.partition.agents) if rec
                      else len(dyn.history[-1].partition.agents),
            "stability": rec.stability_vs_prev if rec
                         else dyn.history[-1].stability_vs_prev,
        })
        print(f"D: step {ev.step} {name} {ev.old_score:.1f}->{ev.new_score:.1f} "
              f"({ev.old_level}->{ev.new_level}) crossed={ev.crossed_threshold} "
              f"trig={trace[-1]['trigger']} agents={trace[-1]['agents']} "
              f"stability={trace[-1]['stability']:.2f}")
    return trace


def experiment_e():
    decisions = make_synthetic(12, seed=11)
    base_p = partition_decisions(decisions, scorer=Scorer())
    out = []
    for w in (0.0, 0.5, 1.0, 2.0, 4.0):
        scorer = Scorer(latency_weight=w, latency_ref_ms=1000.0)
        p = partition_decisions(decisions, scorer=scorer)
        out.append({"w": w, "agents": len(p.agents),
                    "churn": assignment_churn(base_p, p)})
        print(f"E: latency_weight={w:3.1f} agents={out[-1]['agents']} "
              f"churn={out[-1]['churn']:.2f}")
    return out


def write_results(outdir, a_rows, a_metrics, b, c_block, c_weight, d_trace, e):
    with open(os.path.join(outdir, "results.md"), "w") as f:
        f.write("# Decision-partition experiment results\n\n")
        f.write("All runs seeded and deterministic.\n\n")

        f.write("## A -- insurance reproduction (concept's worked example)\n\n")
        f.write("| Decision | Blocks | Weight | Score | Level | Agent |\n"
                "|---|---|---|---|---|---|\n")
        for name, nb, w, s, lv, agent in a_rows:
            f.write(f"| {name} | {nb} | {w:.1f} | {s:.1f} | {lv} | {agent} |\n")
        f.write(f"\nAgents: {a_metrics['agent_count']} "
                f"(naive 1:1 would use {a_metrics['naive_agent_count']}); "
                f"coordination channels {a_metrics['coord_channels']:.0f} vs "
                f"{a_metrics['naive_coord_channels']:.0f} naive.\n\n")

        f.write("## B -- synthetic scaling (mean of 5 seeds)\n\n")
        f.write("| Decisions | Naive agents | Partitioned agents | "
                "Reduction | Load std | Overhead (partitioned / naive) |\n"
                "|---|---|---|---|---|---|\n")
        for n, m in b.items():
            f.write(f"| {n} | {n} | {m['agents']:.1f} | {m['reduction']:.1%} | "
                    f"{m['load_std']:.2f} | {m['overhead']:.1f} / "
                    f"{m['naive_overhead']:.1f} |\n")
        f.write("\n")

        f.write("## C -- sensitivity (assignment churn vs base partition)\n\n")
        f.write("Block-count sweep (mean churn over 12 decisions):\n\n")
        f.write("| Blocks | Churn |\n|---|---|\n")
        for bcount, ch in c_block.items():
            f.write(f"| {bcount} | {ch:.3f} |\n")
        f.write("\nComposite-weight sweep:\n\n")
        f.write("| Composite weight | Churn |\n|---|---|\n")
        for w, ch in c_weight.items():
            f.write(f"| {w:.1f} | {ch:.3f} |\n")
        f.write("\n")

        f.write("## D -- dynamic re-partition\n\n")
        f.write("| Step | Evidence | Scores (id/dmg/pol/frd/set) | "
                "Crossed | Triggers | Agents | Stability |\n"
                "|---|---|---|---|---|---|---|\n")
        order = ["Identity validation", "Damage assessment",
                 "Policy rules compliance", "Fraud detection",
                 "Final settlement"]
        for t in d_trace:
            scores = "/".join(f"{t['scores'][n]:.0f}" for n in order)
            f.write(f"| {t['step']} | {t['event']} | {scores} | "
                    f"{t['crossed']} | {'; '.join(t['trigger']) or '-'} | "
                    f"{t['agents']} | {t['stability']:.2f} |\n")
        f.write("\n")

        f.write("## E -- latency-aware scoring\n\n")
        f.write("| Latency weight | Agents | Churn vs base |\n|---|---|---|\n")
        for row in e:
            f.write(f"| {row['w']:.1f} | {row['agents']} | {row['churn']:.2f} |\n")


def write_charts(outdir, a_rows, b, c_block, c_weight, d_trace, e):
    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    fig.suptitle("Decision Partition -- complexity scoring and agent allocation "
                 "(seeded runs)")

    # 1: insurance scores
    ax = axes[0, 0]
    names = [r[0].replace(" ", "\n") for r in a_rows]
    scores = [r[3] for r in a_rows]
    colors = {"low": "#8EA9C9", "medium": "#F58518", "high": "#E45756"}
    ax.bar(names, scores, color=[colors[r[4]] for r in a_rows])
    ax.axhline(5, color="gray", linestyle="--", linewidth=1)
    ax.axhline(10, color="gray", linestyle="--", linewidth=1)
    ax.text(4.4, 5.3, "medium >= 5", fontsize=8)
    ax.text(4.4, 10.3, "high >= 10", fontsize=8)
    ax.set_title("A: insurance complexity scores")
    ax.set_ylabel("score = blocks x weight")

    # 2: synthetic scaling
    ax = axes[0, 1]
    ns = sorted(b)
    x = np.arange(len(ns))
    w = 0.35
    ax.bar(x - w / 2, ns, w, label="naive 1:1", color="#BAB0AC")
    ax.bar(x + w / 2, [b[n]["agents"] for n in ns], w,
           label="partitioned", color="#4C78A8")
    ax.set_xticks(x)
    ax.set_xticklabels([str(n) for n in ns])
    ax.set_title("B: agent count vs workflow size")
    ax.set_xlabel("decisions")
    ax.legend(fontsize=8)

    # 3: block sweep sensitivity
    ax = axes[0, 2]
    ax.plot(list(c_block), list(c_block.values()), marker="o", color="#4C78A8")
    ax.set_title("C: churn vs block count")
    ax.set_xlabel("blocks per decision")
    ax.set_ylabel("mean assignment churn")

    # 4: weight sweep sensitivity
    ax = axes[1, 0]
    ax.plot(list(c_weight), list(c_weight.values()), marker="o", color="#F58518")
    ax.set_title("C: churn vs composite weight")
    ax.set_xlabel("composite weight")
    ax.set_ylabel("assignment churn")

    # 5: dynamic trajectories
    ax = axes[1, 1]
    order = ["Identity validation", "Damage assessment",
             "Policy rules compliance", "Fraud detection", "Final settlement"]
    steps = [0] + [t["step"] for t in d_trace]
    base_scores = {"Identity validation": 3.0, "Damage assessment": 10.0,
                   "Policy rules compliance": 8.0, "Fraud detection": 10.0,
                   "Final settlement": 4.0}
    for name in order:
        traj = [base_scores[name]] + [t["scores"][name] for t in d_trace]
        ax.plot(steps, traj, marker="o", label=name, linewidth=1.5)
    ax.axhspan(5, 10, color="gray", alpha=0.12)
    ax.axhline(5, color="gray", linestyle="--", linewidth=1)
    ax.axhline(10, color="gray", linestyle="--", linewidth=1)
    ax.set_title("D: scores under evidence updates")
    ax.set_xlabel("evidence step")
    ax.set_ylabel("complexity score")
    ax.legend(fontsize=7)

    # 6: latency sweep
    ax = axes[1, 2]
    ws = [r["w"] for r in e]
    ax.plot(ws, [r["agents"] for r in e], marker="o", label="agents",
            color="#4C78A8")
    ax.set_xlabel("latency weight")
    ax.set_ylabel("agent count", color="#4C78A8")
    ax2 = ax.twinx()
    ax2.plot(ws, [r["churn"] for r in e], marker="s", label="churn",
             color="#E45756")
    ax2.set_ylabel("churn vs base", color="#E45756")
    ax.set_title("E: latency-aware partition shift")

    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "charts.png"), dpi=110)
    print("wrote charts.png")


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "..", "results")
    os.makedirs(outdir, exist_ok=True)

    a_rows, a_metrics = experiment_a()
    b = experiment_b()
    c_block, c_weight = experiment_c()
    d_trace = experiment_d()
    e = experiment_e()

    write_results(outdir, a_rows, a_metrics, b, c_block, c_weight, d_trace, e)
    write_charts(outdir, a_rows, b, c_block, c_weight, d_trace, e)
    print("wrote results.md and charts.png")


if __name__ == "__main__":
    main()
