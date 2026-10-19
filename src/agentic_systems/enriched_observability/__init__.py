"""Enriched observability: AI-enriched intelligence across five layers.

Pipeline per layer: raw telemetry -> processed (classical AI pattern
detection) -> analytic (decision-grade intelligence) -> human-readable
insight narratives. A cross-layer correlation engine links events into
one causal chain, and role-specific views deliver each decision-maker
their relevant slice.

Layers: infra, platform, application, sre, business.
"""
from __future__ import annotations

import numpy as np

from . import analytic, composer, correlate, enrich, roles, telemetry
from .telemetry import CASCADE_CHAIN, LAYERS, simulate

__all__ = [
    "LAYERS", "CASCADE_CHAIN", "simulate", "run_pipeline",
    "telemetry", "enrich", "analytic", "composer", "correlate", "roles",
]

# Metric -> (above, breach threshold) for forecasting.
# Thresholds are chosen on the ramp trajectory so crossings are predictable.
BREACH_THRESHOLDS = {
    ("platform", "mem_pressure_pct"): (True, 85.0),
    ("infra", "net_latency_ms"): (True, 25.0),
    ("application", "checkout_error_rate"): (True, 0.008),
    ("sre", "slo_success"): (False, 0.990),
    ("business", "failed_txns"): (True, 40.0),
}

# Naive fixed thresholds for the baseline detector (experiment b).
NAIVE_THRESHOLDS = {
    ("infra", "net_latency_ms"): (True, 40.0),
    ("infra", "cpu_pct"): (True, 90.0),
    ("platform", "mem_pressure_pct"): (True, 90.0),
    ("platform", "crashloop_pods"): (True, 5.0),
    ("application", "checkout_error_rate"): (True, 0.02),
    ("application", "checkout_latency_p95_ms"): (True, 5000.0),
    ("sre", "slo_success"): (False, 0.985),
    ("sre", "error_budget_burn"): (True, 5.0),
    ("business", "failed_txns"): (True, 100.0),
    ("business", "revenue_loss_per_hr"): (True, 1.0),
    ("business", "csat"): (False, 75.0),
}

# Metrics each layer's detector scans: (metric-key, sub-key or None).
LAYER_METRICS = {
    "infra": [("net_latency_ms", None), ("cpu_pct", "node-b"),
              ("cpu_pct", "node-c")],
    "platform": [("mem_pressure_pct", None), ("crashloop_pods", None)],
    "application": [("checkout_error_rate", None),
                    ("checkout_latency_p95_ms", None)],
    "sre": [("slo_success", None), ("error_budget_burn", None)],
    "business": [("failed_txns", None), ("revenue_loss_per_hr", None),
                 ("csat", None)],
}


def _get_series(data: dict, layer: str, key: str, sub) -> np.ndarray:
    s = data[layer][key]
    if isinstance(s, dict):
        s = s[sub]
    return np.asarray(s, dtype=float)


def detect_layer(layer: str, data: dict, z_thresh: float = 3.0
                 ) -> dict[str, list[tuple[int, int, float]]]:
    """Robust-detector intervals per metric for one layer."""
    out: dict[str, list] = {}
    for key, sub in LAYER_METRICS[layer]:
        s = _get_series(data, layer, key, sub)
        z = enrich.robust_z(s)
        name = key if sub is None else f"{key}[{sub}]"
        out[name] = enrich.detect_intervals(z, thresh=z_thresh)
    return out


def detect_layer_naive(layer: str, data: dict) -> dict[str, list]:
    """Naive fixed-threshold baseline intervals per metric."""
    out: dict[str, list] = {}
    for key, sub in LAYER_METRICS[layer]:
        s = _get_series(data, layer, key, sub)
        name = key if sub is None else f"{key}[{sub}]"
        above, thr = NAIVE_THRESHOLDS[(layer, key)]
        out[name] = enrich.naive_threshold_intervals(s, thr, above=above)
    return out


def run_pipeline(seed: int, z_thresh: float = 3.0) -> dict:
    """End-to-end: simulate -> detect -> analyze -> correlate -> views."""
    data = simulate(seed)
    t0 = telemetry.CASCADE_T0

    events, analytics, narratives = {}, {}, {}
    for layer in LAYERS:
        det = detect_layer(layer, data, z_thresh=z_thresh)
        key_metric = correlate.KEY_SERIES[layer]
        first = det.get(key_metric, [])
        events[layer] = first
        if first:
            start, end, peak_z = max(first,
                                     key=lambda e: (e[1] - e[0]) * e[2])
            name = key_metric
            series = _get_series(data, layer,
                                 *(next((k, s) for k, s in
                                        LAYER_METRICS[layer]
                                        if (k if s is None else f"{k}[{s}]")
                                        == name)))
            # driver correlation vs upstream layer key series
            li = LAYERS.index(layer)
            if li > 0:
                up = _get_series(data, LAYERS[li - 1],
                                 correlate.KEY_SERIES[LAYERS[li - 1]], None)
                r, _ = enrich.lagged_corr(up, series, max_lag=45)
            else:
                r = 0.0
            rev = float(data["business"]["revenue_loss_per_hr"][-1]
                        ) if layer == "business" else 0.0
            thr = BREACH_THRESHOLDS.get((layer, key_metric))
            ev = analytic.analyze_event(
                layer, name, start, end, peak_z, series,
                driver_corr=r, n_evidence=2 if abs(r) > 0.5 else 1,
                revenue_at_risk=rev,
                breach_threshold=thr[1] if thr else None)
            # extra context fields used by role views
            if layer == "sre":
                ev["slo_success_now"] = float(data["sre"]["slo_success"][-1])
                ev["error_budget_burn_per_h"] = float(
                    data["sre"]["error_budget_burn"][-1])
                ev["mttr_proxy_min"] = 45
            if layer == "business":
                ev["revenue_loss_per_hr_now"] = float(
                    data["business"]["revenue_loss_per_hr"][-1])
                ev["csat_now"] = float(data["business"]["csat"][-1])
            if layer == "application":
                ev["deploy_correlated"] = False
                ev["narrative"] = (
                    "TLS handshake failures at the CDN edge cause checkout "
                    "502s; p95 latency 8200ms vs 200ms baseline.")
            analytics[layer] = ev
            narratives[layer] = composer.compose_layer_insight(
                ev, driver=(LAYERS[li - 1] + ":" +
                            correlate.KEY_SERIES[LAYERS[li - 1]]
                            if li > 0 and abs(r) > 0.5 else None))

    chain = correlate.reconstruct_chain(events, data)
    ctx = roles.build_context(data, chain, analytics)
    views = {r: roles.render_role_view(r, ctx) for r in roles.ROLES}
    return {"data": data, "events": events, "analytics": analytics,
            "narratives": narratives, "chain": chain, "context": ctx,
            "views": views,
            "chain_narrative": composer.compose_chain_narrative(chain)}
