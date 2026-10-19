"""Enriched-observability experiments (all seeded; every number measured).

exp_a -- cascading incident end-to-end: per-layer detection delay,
         chain link recall / onset MAE, enrichment wall-clock time.
exp_b -- anomaly detection precision/recall per layer: robust z-score
         detector vs naive fixed-threshold baseline (ground truth from
         the seeded generators).
exp_c -- forecasting: predicted vs actual time-to-breach at onset+10.
exp_d -- cross-layer links: link precision/recall vs the 4 true
         consecutive-layer links; spurious-link count.
exp_e -- role views: relevance rubric per role, enriched views vs
         raw-dump baseline.
exp_f -- triage proxy: raw alert count vs enriched chain items.

Outputs: results/results.md and results/charts.png.
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from agentic_systems.enriched_observability import (
    LAYERS, correlate, detect_layer, detect_layer_naive, enrich, roles,
    run_pipeline, telemetry,
)
from agentic_systems.enriched_observability.telemetry import CASCADE_T0

SEEDS = [7, 11, 42, 0, 99]
FORECAST_CASES = [
    ("platform", "mem_pressure_pct", 85.0, True),
    ("application", "checkout_error_rate", 0.008, True),
    ("sre", "slo_success", 0.990, False),
    ("business", "failed_txns", 40.0, True),
]
RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")


def _gt_mask(anomalies: list, n: int) -> np.ndarray:
    m = np.zeros(n, dtype=bool)
    for s, e, *_ in anomalies:
        m[s:min(e, n)] = True
    return m


def exp_a() -> dict:
    delays, recalls, maes, timings = [], [], [], []
    truth_onset = {c["layer"]: c["onset"] for c in telemetry.CASCADE_CHAIN}
    for seed in SEEDS:
        t0 = time.perf_counter()
        p = run_pipeline(seed)
        timings.append(time.perf_counter() - t0)
        det = {c["layer"]: c["onset"] for c in p["chain"]}
        for layer in LAYERS:
            if layer in det:
                delays.append((layer, det[layer] - truth_onset[layer]))
        rec, mae = correlate.chain_link_recall(p["chain"])
        recalls.append(rec)
        maes.append(mae)
    by_layer: dict[str, list] = {}
    for layer, d in delays:
        by_layer.setdefault(layer, []).append(d)
    return {
        "mean_delay": {l: round(float(np.mean(v)), 1)
                       for l, v in by_layer.items()},
        "mean_link_recall": round(float(np.mean(recalls)), 3),
        "mean_onset_mae_min": round(float(np.mean(maes)), 1),
        "mean_pipeline_wall_s": round(float(np.mean(timings)), 3),
    }


def _pr(pred_mask: np.ndarray, gt_mask: np.ndarray) -> tuple[float, float]:
    tp = int(np.sum(pred_mask & gt_mask))
    fp = int(np.sum(pred_mask & ~gt_mask))
    fn = int(np.sum(~pred_mask & gt_mask))
    prec = tp / max(1, tp + fp)
    rec = tp / max(1, tp + fn)
    return prec, rec


def exp_b() -> dict:
    out: dict[str, dict] = {}
    for layer in LAYERS:
        pr_r, rc_r, pr_n, rc_n = [], [], [], []
        for seed in SEEDS:
            data = telemetry.simulate(seed)
            n = telemetry.T_MIN
            gt_by_metric: dict[str, np.ndarray] = {}
            for s, e, metric, _label in data[layer]["anomalies"]:
                m = gt_by_metric.setdefault(metric, np.zeros(n, dtype=bool))
                m[s:min(e, n)] = True
            det = detect_layer(layer, data)
            det_n = detect_layer_naive(layer, data)
            pm = np.zeros(n, dtype=bool)
            nm = np.zeros(n, dtype=bool)
            gm = np.zeros(n, dtype=bool)
            for metric, g in gt_by_metric.items():
                gm |= g
                for s, e, *_ in det.get(metric, []):
                    pm[s:min(e, n)] = True
                for s, e, *_ in det_n.get(metric, []):
                    nm[s:min(e, n)] = True
            p, r = _pr(pm, gm)
            pn, rn = _pr(nm, gm)
            pr_r.append(p); rc_r.append(r); pr_n.append(pn); rc_n.append(rn)
        out[layer] = {
            "robust_prec": round(float(np.mean(pr_r)), 3),
            "robust_rec": round(float(np.mean(rc_r)), 3),
            "naive_prec": round(float(np.mean(pr_n)), 3),
            "naive_rec": round(float(np.mean(rc_n)), 3),
        }
    return out


def exp_c() -> dict:
    errs = []
    rows = []
    for seed in SEEDS:
        data = telemetry.simulate(seed)
        for layer, key, thr, above in FORECAST_CASES:
            s = np.asarray(data[layer][key], float)
            det = detect_layer(layer, data)
            ivs = det.get(key, [])
            if not ivs:
                continue
            onset = max(ivs, key=lambda e: (e[1] - e[0]) * e[2])[0]
            tq = onset + 10
            fb = enrich.forecast_breach(s[:tq], thr)
            actual = next(
                (t for t in range(tq, len(s))
                 if (s[t] >= thr if above else s[t] <= thr)), None)
            if fb is not None and actual is not None:
                errs.append(abs(fb - (actual - tq)))
                rows.append((fb, actual - tq))
    return {"n": len(errs),
            "mae_min": round(float(np.mean(errs)), 1) if errs else None,
            "rows": [(round(a, 1), b) for a, b in rows]}


def exp_d() -> dict:
    recalls, spurious = [], []
    truth = {("infra", "platform"), ("platform", "application"),
             ("application", "sre"), ("sre", "business")}
    for seed in SEEDS:
        p = run_pipeline(seed)
        got_layers = [c["layer"] for c in p["chain"]]
        got = set(zip(got_layers[:-1], got_layers[1:]))
        recalls.append(len(truth & got) / len(truth))
        spurious.append(len(got - truth))
    return {"mean_link_recall": round(float(np.mean(recalls)), 3),
            "mean_spurious_links": round(float(np.mean(spurious)), 2)}


def exp_e() -> dict:
    enr, raw = {r: [] for r in roles.ROLES}, {r: [] for r in roles.ROLES}
    for seed in SEEDS:
        p = run_pipeline(seed)
        for role in roles.ROLES:
            enr[role].append(roles.relevance_score(
                role, roles.render_role_view(role, p["context"])))
            raw[role].append(roles.relevance_score(
                role, roles.raw_dump_view(p["context"])))
    return {
        "enriched": {r: round(float(np.mean(v)), 3) for r, v in enr.items()},
        "raw_dump": {r: round(float(np.mean(v)), 3) for r, v in raw.items()},
    }


def exp_f() -> dict:
    raw_counts, enr_counts = [], []
    for seed in SEEDS:
        p = run_pipeline(seed)
        data = p["data"]
        n_raw = sum(len(v) for layer in LAYERS
                    for v in detect_layer(layer, data).values())
        raw_counts.append(n_raw)
        enr_counts.append(len(p["chain"]))
    return {"mean_raw_alerts": round(float(np.mean(raw_counts)), 1),
            "mean_enriched_items": round(float(np.mean(enr_counts)), 1)}


def _bar(ax, labels, series: list[tuple[str, list]], ylabel: str,
         title: str):
    x = np.arange(len(labels))
    w = 0.8 / len(series)
    for i, (name, vals) in enumerate(series):
        ax.bar(x + (i - (len(series) - 1) / 2) * w, vals, width=w, label=name)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(fontsize=8)


def main() -> None:
    a = exp_a()
    b = exp_b()
    c = exp_c()
    d = exp_d()
    e = exp_e()
    f = exp_f()

    os.makedirs(RESULTS, exist_ok=True)
    lines = ["# Enriched Observability — experiment results",
             "", f"Seeds: {SEEDS}. Every number measured.",
             "",
             "## (a) Cascade end-to-end",
             f"Mean detection delay per layer (min): {a['mean_delay']}",
             f"Mean chain link recall: {a['mean_link_recall']}",
             f"Mean onset MAE (min): {a['mean_onset_mae_min']}",
             f"Mean pipeline wall time (s): {a['mean_pipeline_wall_s']}",
             "",
             "## (b) Anomaly detection: robust vs naive (per-minute P/R)",
             ""]
    for layer, m in b.items():
        lines.append(
            f"{layer}: robust P={m['robust_prec']} R={m['robust_rec']} | "
            f"naive P={m['naive_prec']} R={m['naive_rec']}")
    lines += ["",
              "## (c) Forecasting time-to-breach (at onset+10)",
              f"n={c['n']}, MAE={c['mae_min']} min",
              "",
              "## (d) Cross-layer links",
              f"Mean link recall: {d['mean_link_recall']}, "
              f"mean spurious links: {d['mean_spurious_links']}",
              "",
              "## (e) Role-view relevance (rubric 0..1)",
              f"Enriched: {e['enriched']}",
              f"Raw dump baseline: {e['raw_dump']}",
              "",
              "## (f) Triage proxy",
              f"Mean raw alerts: {f['mean_raw_alerts']}, "
              f"mean enriched chain items: {f['mean_enriched_items']}",
              ""]
    with open(os.path.join(RESULTS, "results.md"), "w") as fh:
        fh.write("\n".join(lines))

    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    layers = LAYERS
    _bar(axes[0, 0], layers,
         [("detection delay (min)",
           [a["mean_delay"].get(l, 0) for l in layers])],
         "minutes", "(a) Detection delay vs true onset")
    _bar(axes[0, 1], layers,
         [("robust P", [b[l]["robust_prec"] for l in layers]),
          ("robust R", [b[l]["robust_rec"] for l in layers]),
          ("naive P", [b[l]["naive_prec"] for l in layers]),
          ("naive R", [b[l]["naive_rec"] for l in layers])],
         "score", "(b) Anomaly detection: robust vs naive")
    if c["rows"]:
        pred, act = zip(*c["rows"])
        axes[1, 0].scatter(act, pred, s=40)
        mx = max(max(pred), max(act)) * 1.1
        axes[1, 0].plot([0, mx], [0, mx], "k--", lw=1)
        axes[1, 0].set_xlabel("actual lead time (min)")
        axes[1, 0].set_ylabel("predicted lead time (min)")
        axes[1, 0].set_title("(c) Forecast: predicted vs actual breach lead")
    _bar(axes[1, 1], roles.ROLES,
         [("enriched", [e["enriched"][r] for r in roles.ROLES]),
          ("raw dump", [e["raw_dump"][r] for r in roles.ROLES])],
         "relevance", "(e) Role-view relevance")
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "charts.png"), dpi=110)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
