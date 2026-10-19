"""Seeded multi-layer telemetry generators with injected incidents.

Five layers: infra, platform, application, sre, business. Minute
granularity, T=480 minutes (8h). A cascading incident (CDN TLS handshake
failure) propagates infra -> platform -> application -> sre -> business,
plus independent intra-layer incidents for the anomaly-detection
experiments. Every generator records ground-truth anomaly intervals so
experiments can score detectors honestly.
"""
from __future__ import annotations

import numpy as np

LAYERS = ["infra", "platform", "application", "sre", "business"]

T_MIN = 480
CASCADE_T0 = 240  # cascade onset (minutes)


def _ar1(n: int, phi: float, sigma: float, rng: np.random.Generator,
         base: float = 0.0) -> np.ndarray:
    x = np.empty(n)
    x[0] = base + rng.normal(0, sigma)
    for t in range(1, n):
        x[t] = base + phi * (x[t - 1] - base) + rng.normal(0, sigma)
    return x


def _ramp(n: int, t0: int, dur: int, amp: float) -> np.ndarray:
    """0 before t0, linear ramp to amp over dur, flat after."""
    r = np.zeros(n)
    for t in range(t0, min(n, t0 + dur)):
        r[t] = amp * (t - t0 + 1) / dur
    r[min(n, t0 + dur):] = amp
    return r


def _pulse(n: int, t0: int, t1: int, amp: float) -> np.ndarray:
    r = np.zeros(n)
    r[t0:min(n, t1)] = amp
    return r


# Ground-truth causal chain of the cascade (used by correlate.py).
CASCADE_CHAIN = [
    {"layer": "infra", "onset": CASCADE_T0,
     "metric": "net_latency_ms",
     "label": "cross-region latency rises 15->28ms (CDN TLS failures)"},
    {"layer": "platform", "onset": CASCADE_T0 + 5,
     "metric": "mem_pressure_pct",
     "label": "retry storm drives k8s node memory pressure 55->87%"},
    {"layer": "application", "onset": CASCADE_T0 + 10,
     "metric": "checkout_error_rate",
     "label": "checkout 502s: error rate 0.1%->1.2%, p95 200ms->8200ms"},
    {"layer": "sre", "onset": CASCADE_T0 + 15,
     "metric": "slo_success",
     "label": "checkout SLO success 99.9%->98.7%, error budget burning"},
    {"layer": "business", "onset": CASCADE_T0 + 20,
     "metric": "failed_txns",
     "label": "failed transactions spike; $1.7M/hr revenue at risk"},
]


def gen_infra(seed: int) -> dict:
    rng = np.random.default_rng(seed)
    n = T_MIN
    lat = 15.0 + _ar1(n, 0.7, 0.8, rng)
    lat = lat + _ramp(n, CASCADE_T0, 5, 13.0)          # -> ~28ms, sharp onset
    lat = lat + _pulse(n, CASCADE_T0 + 10, CASCADE_T0 + 40, 17.0) * (
        rng.random(n) > 0.7)                            # p95 spikes ~45ms
    cpu = {}
    for i, node in enumerate(["node-a", "node-b", "node-c"]):
        base = 55.0 + 5.0 * i
        s = base + _ar1(n, 0.85, 2.0, rng)
        if i == 1:  # cascade: retry load on node-b
            s = s + _ramp(n, CASCADE_T0 + 5, 20, 25.0)
        cpu[node] = np.clip(s, 0, 100)
    anomalies = [
        (CASCADE_T0, CASCADE_T0 + 15, "net_latency_ms", "cascade"),
        (CASCADE_T0 + 5, CASCADE_T0 + 35, "cpu_pct[node-b]", "cascade"),
        (60, 80, "cpu_pct[node-c]", "independent: batch job"),
    ]
    cpu["node-c"] = cpu["node-c"] + _pulse(n, 60, 80, 30.0)
    return {"net_latency_ms": lat, "cpu_pct": cpu, "anomalies": anomalies}


