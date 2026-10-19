"""Semantic freshness monitor.

Semantics decay: distributions shift, behaviors change, graphs evolve.
The monitor compares a newly extracted artifact against the stored
version and reports a drift score plus a boolean verdict. Thresholds are
per-layer and fixed so false-positive rates are measurable.
"""
from __future__ import annotations

import numpy as np

THRESHOLDS = {
    "L1": 0.50,   # max mean-shift in pooled-std units across fields
    "L2": 0.30,   # centroid cosine drift + max transition-cell change
    "L3": 0.30,   # edge-set Jaccard distance
    "L4": 0.40,   # dominant-period or cascade change
    "L5": 0.34,   # DAG structural Hamming distance (normalized)
    "L6": 0.20,   # intent-distribution total variation
    "L7": 0.25,   # motif support drift
}


def _cos(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))


def drift_l1(new, old):
    """Max |mean shift| in pooled-std units across profiled fields."""
    scores = []
    for f, pn in new["profiles"].items():
        po = old["profiles"].get(f)
        if po is None:
            continue
        s = np.sqrt((pn["std"] ** 2 + po["std"] ** 2) / 2) + 1e-12
        scores.append(abs(pn["mean"] - po["mean"]) / s)
    return max(scores) if scores else 0.0


def drift_l2(new, old):
    """Mean centroid cosine drift + max transition-matrix cell change,
    after optimal centroid matching (Hungarian) so cluster relabeling is
    not mistaken for drift. Max (not mean) cell change is used because
    behavior breaks concentrate in a few transitions."""
    from scipy.optimize import linear_sum_assignment
    cn = np.array(new["centroids"])
    co = np.array(old["centroids"])
    k = min(len(cn), len(co))
    cn, co = cn[:k], co[:k]
    # cost = cosine distance
    cost = np.zeros((k, k))
    for i in range(k):
        for j in range(k):
            cost[i, j] = 1 - _cos(cn[i], co[j])
    ri, cj = linear_sum_assignment(cost)
    cos_d = float(cost[ri, cj].mean())
    tn = np.array(new["transition_matrices"])
    to = np.array(old["transition_matrices"])
    k2 = min(len(tn), len(to), k)
    match = dict(zip(ri, cj))
    mat_max = 0.0
    for i in range(k2):
        j = match.get(i, i)
        if j < len(to):
            mat_max = max(mat_max, float(np.abs(tn[i] - to[j]).max()))
    return float((cos_d + mat_max) / 2)


def drift_l3(new, old):
    """Jaccard distance over (src, dst, type) edge sets."""
    en = {(e["src"], e["dst"], e["type"]) for e in new["edges"]}
    eo = {(e["src"], e["dst"], e["type"]) for e in old["edges"]}
    if not en and not eo:
        return 0.0
    return 1.0 - len(en & eo) / max(len(en | eo), 1)


def drift_l4(new, old):
    """1 if dominant period or cascade set changed, else scaled trend shift."""
    pn = {k: v["dominant_period_h"] for k, v in new["series"].items()}
    po = {k: v["dominant_period_h"] for k, v in old["series"].items()}
    if pn != po:
        return 1.0
    cn = {(c["src"], c["dst"], c["lag_h"]) for c in new["cascades"]}
    co = {(c["src"], c["dst"], c["lag_h"]) for c in old["cascades"]}
    if cn != co:
        return 0.8
    shift = max(abs(new["series"][k]["trend_per_h"]
                    - old["series"][k]["trend_per_h"])
                for k in pn) if pn else 0.0
    return min(1.0, shift * 50)


def drift_l5(new, old):
    """Normalized structural Hamming distance between DAG edge sets."""
    en = set(map(tuple, new["edges"]))
    eo = set(map(tuple, old["edges"]))
    return 1.0 - len(en & eo) / max(len(en | eo), 1)


def drift_l6(new, old):
    """Total-variation distance between intent distributions."""
    from collections import Counter
    cn = Counter(f["intent"] for f in new["frames"])
    co = Counter(f["intent"] for f in old["frames"])
    tot_n, tot_o = sum(cn.values()), sum(co.values())
    keys = set(cn) | set(co)
    return 0.5 * sum(abs(cn[k] / tot_n - co[k] / tot_o) for k in keys)


def drift_l7(new, old):
    """Drift in motif support distribution."""
    sn = np.array([m["support"] for m in new["motifs"]], float)
    so = np.array([m["support"] for m in old["motifs"]], float)
    sn /= sn.sum() + 1e-12
    so /= so.sum() + 1e-12
    n = max(len(sn), len(so))
    sn = np.pad(sn, (0, n - len(sn)))
    so = np.pad(so, (0, n - len(so)))
    return float(0.5 * np.abs(sn - so).sum())


_DRIFT_FNS = {"L1": drift_l1, "L2": drift_l2, "L3": drift_l3,
              "L4": drift_l4, "L5": drift_l5, "L6": drift_l6,
              "L7": drift_l7}


class FreshnessMonitor:
    """Compare a fresh artifact against the stored version."""

    def __init__(self, thresholds=None):
        self.thresholds = dict(THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

    def check(self, layer, new_artifact, old_artifact):
        fn = _DRIFT_FNS[layer]
        score = fn(new_artifact, old_artifact)
        thr = self.thresholds[layer]
        return {"layer": layer, "score": round(float(score), 4),
                "threshold": thr, "drifted": bool(score >= thr)}
