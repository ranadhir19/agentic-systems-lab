"""Layered telemetry simulator.

Six observability layers (infra, network, platform, app, service, product)
emit minute-granularity metric streams. Incidents are injected as
sigma-shifts on specific metrics. Cascade incidents propagate across
adjacent layers with delays, modelling cross-boundary failures whose
symptoms surface far from their origin.

All randomness flows from an explicit seed; nothing is read from global
RNG state.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

LAYERS = ["infra", "network", "platform", "app", "service", "product"]

# layer -> metric -> (baseline mean, baseline std)
METRICS = {
    "infra": {"cpu_util": (55.0, 6.0), "disk_io_wait": (4.0, 1.5)},
    "network": {"rtt_ms": (40.0, 5.0), "packet_loss": (0.10, 0.05)},
    "platform": {"pod_restarts": (0.2, 0.4), "queue_depth": (120.0, 25.0)},
    "app": {"error_rate": (0.5, 0.2), "p99_latency_ms": (320.0, 30.0)},
    "service": {"slo_burn": (0.8, 0.2), "checkout_fail_rate": (1.2, 0.4)},
    "product": {"conversion_rate": (3.4, 0.3), "dau_k": (210.0, 8.0)},
}

# Intra-layer incident templates: (name, layer, {metric: shift_sigma}, duration)
INTRA_TEMPLATES = [
    ("cpu_hot", "infra", {"cpu_util": 6.0}, 45),
    ("disk_stall", "infra", {"disk_io_wait": 7.0}, 30),
    ("net_congestion", "network", {"rtt_ms": 6.0, "packet_loss": 8.0}, 40),
    ("pod_crashloop", "platform", {"pod_restarts": 6.0}, 50),
    ("queue_buildup", "platform", {"queue_depth": 5.0}, 35),
    ("bad_deploy", "app", {"error_rate": 7.0, "p99_latency_ms": 4.0}, 55),
    ("db_slowdown", "service", {"slo_burn": 5.0, "checkout_fail_rate": 4.0}, 45),
    ("promo_bug", "product", {"conversion_rate": -4.5}, 60),
]

# Cascade templates: (name, [(delay, layer, metric, shift_sigma, duration)]).
# Segments walk adjacent layers so every step crosses a real boundary.
CASCADE_TEMPLATES = [
    ("infra_overload_cascade", [
        (0, "infra", "cpu_util", 5.5, 60),
        (10, "network", "rtt_ms", 4.5, 50),
        (20, "platform", "queue_depth", 5.0, 45),
        (32, "app", "p99_latency_ms", 5.0, 45),
    ]),
    ("network_partition_cascade", [
        (0, "network", "packet_loss", 7.0, 50),
        (8, "platform", "queue_depth", 5.0, 45),
        (18, "app", "error_rate", 5.5, 40),
        (30, "service", "checkout_fail_rate", 4.5, 35),
    ]),
    ("deploy_cascade", [
        (0, "platform", "pod_restarts", 6.0, 45),
        (12, "app", "error_rate", 5.0, 45),
        (25, "service", "slo_burn", 4.5, 40),
        (38, "product", "conversion_rate", -3.0, 40),
    ]),
]

AR_PHI = 0.3  # baseline autocorrelation


@dataclass
class Segment:
    incident_id: str
    kind: str  # "intra" | "cascade"
    layer: str
    metric: str
    t0: int
    t1: int


@dataclass
class Incident:
    id: str
    kind: str
    name: str
    segments: list = field(default_factory=list)

    @property
    def onset(self) -> int:
        return min(s.t0 for s in self.segments)

    @property
    def end(self) -> int:
        return max(s.t1 for s in self.segments)

    @property
    def layers(self) -> list:
        return [s.layer for s in self.segments]


@dataclass
class SimResult:
    telemetry: dict  # (layer, metric) -> np.ndarray
    incidents: list  # list[Incident]
    T: int
    seed: int

    def segments(self) -> list:
        out = []
        for inc in self.incidents:
            out.extend(inc.segments)
        return out


def _baseline_series(rng: np.random.Generator, mu: float, sd: float,
                     T: int) -> np.ndarray:
    eps = rng.normal(0.0, sd, T)
    x = np.empty(T)
    x[0] = mu + eps[0]
    for t in range(1, T):
        x[t] = mu + AR_PHI * (x[t - 1] - mu) + eps[t] * np.sqrt(1 - AR_PHI ** 2)
    return x


def simulate(seed: int = 0, T: int = 1440,
             n_cascade: int = 3) -> SimResult:
    """Simulate one day (T minutes) of telemetry with injected incidents.

    Uses every intra-layer template once and the first ``n_cascade``
    cascade templates, placed at shuffled, jittered slots.
    """
    rng = np.random.default_rng(seed)
    telemetry = {}
    for layer, mets in METRICS.items():
        for metric, (mu, sd) in mets.items():
            telemetry[(layer, metric)] = _baseline_series(rng, mu, sd, T)

    jobs = []
    for name, layer, shifts, dur in INTRA_TEMPLATES:
        jobs.append(("intra", name, [(0, layer, m, sh, dur)
                                     for m, sh in shifts.items()]))
    for name, segs in CASCADE_TEMPLATES[:n_cascade]:
        jobs.append(("cascade", name, segs))

    order = rng.permutation(len(jobs))
    slots = np.linspace(120, T - 220, len(jobs))
    slots = slots + rng.integers(-30, 31, size=len(jobs))
    slots = np.clip(slots, 60, T - 160).astype(int)

    incidents = []
    for k, j in enumerate(order):
        kind, name, segs = jobs[j]
        onset = int(slots[k])
        inc = Incident(id=f"{kind[0].upper()}{k:02d}", kind=kind, name=name)
        for delay, layer, metric, shift, dur in segs:
            t0 = onset + delay
            t1 = min(T, t0 + dur)
            sd = METRICS[layer][metric][1]
            telemetry[(layer, metric)][t0:t1] += shift * sd
            inc.segments.append(Segment(inc.id, kind, layer, metric, t0, t1))
        incidents.append(inc)

    # Keep physical metrics non-negative.
    for (layer, metric), x in telemetry.items():
        if metric in ("packet_loss", "pod_restarts", "error_rate", "slo_burn",
                      "checkout_fail_rate", "conversion_rate", "dau_k",
                      "disk_io_wait", "queue_depth", "cpu_util", "rtt_ms",
                      "p99_latency_ms"):
            np.clip(x, 0.0, None, out=x)

    incidents.sort(key=lambda i: i.onset)
    return SimResult(telemetry=telemetry, incidents=incidents, T=T, seed=seed)
