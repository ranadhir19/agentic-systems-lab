"""Boundary-assessment agentic workflow.

Continuously assesses observability power per layer *and* at layer
boundaries from telemetry and alerts alone:

* per-layer: bin-level TP/TN/FP/FN, precision/recall/F1, segment-level
  recall, mean time-to-detect;
* per-boundary: for every cascade step crossing an adjacent layer pair,
  whether the downstream deviation was detected (recall), mean
  time-to-detect, and an F1 whose false positives are cross-layer
  alerts fired inside the cascade window that match nothing;
* gap ranking: boundaries ordered by observability gap (1 - F1), so the
  weakest boundary -- and the targeted fix it needs -- is identified
  without access to ground-truth design intent.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .layers import LAYERS

BIN = 30
MATCH_WINDOW = 60


@dataclass
class LayerStats:
    layer: str
    tp: int; tn: int; fp: int; fn: int
    precision: float; recall: float; f1: float
    seg_recall: float; mean_ttd: float; n_segments: int


def _prf(tp: int, fp: int, fn: int):
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


def assess_layers(sim, alerts_by_layer: dict) -> dict:
    """Per-layer observability power from alerts vs ground-truth segments."""
    alerts = [a for lst in alerts_by_layer.values() for a in lst]
    nbins = sim.T // BIN
    stats = {}
    for layer in LAYERS:
        seg_list = [s for s in sim.segments() if s.layer == layer]
        seg_bins, pred_bins = set(), set()
        for s in seg_list:
            for b in range(s.t0 // BIN, min(nbins, s.t1 // BIN + 1)):
                seg_bins.add(b)
        for a in alerts:
            if a.layer == layer:
                pred_bins.add(a.t // BIN)
        tp = len(seg_bins & pred_bins)
        fp = len(pred_bins - seg_bins)
        fn = len(seg_bins - pred_bins)
        tn = nbins - tp - fp - fn
        p, r, f = _prf(tp, fp, fn)
        hits, ttds = 0, []
        for s in seg_list:
            cands = [a.t for a in alerts
                     if a.layer == layer and s.t0 <= a.t <= s.t0 + MATCH_WINDOW]
            if cands:
                hits += 1
                ttds.append(min(cands) - s.t0)
        stats[layer] = LayerStats(
            layer, tp, tn, fp, fn, p, r, f,
            seg_recall=hits / len(seg_list) if seg_list else 0.0,
            mean_ttd=float(np.mean(ttds)) if ttds else float("nan"),
            n_segments=len(seg_list))
    return stats


def boundary_events(sim) -> list:
    """Every cascade step that crosses an adjacent layer pair."""
    evs = []
    for inc in sim.incidents:
        if inc.kind != "cascade":
            continue
        segs = sorted(inc.segments, key=lambda s: s.t0)
        for s1, s2 in zip(segs, segs[1:]):
            i1, i2 = LAYERS.index(s1.layer), LAYERS.index(s2.layer)
            if abs(i1 - i2) == 1:
                a, b = (s1.layer, s2.layer) if i1 < i2 else (s2.layer, s1.layer)
                evs.append({"incident": inc.id, "boundary": (a, b),
                            "t_up": s1.t0, "t_down": s2.t0,
                            "down_layer": s2.layer, "down_metric": s2.metric,
                            "up_layer": s1.layer, "up_metric": s1.metric})
    return evs


@dataclass
class BoundaryStats:
    boundary: tuple
    n: int
    recall: float
    mean_ttd: float
    precision: float
    f1: float
    gap: float  # 1 - f1


def assess_boundaries(sim, alerts_by_layer: dict) -> dict:
    """Per-boundary observability power on cascade crossings.

    A crossing counts as *linked* (observed at the boundary) when either
    adjacent observer raises a cross-layer alert on one of the crossing's
    own deviating metrics inside the cascade window -- i.e. someone
    actually saw across the boundary while the cascade crossed it. This
    is the operational meaning of "observability power at the boundary":
    not whether each side noticed its own blip, but whether the crossing
    itself was visible. Requiring the alert to be on the deviating
    metric keeps lucky spurious alarms from counting as links.

    False positives are cross-layer alerts involving the pair that fire
    during quiet periods (no incident window nearby): boundary cry-wolf
    alarms.
    """
    alerts = [a for lst in alerts_by_layer.values() for a in lst]
    inc_windows = [(inc.onset - 30, inc.end + 60) for inc in sim.incidents]

    def in_any_window(t: int) -> bool:
        return any(a <= t <= b for a, b in inc_windows)

    out = {}
    for ev in boundary_events(sim):
        out.setdefault(ev["boundary"], []).append(ev)
    stats = {}
    for boundary, evs in out.items():
        tp = 0
        ttds = []
        for ev in evs:
            link = [al for al in alerts
                    if al.cross and al.observer in boundary
                    and ((al.layer == ev["down_layer"]
                          and al.metric == ev["down_metric"])
                         or (al.layer == ev["up_layer"]
                             and al.metric == ev["up_metric"]))
                    and ev["t_up"] - 15 <= al.t <= ev["t_down"] + 60]
            if link:
                tp += 1
                # Negative = the crossing was visible before the
                # downstream symptom onset (a leading indicator).
                ttds.append(min(al.t for al in link) - ev["t_down"])
        fn = len(evs) - tp
        fp = sum(1 for al in alerts
                 if al.cross and al.observer in boundary
                 and al.layer in boundary and not in_any_window(al.t))
        p, r, f = _prf(tp, fp, fn)
        stats[boundary] = BoundaryStats(
            boundary, len(evs), r,
            float(np.mean(ttds)) if ttds else float("nan"),
            p, f, 1.0 - f)
    return stats


def rank_boundaries(bstats: dict) -> list:
    """Boundaries ordered by observability gap, worst first."""
    return sorted(bstats.values(), key=lambda s: (-s.gap, s.boundary))
