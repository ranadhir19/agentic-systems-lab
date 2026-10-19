"""Analytic stage: from processed signals to decision-grade intelligence.

For each detected anomaly interval this produces:
- failure_probability: calibrated-ish mapping of anomaly score + trend,
- root_cause_confidence: from cross-series correlation evidence,
- impact_score: normalized business impact (0..1),
- recommended_action: rule-based remediation suggestion.

Rules are transparent and deterministic; the measured contribution is the
pipeline (detection -> forecast -> recommendation), not the wording.
"""
from __future__ import annotations

import numpy as np

from . import enrich


def _sigmoid(x: float) -> float:
    return float(1.0 / (1.0 + np.exp(-x)))


def failure_probability(peak_z: float, slope: float,
                        slope_scale: float = 1.0) -> float:
    """P(failure | anomaly): rises with |z| and with adverse trend."""
    return _sigmoid(0.9 * (abs(peak_z) - 3.0) + 0.6 * slope_scale * abs(slope))


def root_cause_confidence(corr: float, n_evidence: int) -> float:
    """Confidence that the correlated driver is the root cause."""
    strength = min(1.0, abs(corr))
    ev = min(1.0, n_evidence / 3.0)
    return _sigmoid(4.0 * (0.65 * strength + 0.35 * ev) - 2.0)


def impact_score(layer: str, peak_z: float, revenue_at_risk: float = 0.0,
                 users_affected: float = 0.0) -> float:
    """0..1 business impact score; business-layer metrics dominate."""
    layer_w = {"infra": 0.25, "platform": 0.35, "application": 0.6,
               "sre": 0.7, "business": 1.0}[layer]
    money = min(1.0, revenue_at_risk / 2.0)   # $2M/hr saturates
    users = min(1.0, users_affected / 5000.0)
    sig = _sigmoid(0.9 * (abs(peak_z) - 3.0))
    return float(np.clip(0.5 * layer_w * sig + 0.3 * money + 0.2 * users,
                         0.0, 1.0))


# (layer, metric-substring) -> remediation recommendation templates.
RECOMMENDATIONS = [
    (("infra", "net_latency"), "Fail over cross-region traffic away from the "
     "degraded path; verify CDN/TLS certificate chain on the affected edge."),
    (("infra", "cpu_pct"), "Migrate workloads off the saturated node; "
     "check for retry storms from downstream before adding capacity."),
    (("platform", "mem_pressure"), "Scale the affected cluster (add nodes); "
     "cap retry budgets on callers to stop the pressure feedback loop."),
    (("platform", "crashloop"), "Inspect pod events for misconfigured "
     "secrets or env; rotate secrets via the vault and redeploy."),
    (("application", "checkout_error_rate"), "Check CDN/TLS handshake health "
     "on the checkout path; consider rolling back the latest deploy if "
     "error onset aligns with a release."),
    (("application", "checkout_latency"), "Trace p95 latency by downstream "
     "dependency; shed load or fail over the slowest dependency."),
    (("sre", "slo_success"), "Declare incident; fail over to the backup "
     "payment gateway before the error budget exhausts."),
    (("sre", "error_budget"), "Freeze non-critical deploys; prioritize "
     "reliability work until burn rate normalizes."),
    (("business", "failed_txns"), "Engage the backup payment path immediately; "
     "prepare customer comms for the affected checkout window."),
    (("business", "revenue_loss"), "Escalate to executive bridge; approve "
     "emergency failover — revenue impact exceeds the incident threshold."),
    (("business", "csat"), "Trigger proactive customer outreach for failed "
     "checkouts; monitor social sentiment for spillover."),
]


def recommend(layer: str, metric: str) -> str:
    for (lyr, sub), text in RECOMMENDATIONS:
        if lyr == layer and sub in metric:
            return text
    return ("Investigate the anomalous metric; correlate with upstream "
            "layers before acting.")


def analyze_event(layer: str, metric: str, start: int, end: int, peak_z: float,
                  series: np.ndarray, driver_corr: float = 0.0,
                  n_evidence: int = 1, revenue_at_risk: float = 0.0,
                  users_affected: float = 0.0,
                  breach_threshold: float | None = None) -> dict:
    """Full analytic record for one detected anomaly interval."""
    slope = enrich.trend_slope(series[:end])
    ttb = (enrich.forecast_breach(series[:end], breach_threshold)
           if breach_threshold is not None else None)
    return {
        "layer": layer, "metric": metric, "start": start, "end": end,
        "peak_z": round(peak_z, 2), "slope": round(slope, 4),
        "failure_probability": round(failure_probability(peak_z, slope), 3),
        "root_cause_confidence": round(
            root_cause_confidence(driver_corr, n_evidence), 3),
        "impact_score": round(impact_score(layer, peak_z, revenue_at_risk,
                                           users_affected), 3),
        "time_to_breach_min": ttb,
        "recommended_action": recommend(layer, metric),
    }
