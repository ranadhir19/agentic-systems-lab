"""CISO AI Risk Twin experiments.

All deterministic (seed 0; no stochastic components in the engine).

Exp A — worked example end-to-end: inconsistencies, findings by
  kind/severity, evidence-level histogram, readiness score.
Exp B — dynamic funnel on 3 synthetic architectures of increasing
  complexity: 125 questions -> relevant -> auto-answered ->
  evidence-required -> clarification.
Exp C — evidence-level sensitivity: the same architecture assessed with
  no vendor evidence vs L1, L2, L4 vendor packs; assessment confidence
  and evidence completeness deltas.
Exp D — fix-and-rerun: add a human-approval node + tool input schema,
  re-assess, diff resolved/introduced/still-open findings.
Exp E — drift detection: runtime-observed edges vs the approved twin;
  an unapproved PII exfiltration edge must raise a critical alert.

Outputs: results/results.md and results/charts.png.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from agentic_systems import ai_risk_twin as rt

RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")
SEED = 0


def exp_a():
    twin = rt.worked_example()
    rules = rt.build_rules()
    inc = rt.check_consistency(twin)
    findings = rt.open_findings(rt.run_rules(twin, rules))
    r = rt.score_readiness(twin, findings, inc)
    summ = rt.summarize_findings(findings)
    levels = {}
    for f in findings:
        for e in f.evidence:
            levels[e.level.name] = levels.get(e.level.name, 0) + 1
    return {
        "inconsistencies": [(i.subject, i.claim, i.observed) for i in inc],
        "summary": summ,
        "evidence_levels": levels,
        "readiness": {
            "architecture": r.architecture_completeness,
            "evidence": r.evidence_completeness,
            "control": r.control_coverage,
            "confidence": r.assessment_confidence,
            "score": r.score, "verdict": r.verdict,
            "blocking": r.blocking,
        },
        "critical_titles": sorted({f.title for f in findings
                                   if f.severity == "critical"}),
    }


def exp_b():
    bank = rt.build_question_bank()
    out = {}
    for name, fn in [("simple_chatbot", rt.simple_chatbot),
                     ("rag_assistant", rt.rag_assistant),
                     ("agentic_platform", rt.agentic_platform)]:
        twin = fn()
        fr = rt.run_funnel(twin, bank)
        out[name] = fr.counts
    return out


def exp_c():
    twin = rt.worked_example()
    rules = rt.build_rules()
    inc = rt.check_consistency(twin)
    rows = {}
    for label, level in [("none", None),
                         ("L1_assertion", rt.EvidenceLevel.L1_ASSERTION),
                         ("L2_vendor_doc", rt.EvidenceLevel.L2_VENDOR_DOC),
                         ("L4_enterprise", rt.EvidenceLevel.L4_ENTERPRISE)]:
        pack = rt.vendor_evidence_pack(level) if level else {}
        findings = rt.open_findings(rt.run_rules(twin, rules, pack))
        r = rt.score_readiness(twin, findings, inc)
        rows[label] = {
            "confidence": r.assessment_confidence,
            "evidence_completeness": r.evidence_completeness,
            "score": r.score,
        }
    return rows


def exp_d():
    rules = rt.build_rules()
    before = rt.open_findings(rt.run_rules(rt.worked_example(), rules))
    after = rt.open_findings(rt.run_rules(rt.worked_example_fixed(), rules))
    d = rt.diff_findings(before, after)
    return {
        "counts": d.counts,
        "severity_delta": d.severity_delta(),
        "resolved_rules": sorted({f.rule_id for f in d.resolved}),
        "introduced": [(f.rule_id, f.title, f.targets) for f in d.introduced],
    }


def exp_e():
    twin = rt.worked_example()
    obs = [{"src": e["src"], "dst": e["dst"], "method": e.get("method"),
            "rel": e.get("rel"), "data": e.get("data")}
           for e in twin.edges]
    # Runtime: the agent starts exfiltrating PII to an unapproved endpoint.
    obs.append({"src": "support_agent", "dst": "shadow_analytics",
                "rel": "sends", "data": "pii"})
    alerts = rt.detect_drift(twin, obs)
    return [{"edge": a.edge, "severity": a.severity, "detail": a.detail}
            for a in alerts]


def charts(a, b, c, d):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle("CISO AI Risk Twin — experiment results (seed 0, "
                 "deterministic)")

    # 1. Funnel shrink across architectures.
    ax = axes[0, 0]
    names = list(b.keys())
    stages = ["relevant", "auto_answered", "evidence_required",
              "clarification"]
    x = range(len(names))
    w = 0.2
    for i, st in enumerate(stages):
        ax.bar([p + (i - 1.5) * w for p in x],
               [b[n][st] for n in names], width=w, label=st)
    ax.set_xticks(list(x))
    ax.set_xticklabels(["simple", "rag", "agentic"])
    ax.set_ylabel("questions")
    ax.set_title("Dynamic funnel: 125-question bank per architecture")
    ax.legend(fontsize=8)

    # 2. Readiness dimensions, worked example.
    ax = axes[0, 1]
    rd = a["readiness"]
    dims = ["architecture", "evidence", "control", "confidence"]
    ax.bar(dims, [rd[k] for k in dims])
    ax.set_ylim(0, 1.05)
    ax.set_title(f"Readiness dimensions (verdict: {rd['verdict']}, "
                 f"score {rd['score']:.3f})")
    ax.set_ylabel("fraction")

    # 3. Evidence-level sensitivity.
    ax = axes[1, 0]
    labels = list(c.keys())
    ax.plot(labels, [c[k]["confidence"] for k in labels], marker="o",
            label="assessment confidence")
    ax.plot(labels, [c[k]["evidence_completeness"] for k in labels],
            marker="s", label="evidence completeness")
    ax.set_title("Evidence hierarchy: confidence vs vendor-pack level")
    ax.set_ylabel("fraction")
    ax.legend(fontsize=8)

    # 4. Fix-and-rerun severity mass.
    ax = axes[1, 1]
    cats = ["resolved", "introduced", "still_open"]
    vals = [d["counts"][k] for k in cats]
    ax.bar(cats, vals)
    ax.set_title(f"Fix-and-rerun diff (severity delta "
                 f"{d['severity_delta']:+d})")
    ax.set_ylabel("findings")

    fig.tight_layout()
    out = os.path.join(RESULTS, "charts.png")
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return out


def write_md(a, b, c, d, e):
    lines = ["# CISO AI Risk Twin — results",
             "",
             "All numbers from deterministic runs (seed 0).",
             "",
             "## Exp A — worked example end-to-end",
             "",
             f"Inconsistencies (doc claim vs architecture): "
             f"{len(a['inconsistencies'])}"]
    for s, cl, ob in a["inconsistencies"]:
        lines.append(f"- {s}: claimed {cl!r}; observed {ob}")
    s = a["summary"]
    lines += ["",
              f"Findings: {s['total']} ({s['design']} design, "
              f"{s['information']} information; {s['critical']} critical, "
              f"{s['high']} high, {s['medium']} medium, {s['low']} low)",
              "",
              "Critical finding titles:"]
    lines += [f"- {t}" for t in a["critical_titles"]]
    lines += ["",
              "Evidence-level histogram (finding evidence items):"]
    for lvl, n in sorted(a["evidence_levels"].items()):
        lines.append(f"- {lvl}: {n}")
    r = a["readiness"]
    lines += ["",
              f"Readiness: architecture {r['architecture']}, evidence "
              f"{r['evidence']}, control {r['control']}, confidence "
              f"{r['confidence']} -> score {r['score']}, "
              f"**{r['verdict']}**",
              "Blocking reasons:"]
    lines += [f"- {x}" for x in r["blocking"]]
    lines += ["", "## Exp B — dynamic funnel (125-question bank)", ""]
    lines.append("| architecture | relevant | auto-answered | "
                 "evidence-required | clarification |")
    lines.append("|---|---|---|---|---|")
    for n, co in b.items():
        lines.append(f"| {n} | {co['relevant']} | {co['auto_answered']} | "
                     f"{co['evidence_required']} | {co['clarification']} |")
    lines += ["", "## Exp C — evidence-level sensitivity", ""]
    lines.append("| vendor pack | confidence | evidence completeness | "
                 "readiness score |")
    lines.append("|---|---|---|---|")
    for k, v in c.items():
        lines.append(f"| {k} | {v['confidence']} | "
                     f"{v['evidence_completeness']} | {v['score']} |")
    lines += ["", "## Exp D — fix-and-rerun", "",
              f"Resolved {d['counts']['resolved']}, introduced "
              f"{d['counts']['introduced']}, still open "
              f"{d['counts']['still_open']}; severity delta "
              f"{d['severity_delta']:+d}.",
              f"Resolved rules: {', '.join(d['resolved_rules'])}",
              "Introduced:"]
    lines += [f"- {rid} {title} {tgt}" for rid, title, tgt in d["introduced"]]
    lines += ["", "## Exp E — drift detection", ""]
    for al in e:
        lines.append(f"- **{al['severity']}** {al['edge'][0]} -> "
                     f"{al['edge'][1]}: {al['detail']}")
    with open(os.path.join(RESULTS, "results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


def main():
    os.makedirs(RESULTS, exist_ok=True)
    a, b, c, d, e = exp_a(), exp_b(), exp_c(), exp_d(), exp_e()
    charts(a, b, c, d)
    write_md(a, b, c, d, e)
    print("Exp A readiness:", a["readiness"]["score"],
          a["readiness"]["verdict"])
    print("Exp B funnel:", {k: v for k, v in b.items()})
    print("Exp C confidence:",
          {k: v["confidence"] for k, v in c.items()})
    print("Exp D diff:", d["counts"], "delta", d["severity_delta"])
    print("Exp E alerts:", len(e))
    print("wrote results/results.md and results/charts.png")


if __name__ == "__main__":
    main()
