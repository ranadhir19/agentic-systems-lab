"""HealFlow experiments.

Phase 1 — fault battery: 3 workflows x fault scenarios x 4 systems
  (healflow, healflow-no-memory, naive retry, llm-replan).
  Faults: transient outage, permanent outage (post-payment!), schema
  change, corrupted intermediate.
  Metrics: end-to-end success, graceful termination, side effects
  (uncompensated external actions), tool calls, diagnosis accuracy.

Phase 2 — repair-memory transfer: train HealFlow on the etl schema-change
  fault, then test on the analogous research-flow schema change with the
  memory kept vs a fresh no-memory runtime. Metrics: diagnosis steps,
  memory hits, success.

Outputs: results/results.md and results/charts.png.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.catalog import (SUBSTITUTES, PREDS, build_injector, etl_flow,
                         order_flow, research_flow)
from src.runtime import HealFlowRuntime, ReplanBaseline, RetryBaseline


def garbage_plan(out):
    return {"plan": ["???", None, 123]}


def make_scenario(name, workflow_fn, fault, expected_cause):
    return {"name": name, "workflow_fn": workflow_fn, "fault": fault,
            "expected": expected_cause}


SCENARIOS = [
    make_scenario("order: transient payment outage", order_flow,
                  ("charge_payment", "outage", {"n": 2}), "transient_outage"),
    make_scenario("order: inventory permanently down", order_flow,
                  ("reserve_inventory", "outage", {"n": 99}),
                  "persistent_outage"),
    make_scenario("etl: transient extract outage", etl_flow,
                  ("extract", "outage", {"n": 2}), "transient_outage"),
    make_scenario("etl: upstream schema change", etl_flow,
                  ("extract", "schema_change",
                   {"mapping": {"user_id": "uid"}}), "schema_change"),
    make_scenario("research: corrupted plan (permanent)", research_flow,
                  ("plan", "corrupt", {"n": 99, "fn": garbage_plan}),
                  "bad_intermediate"),
    make_scenario("research: search schema change", research_flow,
                  ("search", "schema_change",
                   {"mapping": {"title": "headline"}}), "schema_change"),
]


def fresh_systems():
    return [
        ("healflow", lambda: HealFlowRuntime(
            build_injector(), PREDS, SUBSTITUTES, use_memory=True)),
        ("healflow-no-mem", lambda: HealFlowRuntime(
            build_injector(), PREDS, SUBSTITUTES, use_memory=False)),
        ("retry", lambda: RetryBaseline(build_injector(), PREDS)),
        ("replan", lambda: ReplanBaseline(build_injector(), PREDS)),
    ]


def run_scenario(system, sc):
    injector = system.injector  # all runtimes hold their injector
    tool, kind, params = sc["fault"]
    injector.add_fault(tool, kind, **params)
    return system.run(sc["workflow_fn"](), expected_cause=sc["expected"])


def phase1():
    table = {}
    for sc in SCENARIOS:
        for sname, sfactory in fresh_systems():
            system = sfactory()
            rep = run_scenario(system, sc)
            table[(sc["name"], sname)] = rep
            print(f"{sc['name'][:34]:34s} {sname:15s} "
                  f"success={rep.success!s:5s} graceful={rep.graceful!s:5s} "
                  f"sidefx={rep.side_effects} calls={rep.tool_calls} "
                  f"diag={rep.correct_diagnosis} repairs={rep.repairs}")
    return table


def phase2():
    # train on etl schema change, test on research schema change
    train_sc = SCENARIOS[3]
    test_sc = SCENARIOS[5]
    mem_rt = HealFlowRuntime(build_injector(), PREDS, SUBSTITUTES,
                             use_memory=True)
    run_scenario(mem_rt, train_sc)  # train (memory learns)
    rep_mem = run_scenario(mem_rt, test_sc)
    nomem_rt = HealFlowRuntime(build_injector(), PREDS, SUBSTITUTES,
                               use_memory=False)
    rep_nomem = run_scenario(nomem_rt, test_sc)
    print(f"transfer with-memory:    diag_steps={rep_mem.diagnosis_steps} "
          f"hits={rep_mem.memory_hits} success={rep_mem.success} "
          f"calls={rep_mem.tool_calls}")
    print(f"transfer without-memory: diag_steps={rep_nomem.diagnosis_steps} "
          f"success={rep_nomem.success} calls={rep_nomem.tool_calls}")
    return rep_mem, rep_nomem


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "..", "results")
    os.makedirs(outdir, exist_ok=True)

    table = phase1()
    rep_mem, rep_nomem = phase2()
    systems = [s for s, _ in fresh_systems()]

    with open(os.path.join(outdir, "results.md"), "w") as f:
        f.write("# HealFlow experiment results\n\n")
        f.write("## Phase 1 — fault battery\n\n")
        f.write("| Scenario | System | Success | Graceful | Side effects | "
                "Tool calls | Diagnosis correct | Repairs |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for sc in SCENARIOS:
            for s in systems:
                r = table[(sc["name"], s)]
                f.write(f"| {sc['name']} | {s} | {r.success} | {r.graceful} | "
                        f"{r.side_effects} | {r.tool_calls} | "
                        f"{r.correct_diagnosis} | {','.join(r.repairs)} |\n")
        f.write("\n## Phase 2 — repair-memory transfer\n\n")
        f.write("| | With memory | Without memory |\n|---|---|---|\n")
        f.write(f"| Diagnosis steps | {rep_mem.diagnosis_steps} | "
                f"{rep_nomem.diagnosis_steps} |\n")
        f.write(f"| Memory hits | {rep_mem.memory_hits} | — |\n")
        f.write(f"| Success | {rep_mem.success} | {rep_nomem.success} |\n")
        f.write(f"| Tool calls | {rep_mem.tool_calls} | "
                f"{rep_nomem.tool_calls} |\n")

    # charts
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    fig.suptitle("HealFlow — fault battery (deterministic simulation)")
    ax = axes[0]
    xs = range(len(SCENARIOS))
    w = 0.2
    colors = {"healflow": "#4C78A8", "healflow-no-mem": "#8EA9C9",
              "retry": "#F58518", "replan": "#E45756"}
    for i, s in enumerate(systems):
        ax.bar([x + (i - 1.5) * w for x in xs],
               [int(table[(sc["name"], s)].success) for sc in SCENARIOS],
               w, label=s, color=colors[s])
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"S{i + 1}" for i in range(len(SCENARIOS))], fontsize=8)
    ax.set_title("Task success per scenario")
    ax.legend(fontsize=8)
    ax = axes[1]
    for i, s in enumerate(systems):
        ax.bar([x + (i - 1.5) * w for x in xs],
               [table[(sc["name"], s)].side_effects for sc in SCENARIOS],
               w, label=s, color=colors[s])
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"S{i + 1}" for i in range(len(SCENARIOS))], fontsize=8)
    ax.set_title("Uncompensated side effects")
    ax = axes[2]
    for i, s in enumerate(systems):
        ax.bar([x + (i - 1.5) * w for x in xs],
               [table[(sc["name"], s)].tool_calls for sc in SCENARIOS],
               w, label=s, color=colors[s])
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"S{i + 1}" for i in range(len(SCENARIOS))], fontsize=8)
    ax.set_title("Tool calls (cost proxy)")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "charts.png"), dpi=110)
    print("wrote results.md and charts.png")


if __name__ == "__main__":
    main()