def gen_platform(seed: int) -> dict:
    rng = np.random.default_rng(seed + 101)
    n = T_MIN
    mem = 55.0 + _ar1(n, 0.9, 1.5, rng)
    mem = mem + _ramp(n, CASCADE_T0 + 5, 40, 32.0)       # -> ~87%
    crashloop = np.zeros(n)
    crashloop[100:160] = 7.0                             # secrets misconfig
    crashloop = crashloop + rng.poisson(0.05, n)
    anomalies = [
        (CASCADE_T0 + 5, CASCADE_T0 + 55, "mem_pressure_pct", "cascade"),
        (100, 160, "crashloop_pods", "independent: expired secrets"),
    ]
    return {"mem_pressure_pct": np.clip(mem, 0, 100),
            "crashloop_pods": crashloop, "anomalies": anomalies}


def gen_application(seed: int) -> dict:
    rng = np.random.default_rng(seed + 202)
    n = T_MIN
    err = 0.001 + np.abs(_ar1(n, 0.9, 0.0004, rng))
    err = err + _ramp(n, CASCADE_T0 + 10, 30, 0.011)      # -> 1.2%
    lat = 200.0 + _ar1(n, 0.85, 15.0, rng)
    lat = lat + _ramp(n, CASCADE_T0 + 10, 30, 8000.0)    # -> 8200ms
    lat[30:40] = lat[30:40] + 600.0                      # canary blip
    anomalies = [
        (CASCADE_T0 + 10, CASCADE_T0 + 50, "checkout_error_rate", "cascade"),
        (CASCADE_T0 + 10, CASCADE_T0 + 50, "checkout_latency_p95_ms", "cascade"),
        (30, 40, "checkout_latency_p95_ms", "independent: canary blip"),
    ]
    return {"checkout_error_rate": np.clip(err, 0, 1),
            "checkout_latency_p95_ms": np.clip(lat, 0, None),
            "anomalies": anomalies}


def gen_sre(seed: int) -> dict:
    rng = np.random.default_rng(seed + 303)
    n = T_MIN
    slo = 0.999 + _ar1(n, 0.9, 0.0004, rng)
    slo = slo - _ramp(n, CASCADE_T0 + 15, 25, 0.012)      # -> 98.7%
    slo = np.clip(slo, 0, 1)
    burn = np.zeros(n)                                    # error budget burn %/h
    burn[CASCADE_T0 + 15:] = 45.0 / 24 + rng.normal(0, 0.5, n - CASCADE_T0 - 15)
    burn = np.clip(burn, 0, None)
    anomalies = [(CASCADE_T0 + 15, CASCADE_T0 + 50, "slo_success", "cascade"),
                 (CASCADE_T0 + 15, CASCADE_T0 + 50, "error_budget_burn", "cascade")]
    return {"slo_success": slo, "error_budget_burn": burn,
            "anomalies": anomalies}


def gen_business(seed: int) -> dict:
    rng = np.random.default_rng(seed + 404)
    n = T_MIN
    failed = 5.0 + np.abs(_ar1(n, 0.85, 1.2, rng))
    failed = failed + _ramp(n, CASCADE_T0 + 20, 30, 55.0)  # -> ~60/min
    revenue_loss = failed * 1367.0 * 60 / 1e6             # $M per hour
    csat = 85.0 + _ar1(n, 0.95, 0.4, rng)
    csat = csat - _ramp(n, CASCADE_T0 + 20, 90, 13.0)     # -> ~72
    anomalies = [(CASCADE_T0 + 20, CASCADE_T0 + 60, "failed_txns", "cascade"),
                 (CASCADE_T0 + 20, CASCADE_T0 + 60, "revenue_loss_per_hr", "cascade"),
                 (CASCADE_T0 + 20, CASCADE_T0 + 120, "csat", "cascade")]
    return {"failed_txns": np.clip(failed, 0, None),
            "revenue_loss_per_hr": np.clip(revenue_loss, 0, None),
            "csat": np.clip(csat, 0, 100), "anomalies": anomalies}


GENERATORS = {"infra": gen_infra, "platform": gen_platform,
              "application": gen_application, "sre": gen_sre,
              "business": gen_business}


def simulate(seed: int) -> dict:
    """Generate all five layers. Returns {layer: {...series..., 'anomalies': [...]}}."""
    return {layer: GENERATORS[layer](seed) for layer in LAYERS}
