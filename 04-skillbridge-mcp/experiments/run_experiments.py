"""SkillBridge MCP experiments.

Exp 1 — Portability: 6 skills x 3 adapters x {skillbridge, raw} modes.
        Same skills, same inputs; only the adapter (and mode) changes.
        Metrics: per-adapter pass rate, cross-adapter std, portability
        score (worst-adapter pass rate).

Exp 2 — Reuse economics: analytical build-cost model.
        baseline(M) = S*M*E            (every skill rebuilt per provider)
        bridge(M)   = S*E + M*A + F   (skills once + one adapter per model)
        S=20 skills, E=5d per skill/provider, A=8d per adapter, F=15d.

Exp 3 — Governance: policy engine under adversarial runs.
        Unlisted tool, high-sensitivity tool without approval, and
        deprecated-version runs must be denied; clean runs allowed.

Outputs: results/results.md and results/charts.png.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.adapters import default_adapters
from src.capabilities import CapabilityServer
from src.catalog import build_catalog
from src.eval import EvalHarness
from src.policy import PolicyEngine
from src.runtime import SkillRuntime
from src.skill import SkillManifest, SkillPackage, Step

SKILLS = ["invoice-extractor", "pii-redactor", "sql-generator",
          "code-reviewer", "meeting-summarizer", "rag-answerer"]


def exp_portability():
    registry, broker = build_catalog()
    runtime = SkillRuntime(registry, broker, PolicyEngine())
    adapters = default_adapters(seed=3)
    harness = EvalHarness(runtime)
    results = harness.evaluate(SKILLS, adapters, seed=11)
    per_skill, agg = {}, {"skillbridge": [], "raw": []}
    for s in SKILLS:
        per_skill[s] = {}
        for mode in ("skillbridge", "raw"):
            p = harness.portability(results, s, mode, adapters)
            per_skill[s][mode] = p
            agg[mode].append(p["std"])
    return per_skill, agg, adapters


def exp_economics():
    S, E, A, F = 20, 5, 8, 15
    rows = []
    for m in range(1, 9):
        base = S * m * E
        bridge = S * E + m * A + F
        rows.append((m, base, bridge, base - bridge))
    return rows


def exp_governance():
    registry, broker = build_catalog()
    runtime = SkillRuntime(registry, broker, PolicyEngine())
    adapters = default_adapters(seed=5)
    ad = adapters[0]
    denied, reasons = 0, []

    # 1. unlisted tool: skill workflow uses text.scan_pii, not approved
    rogue = SkillPackage(
        SkillManifest("rogue-skill", "1.0.0", "uses unlisted tool", (),
                      ("text.scan_pii",), "internal",
                      approved_tools=("text.extract",)),
        "do it", [Step("tool", "text.scan_pii", capability="text.scan_pii")], [])
    registry.register(rogue)
    r = runtime.run("rogue-skill", ad, {"document": "hi bob@x.com"})
    denied += (not r.allowed)
    reasons.append(("unlisted tool", r.allowed, r.reason))

    # 2. high-sensitivity tool without approval
    exporter = SkillPackage(
        SkillManifest("exporter", "1.0.0", "exports data", (),
                      ("data.export",), "confidential"),
        "export", [Step("tool", "data.export", capability="data.export",
                        args={"query": "all"})], [])
    registry.register(exporter)
    r = runtime.run("exporter", ad, {})
    denied += (not r.allowed)
    reasons.append(("high-sensitivity w/o approval", r.allowed, r.reason))
    # with approval token it passes the gate
    r2 = runtime.run("exporter", ad, {}, approval_token="mgr-approval-1")
    reasons.append(("high-sensitivity WITH approval", r2.allowed, r2.reason))

    # 3. deprecated version
    r = runtime.run("sql-generator", ad,
                    {"agg": "SUM", "metric": "x", "table": "t"},
                    version_spec="0.5.0")
    denied += (not r.allowed)
    reasons.append(("deprecated version", r.allowed, r.reason))

    # 4. clean runs all allowed
    ok = 0
    for i in range(20):
        r = runtime.run("invoice-extractor", ad,
                        {"document": "Vendor: V\nAmount: $1\nDate: 2026-01-01"})
        ok += r.allowed
    return denied, 3, ok, 20, reasons


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    outdir = os.path.join(here, "..", "results")
    os.makedirs(outdir, exist_ok=True)

    per_skill, agg, adapters = exp_portability()
    econ = exp_economics()
    denied, n_bad, ok, n_good, reasons = exp_governance()

    with open(os.path.join(outdir, "results.md"), "w") as f:
        f.write("# SkillBridge MCP experiment results\n\n")
        f.write("## Exp 1 — Portability (6 skills x 3 adapters)\n\n")
        f.write("| Skill | Mode | " +
                " | ".join(a.name for a in adapters) +
                " | Mean | Worst | Std |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for s in SKILLS:
            for mode in ("skillbridge", "raw"):
                p = per_skill[s][mode]
                cells = " | ".join(f"{p['per_adapter'][a.name]:.0%}"
                                   for a in adapters)
                f.write(f"| {s} | {mode} | {cells} | {p['mean']:.0%} | "
                        f"{p['min']:.0%} | {p['std']:.3f} |\n")
        import statistics
        for mode in ("skillbridge", "raw"):
            stds = agg[mode]
            f.write(f"\nMean cross-adapter std ({mode}): "
                    f"{statistics.fmean(stds):.3f}\n")
        f.write("\n## Exp 2 — Reuse economics (dev-days)\n\n")
        f.write("| Models | Per-provider rebuild | SkillBridge | Saved |\n"
                "|---|---|---|---|\n")
        for m, base, bridge, saved in econ:
            f.write(f"| {m} | {base} | {bridge} | {saved} |\n")
        f.write("\n## Exp 3 — Governance\n\n")
        f.write(f"Adversarial runs denied: {denied}/{n_bad}; "
                f"clean runs allowed: {ok}/{n_good}.\n\n")
        for name, allowed, reason in reasons:
            f.write(f"- {name}: {'ALLOWED' if allowed else 'DENIED'} — {reason}\n")

    # charts
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.2))
    fig.suptitle("SkillBridge MCP — experiments (seeded simulation)")
    ax = axes[0]
    xs = range(len(SKILLS))
    w = 0.35
    ax.bar([x - w / 2 for x in xs],
           [per_skill[s]["skillbridge"]["std"] for s in SKILLS],
           w, label="skillbridge", color="#4C78A8")
    ax.bar([x + w / 2 for x in xs],
           [per_skill[s]["raw"]["std"] for s in SKILLS],
           w, label="raw baseline", color="#E45756")
    ax.set_xticks(list(xs))
    ax.set_xticklabels([s.split("-")[0] for s in SKILLS], rotation=20, fontsize=8)
    ax.set_title("Cross-adapter std dev of pass rate")
    ax.legend(fontsize=8)
    ax = axes[1]
    ax.plot([m for m, _, _, _ in econ], [b for _, b, _, _ in econ],
            marker="o", label="per-provider rebuild", color="#E45756")
    ax.plot([m for m, _, _, _ in econ], [br for _, _, br, _ in econ],
            marker="o", label="SkillBridge", color="#4C78A8")
    ax.set_title("Build cost vs number of models (dev-days)")
    ax.set_xlabel("models")
    ax.legend(fontsize=8)
    ax = axes[2]
    ax.bar(["adversarial\nruns denied", "clean\nruns allowed"],
           [denied / n_bad, ok / n_good], color=["#E45756", "#54A24B"])
    ax.set_ylim(0, 1.05)
    ax.set_title("Governance decisions")
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, "charts.png"), dpi=110)

    print("portability std: skillbridge",
          f"{sum(agg['skillbridge']) / len(agg['skillbridge']):.3f}",
          " raw", f"{sum(agg['raw']) / len(agg['raw']):.3f}")
    print(f"governance: denied {denied}/{n_bad}, clean allowed {ok}/{n_good}")
    print("wrote results.md and charts.png")


if __name__ == "__main__":
    main()
