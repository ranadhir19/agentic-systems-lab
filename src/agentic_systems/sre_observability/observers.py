"""Per-layer observer agents.

Each observer sees its own layer's raw metric streams (strong signal) and
only lossy, delayed, aggregated summaries of every other layer (weak
signal). The asymmetry is the mechanistic source of the boundary
problem: intra-layer anomalies are detected reliably while
cross-boundary deviations are routinely missed.

Detection is a trailing z-score threshold with a consecutive-hits rule
and a per-metric cooldown, identical logic for own and foreign views;
only the signal quality differs.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .layers import LAYERS, METRICS

OWN_THRESH = 3.5
CONSEC = 2
OWN_COOLDOWN = 20
CROSS_COOLDOWN = 30


@dataclass
class ExportCfg:
    """How one observer sees another layer's telemetry."""
    delay: int = 8       # minutes of staleness
    avg: int = 15        # aggregation window (minutes)
    noise_mult: float = 1.0  # extra noise as multiple of metric std
    thresh: float = 4.0


DEFAULT_EXPORT = ExportCfg()
# The service<->product boundary is starved by design: product analytics
# exports are heavily delayed and noisy, modelling the classic
# "infra/app metrics never reach the product dashboard" blind spot.
WEAK_EXPORT = ExportCfg(delay=40, avg=15, noise_mult=3.0, thresh=6.0)

_FIX_OVERRIDES: dict = {}


def reset_export_overrides() -> None:
    _FIX_OVERRIDES.clear()


def install_export_fix(a: str, b: str) -> None:
    """Targeted fix: give a boundary near-raw cross-layer visibility."""
    _FIX_OVERRIDES[frozenset((a, b))] = ExportCfg(
        delay=2, avg=10, noise_mult=0.5, thresh=3.5)


def export_cfg(observer: str, source: str) -> ExportCfg:
    key = frozenset((observer, source))
    if key in _FIX_OVERRIDES:
        return _FIX_OVERRIDES[key]
    if key == frozenset(("service", "product")):
        return WEAK_EXPORT
    return DEFAULT_EXPORT


@dataclass
class Alert:
    t: int
    observer: str   # which agent raised it
    layer: str      # which layer the anomaly is in
    metric: str
    z: float
    cross: bool     # True if raised from a foreign-layer summary view


def trailing_z(x: np.ndarray, win: int = 180, min_win: int = 90) -> np.ndarray:
    """Robust z-score of each point vs the trailing window before it.

    Uses trailing median / MAD (via a shifted centered median filter) so
    a recent incident inside the window cannot contaminate its own
    baseline -- the classic failure of mean/std baselines under incident
    crowding. ``trail[t]`` covers ``x[t-win:t]`` exactly.
    """
    from scipy.ndimage import median_filter

    x = np.asarray(x, dtype=float)
    T = len(x)
    half = win // 2
    cf = median_filter(x, size=win, mode="nearest")
    trail_med = np.empty(T)
    trail_med[half:] = cf[:T - half]
    trail_med[:half] = cf[0]
    dev = np.abs(x - trail_med)
    cfd = median_filter(dev, size=win, mode="nearest")
    trail_mad = np.empty(T)
    trail_mad[half:] = cfd[:T - half]
    trail_mad[:half] = cfd[0]
    z = np.zeros(T)
    ok = trail_mad > 1e-9
    z[ok] = 0.6745 * (x[ok] - trail_med[ok]) / trail_mad[ok]
    z[:min_win] = 0.0
    return z


def detect_runs(z: np.ndarray, thresh: float, consec: int = CONSEC,
                cooldown: int = OWN_COOLDOWN) -> list:
    """Times where |z| >= thresh on `consec` of any 3 consecutive steps.

    The 2-of-3 rule tolerates single-step noise dips inside a sustained
    shift, which a strict consecutive rule misses.
    """
    hits = np.abs(z) >= thresh
    out = []
    t, T = 0, len(z)
    while t < T - 2:
        if hits[t:t + 3].sum() >= consec:
            out.append(t + 2)
            t = t + 3 + cooldown
            continue
        t += 1
    return out


def summary_view(x: np.ndarray, delay: int, avg: int,
                 noise_std: float, rng: np.random.Generator) -> np.ndarray:
    """What an observer sees of a foreign metric: delayed, averaged, noisy."""
    x = np.asarray(x, dtype=float)
    T = len(x)
    cs = np.concatenate([[0.0], np.cumsum(x)])
    idx = np.arange(T)
    hi = np.clip(idx - delay, 1, T)
    lo = np.clip(hi - avg, 0, T - 1)
    w = np.maximum(hi - lo, 1)
    s = (cs[hi] - cs[lo]) / w
    if noise_std > 0:
        s = s + rng.normal(0.0, noise_std, T)
    return s


class LayerObserver:
    """One observer agent per observability layer."""

    def __init__(self, layer: str):
        if layer not in LAYERS:
            raise ValueError(f"unknown layer {layer}")
        self.layer = layer

    def observe(self, sim, rng: np.random.Generator) -> list:
        alerts = []
        # Own layer: raw streams, sensitive threshold.
        for metric in METRICS[self.layer]:
            x = sim.telemetry[(self.layer, metric)]
            z = trailing_z(x)
            for t in detect_runs(z, OWN_THRESH, CONSEC, OWN_COOLDOWN):
                alerts.append(Alert(t, self.layer, self.layer, metric,
                                    float(z[t]), False))
        # Foreign layers: lossy summaries, desensitized threshold.
        for layer in LAYERS:
            if layer == self.layer:
                continue
            cfg = export_cfg(self.layer, layer)
            for metric, (mu, sd) in METRICS[layer].items():
                x = sim.telemetry[(layer, metric)]
                s = summary_view(x, cfg.delay, cfg.avg,
                                 cfg.noise_mult * sd, rng)
                z = trailing_z(s)
                for t in detect_runs(z, cfg.thresh, CONSEC, CROSS_COOLDOWN):
                    alerts.append(Alert(t, self.layer, layer, metric,
                                        float(z[t]), True))
        alerts.sort(key=lambda a: a.t)
        return alerts


def observe_all(sim, seed: int = 0) -> dict:
    """Run every layer observer; returns {layer: [Alert]}."""
    out = {}
    for layer in LAYERS:
        rng = np.random.default_rng(seed * 1000 + LAYERS.index(layer) + 7)
        out[layer] = LayerObserver(layer).observe(sim, rng)
    return out
