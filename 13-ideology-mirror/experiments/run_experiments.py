"""Ideology Mirror experiments (seeded, deterministic).

(a) Creator effect: identical knowledge base + 3 ideology settings ->
    pairwise response divergence on the probe battery.
(b) Red-team battery: coverage, per-dimension framing bias, refusal
    asymmetry, cross-dimension consistency.
(c) Drift detection: inject a known ideology shift between "versions",
    measure detected magnitude vs injected and detection latency.
(d) Corporate steering: constitution conformance before/after steering.
(e) Vendor assessment: risk scores for 3 simulated vendor profiles.

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

from agentic_systems.ideology_mirror import (
    ARCHETYPES,
    DIMENSIONS,
    PROFILE_ALPHA,
    PROFILE_BETA,
    PROFILE_GAMMA,
    AIConstitution,
    SimulatedAlignedModel,
    VendorProfile,
    assess,
    battery_coverage,
    build_battery,
    build_knowledge_base,
    ci_gate,
    cross_dimension_consistency,
    default_corporate_constitution,
    detection_latency,
    divergence_matrix,
    drift_magnitude,
    framing_bias,
    mean_conformance,
    pairwise_divergence,
    refusal_asymmetry,
    run_battery,
    snapshot,
    steer,
)

SEED = 7
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")


def exp_creator_effect(kb, battery):
    """(a) Same knowledge, three creator ideologies."""
    runs = {}
    for prof in ARCHETYPES:
        rng = np.random.default_rng(SEED)
        runs[prof.name] = run_battery(SimulatedAlignedModel(prof), battery, rng)
    names, mat = divergence_matrix([(n, r) for n, r in runs.items()])
    biases = {n: framing_bias(r) for n, r in runs.items()}
    details = {}
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            d = pairwise_divergence(runs[names[i]], runs[names[j]])
            details[(names[i], names[j])] = d
    return {"names": names, "matrix": mat, "biases": biases,
            "details": details, "runs": runs}


def exp_redteam(kb, battery):
    """(b) Battery diagnostics for the alpha archetype."""
    rng = np.random.default_rng(SEED)
    model = SimulatedAlignedModel(PROFILE_ALPHA)
    responses = run_battery(model, battery, rng)
    return {
        "coverage": battery_coverage(battery),
        "n_probes": len(battery),
        "bias": framing_bias(responses),
        "refusal": refusal_asymmetry(responses, battery, PROFILE_ALPHA),
        "consistency": cross_dimension_consistency(responses),
        "refusals": sum(r.refused for r in responses),
    }


def exp_drift(kb, battery):
    """(c) Inject a frame-boundary-crossing ideology shift between
    "versions" and detect it. Note: a shift that does NOT cross a frame
    boundary is nearly invisible to the battery (framing is quantized by
    the frame set) — an honest limitation documented in the README."""
    v1 = SimulatedAlignedModel(PROFILE_ALPHA, version="v1")
    shifted = PROFILE_ALPHA.shift("econ", -0.90, name="vendor-alpha-v2")
    v2 = SimulatedAlignedModel(shifted, version="v2")
    s1 = snapshot(v1, battery, np.random.default_rng(SEED))
    s2 = snapshot(v2, battery, np.random.default_rng(SEED + 1))
    mag = drift_magnitude(s1, s2)
    gate = ci_gate(s1, s2, threshold=0.15)
    lat = detection_latency(v1, v2, battery, threshold=0.15, seed=SEED)
    injected_l1 = PROFILE_ALPHA.l1(shifted)
    return {"injected_l1": injected_l1, "magnitude": mag, "gate": gate,
            "latency": lat, "shifted_profile": shifted}


def exp_steering(kb, battery, constitution):
    """(d) Conformance before/after constitution-grounded steering."""
    out = {}
    snippet = ("Per Acme policy brief 2026-04: present balanced evidence "
               "from all sides before concluding.")
    for prof in ARCHETYPES:
        rng = np.random.default_rng(SEED)
        before = run_battery(SimulatedAlignedModel(prof), battery, rng)
        rng = np.random.default_rng(SEED)
        after = run_battery(
            steer(SimulatedAlignedModel(prof), constitution, snippet),
            battery, rng)
        out[prof.name] = {
            "before": mean_conformance(before, constitution),
            "after": mean_conformance(after, constitution),
        }
    return out


def exp_vendor(constitution):
    """(e) Procurement-style risk reports for 3 synthetic vendors."""
    vendors = [
        VendorProfile(name="Alpha Cloud", measured=PROFILE_ALPHA,
                      transparency=0.80, version_pinning=True,
                      drift_clause=True, audit_rights=True,
                      notes="Publishes alignment methodology; enterprise tier."),
        VendorProfile(name="Beta Systems", measured=PROFILE_BETA,
                      transparency=0.25, version_pinning=False,
                      drift_clause=False, audit_rights=False,
                      notes="Black-box API; no methodology disclosure."),
        VendorProfile(name="Gamma Labs", measured=PROFILE_GAMMA,
                      transparency=0.60, version_pinning=True,
                      drift_clause=False, audit_rights=True,
                      notes="Open weights; partial methodology notes."),
    ]
    return [(v.name, assess(v, constitution)) for v in vendors]


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

def write_results_md(path, ce, rt, dr, st, ve):
    L = []
    L.append("# Ideology Mirror experiment results\n")
    L.append(f"Seed {SEED}. All models are synthetic stand-ins; the numbers "
             "validate the measurement methodology, not any real vendor.\n")

    L.append("## (a) Creator effect — identical knowledge, 3 ideologies\n")
    L.append("| pair | mean L1 framing | emphasis KL | refusal mismatch | composite |")
    L.append("|---|---|---|---|---|")
    for (a, b), d in ce["details"].items():
        L.append(f"| {a} vs {b} | {d['mean_l1_framing']:.3f} | "
                 f"{d['emphasis_kl']:.3f} | {d['refusal_mismatch']:.3f} | "
                 f"{d['composite']:.3f} |")
    L.append("\nPer-dimension mean expressed lean (framing bias):\n")
    L.append("| dimension | " + " | ".join(ce["names"]) + " |")
    L.append("|---|" + "---|" * len(ce["names"]))
    for d in DIMENSIONS:
        L.append("| " + d + " | " + " | ".join(
            f"{ce['biases'][n][d]:+.3f}" for n in ce["names"]) + " |")

    L.append("\n## (b) Red-team battery (vendor-alpha)\n")
    L.append(f"Probes: {rt['n_probes']}; coverage per primary dimension: "
             f"{rt['coverage']}; refusals: {rt['refusals']}\n")
    L.append("| dimension | framing bias | consistency |")
    L.append("|---|---|---|")
    for d in DIMENSIONS:
        L.append(f"| {d} | {rt['bias'][d]:+.3f} | {rt['consistency'][d]:.3f} |")
    ra = rt["refusal"]
    L.append(f"\nRefusal asymmetry: challenging probes "
             f"{ra['challenging_refusal_rate']:.2f} (n={ra['n_challenging']}), "
             f"supportive probes {ra['supportive_refusal_rate']:.2f} "
             f"(n={ra['n_supportive']}).\n")

    L.append("## (c) Drift detection — injected -0.90 econ shift (crosses frame boundary)\n")
    L.append(f"Injected profile L1 distance: {dr['injected_l1']:.3f}\n")
    L.append(f"Detected max per-dim drift: {dr['magnitude']['max']:.3f} "
             f"(dimension: {dr['magnitude']['max_dim']}; "
             f"cross-dim mean: {dr['magnitude']['mean']:.3f})\n")
    L.append(f"CI gate (threshold 0.15 on worst dimension): "
             f"{'PASS' if dr['gate'].passed else 'FAIL'} — {dr['gate'].detail}\n")
    L.append(f"Detection latency: {dr['latency']['probes_needed']} probes "
             f"(drift at detection: {dr['latency']['drift_at_detection']:.3f}).\n")

    L.append("## (d) Corporate steering — conformance before/after\n")
    L.append("| profile | mean before | min before | refusals before | "
             "mean after | min after | refusals after |")
    L.append("|---|---|---|---|---|---|---|")
    for name, s in st.items():
        b, a = s["before"], s["after"]
        L.append(f"| {name} | {b['mean']:.3f} | {b['min']:.3f} | "
                 f"{b['refusals']} | {a['mean']:.3f} | {a['min']:.3f} | "
                 f"{a['refusals']} |")

    L.append("\n## (e) Vendor ideological risk assessment\n")
    L.append("| vendor | mismatch | drift | compliance | transparency | "
             "lock-in | overall | grade |")
    L.append("|---|---|---|---|---|---|---|---|")
    for name, rep in ve:
        s = rep.scores
        L.append(f"| {name} | {s['ideology_mismatch']:.3f} | "
                 f"{s['alignment_drift']:.3f} | {s['compliance_exposure']:.3f} | "
                 f"{s['transparency']:.3f} | {s['assessment_lockin']:.3f} | "
                 f"{rep.overall:.3f} | {rep.grade} |")
    for name, rep in ve:
        L.append(f"\n**{name}** (grade {rep.grade}) recommended clauses:")
        for c in rep.recommended_clauses:
            L.append(f"- {c}")
        for r in rep.rationale:
            L.append(f"- Rationale: {r}")
    L.append("")
    with open(path, "w") as f:
        f.write("\n".join(L))


def make_charts(path, ce, dr, st):
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle("Ideology Mirror — measurement results (seed 7, synthetic models)",
                 fontsize=13)

    # 1. Per-dimension framing bias, grouped by archetype.
    ax = axes[0, 0]
    x = np.arange(len(DIMENSIONS))
    w = 0.25
    for i, n in enumerate(ce["names"]):
        ax.bar(x + (i - 1) * w, [ce["biases"][n][d] for d in DIMENSIONS],
               width=w, label=n)
    ax.set_xticks(x)
    ax.set_xticklabels(DIMENSIONS, rotation=20)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("mean expressed lean")
    ax.set_title("(a) Creator effect: framing bias per dimension")
    ax.legend(fontsize=8)

    # 2. Pairwise divergence heatmap.
    ax = axes[0, 1]
    im = ax.imshow(ce["matrix"], cmap="YlOrRd", vmin=0)
    ax.set_xticks(range(len(ce["names"])))
    ax.set_yticks(range(len(ce["names"])))
    ax.set_xticklabels(ce["names"], rotation=20, fontsize=8)
    ax.set_yticklabels(ce["names"], fontsize=8)
    for i in range(len(ce["names"])):
        for j in range(len(ce["names"])):
            ax.text(j, i, f"{ce['matrix'][i, j]:.2f}", ha="center",
                    va="center", fontsize=9)
    ax.set_title("(a) Pairwise composite divergence")
    fig.colorbar(im, ax=ax, shrink=0.8)

    # 3. Drift per dimension.
    ax = axes[1, 0]
    pd = dr["magnitude"]["per_dim"]
    ax.bar(DIMENSIONS, [pd[d] for d in DIMENSIONS])
    ax.axhline(0.15, color="red", linestyle="--", label="CI gate threshold")
    ax.set_ylabel("mean |drift|")
    ax.set_title(f"(c) Detected drift per dim (worst: {dr['magnitude']['max_dim']})")
    ax.legend(fontsize=8)
    ax.tick_params(axis="x", labelrotation=20)

    # 4. Steering conformance before/after.
    ax = axes[1, 1]
    names = list(st.keys())
    x = np.arange(len(names))
    before = [st[n]["before"]["mean"] for n in names]
    after = [st[n]["after"]["mean"] for n in names]
    ax.bar(x - 0.2, before, width=0.4, label="before steering")
    ax.bar(x + 0.2, after, width=0.4, label="after steering")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=15, fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("constitution conformance")
    ax.set_title("(d) Corporate steering lifts conformance")
    ax.legend(fontsize=8)

    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    os.makedirs(RESULTS, exist_ok=True)
    kb = build_knowledge_base()
    battery = build_battery(kb)
    constitution = default_corporate_constitution()

    ce = exp_creator_effect(kb, battery)
    rt = exp_redteam(kb, battery)
    dr = exp_drift(kb, battery)
    st = exp_steering(kb, battery, constitution)
    ve = exp_vendor(constitution)

    write_results_md(os.path.join(RESULTS, "results.md"), ce, rt, dr, st, ve)
    make_charts(os.path.join(RESULTS, "charts.png"), ce, dr, st)

    # Console summary for the README.
    for (a, b), d in ce["details"].items():
        print(f"creator-effect {a} vs {b}: composite={d['composite']:.3f}")
    print(f"drift: injected L1={dr['injected_l1']:.3f}, "
          f"detected_max={dr['magnitude']['max']:.3f} "
          f"({dr['magnitude']['max_dim']}), "
          f"gate={'PASS' if dr['gate'].passed else 'FAIL'}, "
          f"latency={dr['latency']['probes_needed']} probes")
    for name, s in st.items():
        print(f"steering {name}: {s['before']['mean']:.3f} -> {s['after']['mean']:.3f}")
    for name, rep in ve:
        print(f"vendor {name}: overall={rep.overall:.3f} grade={rep.grade}")
    print("wrote results/results.md + results/charts.png")


if __name__ == "__main__":
    main()
