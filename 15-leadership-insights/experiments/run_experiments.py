"""Leadership-insights experiments (seeded, deterministic).

(a) Metric accuracy: estimated review latency / escalation rates vs the
    generator's injected ground truth.
(b) Injected-issue recovery: does each lens find its planted problem?
(c) Dollar quantification: license reclaim savings vs expected.
(d) Siloed vs integrated: which insights need joined sources.
(e) Entity-resolution accuracy across the five sources.

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
import pandas as pd

from agentic_systems.leadership_insights import (
    generate_enterprise, build_unified, resolution_scores,
    dora_metrics, pr_analytics, detect_bottlenecks,
    license_report, reclaim_opportunities,
    resolution_timelines, csat_drivers, EscalationPredictor,
    productivity_satisfaction, skill_gaps, retention_risk, retention_scores,
    run_insights,
)

SEED = 7
HERE = os.path.dirname(__file__)
RES = os.path.join(HERE, "..", "results")


def exp_a_accuracy(u, gt):
    """Estimated metrics vs injected ground truth."""
    pr = pr_analytics(u)
    rows = []
    for team, true_mean in gt["true_review_mean"].items():
        est = pr.loc[team, "review_mean_h"]
        rows.append({"team": team, "true_mean_h": round(true_mean, 1),
                     "est_mean_h": est,
                     "rel_err": round(abs(est - true_mean) / true_mean, 3)})
    df = pd.DataFrame(rows)
    # Escalation rate for the injected cluster service.
    s = u["snow"]
    esc = s.groupby("service").escalated.mean()
    return df, {"checkout-web esc_rate": round(float(esc["checkout-web"]), 3),
                "org esc_rate": round(float(s.escalated.mean()), 3)}


def exp_b_recovery(u, gt):
    """Each lens vs its planted problem."""
    out = {}
    # 1. Bottleneck team.
    bn = detect_bottlenecks(u)
    flagged = set(bn[bn.bottleneck].index)
    out["bottleneck"] = {
        "flagged": sorted(flagged),
        "expected": [gt["bottleneck_team"]],
        "hit": gt["bottleneck_team"] in flagged,
        "false_positives": sorted(flagged - {gt["bottleneck_team"]}),
    }
    # 2. License waste: reclaimed ids vs planted waste ids.
    df, _ = reclaim_opportunities(u)
    found = set(df.employee_id)
    truth = gt["waste_premium_ids"] | gt["waste_suite_ids"]
    tp = len(found & truth)
    out["license_waste"] = {
        "precision": round(tp / len(found), 3) if found else 0.0,
        "recall": round(tp / len(truth), 3) if truth else 0.0,
        "n_found": len(found), "n_truth": len(truth),
    }
    # 3. Retention risk top-10 vs planted flags.
    rr = retention_risk(u)
    out["retention"] = retention_scores(rr, k=10)
    # 4. Escalation cluster: service with max escalation rate.
    s = u["snow"]
    esc = s.groupby("service").escalated.mean()
    top = esc.idxmax()
    out["escalation"] = {"top_service": top,
                         "expected": gt["escalation_cluster_service"],
                         "hit": top == gt["escalation_cluster_service"],
                         "top_rate": round(float(esc.max()), 3)}
    return out


def exp_c_dollars(u, gt):
    _, summary = reclaim_opportunities(u)
    expected = (12 * 180 + 8 * 95) * 12  # planted waste, $/yr
    return {"reclaim_annual": summary["annual_saving"],
            "expected_annual": expected,
            "match": abs(summary["annual_saving"] - expected) < 1e-6}


def exp_d_siloed(u):
    integ = run_insights(u, mode="integrated")
    silo = run_insights(u, mode="siloed")
    missed = [i["title"] for i in integ if i["n_sources"] > 1]
    return {"integrated_n": len(integ), "siloed_n": len(silo),
            "missed_n": len(missed), "missed": missed,
            "siloed_titles": [i["title"] for i in silo]}


def exp_e_resolution(u):
    return resolution_scores(u)


def exp_f_predictor(u):
    s = u["snow"].reset_index(drop=True)
    tr, te = s.iloc[:400], s.iloc[400:560]
    m = EscalationPredictor().fit(tr)
    thresh = float(tr.escalated.mean())
    sc = m.scores(te, threshold=thresh)
    sc["threshold"] = round(thresh, 3)
    return sc


def make_charts(u):
    fig, ax = plt.subplots(2, 2, figsize=(12, 9))
    fig.suptitle("Leadership Insights — seeded run (seed 7)", fontsize=13)

    # 1. DORA: deploys/week per team.
    dora = dora_metrics(u)
    ax[0, 0].bar(dora.index, dora.deploys_per_week, color="#6ea8fe")
    ax[0, 0].set_title("Deployment frequency (per week)")
    ax[0, 0].tick_params(axis="x", rotation=30)

    # 2. License utilization.
    lr = license_report(u)
    ax[0, 1].bar(lr.index, lr.utilization, color="#5eead4")
    ax[0, 1].set_title("License utilization (active / assigned)")
    ax[0, 1].tick_params(axis="x", rotation=20)
    ax[0, 1].set_ylim(0, 1.05)

    # 3. CSAT vs resolution time.
    s = u["snow"].dropna(subset=["csat"]).sample(300, random_state=7)
    ax[1, 0].scatter(np.log1p(s.resolve_h), s.csat, alpha=0.35, s=12,
                     color="#f0b35e")
    ax[1, 0].set_xlabel("log1p(resolution hours)")
    ax[1, 0].set_ylabel("CSAT")
    ax[1, 0].set_title("CSAT degrades with resolution time")

    # 4. Siloed vs integrated insight coverage.
    d = exp_d_siloed(u)
    ax[1, 1].bar(["siloed\n(1 source)", "integrated\n(joined)"],
                 [d["siloed_n"], d["integrated_n"]], color=["#99a4ba", "#f08787"])
    ax[1, 1].set_title(f"Insights found: {d['siloed_n']} vs {d['integrated_n']} "
                       f"({d['missed_n']} need joins)")

    fig.tight_layout()
    os.makedirs(RES, exist_ok=True)
    fig.savefig(os.path.join(RES, "charts.png"), dpi=110)
    plt.close(fig)


def main():
    data, gt = generate_enterprise(SEED)
    u = build_unified(data)

    a_df, a_esc = exp_a_accuracy(u, gt)
    b = exp_b_recovery(u, gt)
    c = exp_c_dollars(u, gt)
    d = exp_d_siloed(u)
    e = exp_e_resolution(u)
    f = exp_f_predictor(u)

    # Extra lens outputs for the report.
    dora = dora_metrics(u)
    lr = license_report(u)
    cd = csat_drivers(u)
    gaps, _ = skill_gaps(u)

    make_charts(u)

    lines = []
    lines.append("# Leadership Insights — experiment results\n")
    lines.append(f"Seed {SEED}. All numbers from actual runs.\n")
    lines.append("## (a) Metric accuracy vs ground truth\n")
    lines.append(a_df.to_string(index=False))
    lines.append(f"\nEscalation rates: {a_esc}\n")
    lines.append("## (b) Injected-issue recovery\n")
    for k, v in b.items():
        lines.append(f"- **{k}**: {v}")
    lines.append("\n## (c) Dollar quantification\n")
    lines.append(f"- Reclaimable: ${c['reclaim_annual']:,.0f}/yr "
                 f"(expected ${c['expected_annual']:,.0f}/yr) — match={c['match']}")
    lines.append("\n## (d) Siloed vs integrated\n")
    lines.append(f"- Integrated finds {d['integrated_n']} insights; "
                 f"siloed finds {d['siloed_n']}. Missed without joins "
                 f"({d['missed_n']}):")
    for t in d["missed"]:
        lines.append(f"  - {t}")
    lines.append("\n## (e) Entity resolution\n")
    lines.append(f"- {e}")
    lines.append("\n## (f) Escalation predictor (client lens)\n")
    lines.append(f"- train 400 / test 160, threshold=train base rate: {f}")
    lines.append("\n## Lens outputs\n")
    lines.append("### DORA\n" + dora.to_string())
    lines.append("\n### License report\n" + lr.to_string())
    lines.append(f"\n### CSAT drivers\n- {cd['corr_csat_logresolve']=}, "
                 f"{cd['corr_csat_escalated']=}")
    lines.append("\n### Top skill gaps\n" + gaps.to_string(index=False))
    with open(os.path.join(RES, "results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    print("=== (a) accuracy ===")
    print(a_df.to_string(index=False), a_esc)
    print("=== (b) recovery ===", b)
    print("=== (c) dollars ===", c)
    print("=== (d) siloed ===", {k: v for k, v in d.items() if k != "missed"},
          "\nmissed:", d["missed"])
    print("=== (e) resolution ===", e)
    print("wrote results/results.md + charts.png")


if __name__ == "__main__":
    main()
