"""Shared math helpers: k-means, distribution stats, independence tests.

Everything is seeded explicitly; no global RNG state.
"""
from __future__ import annotations

import numpy as np
from scipy import stats as sstats


def kmeans(X, k, seed=0, iters=100):
    """Lloyd's k-means. Returns (labels, centroids). Deterministic."""
    rng = np.random.default_rng(seed)
    X = np.asarray(X, dtype=float)
    idx = rng.choice(len(X), size=k, replace=False)
    C = X[idx].copy()
    labels = np.zeros(len(X), dtype=int)
    for _ in range(iters):
        d2 = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        new = d2.argmin(1)
        if np.array_equal(new, labels) and _ > 0:
            break
        labels = new
        for j in range(k):
            if (labels == j).any():
                C[j] = X[labels == j].mean(0)
    return labels, C


def adjusted_rand_index(a, b):
    """ARI between two labelings (no sklearn)."""
    a = np.asarray(a)
    b = np.asarray(b)
    # map string labels to ints
    _, ai = np.unique(a, return_inverse=True)
    _, bi = np.unique(b, return_inverse=True)
    n = len(a)
    cont = np.zeros((ai.max() + 1, bi.max() + 1))
    np.add.at(cont, (ai, bi), 1)
    sum_comb = lambda v: (v * (v - 1) / 2).sum()
    idx = sum_comb(cont.sum(1)) * sum_comb(cont.sum(0)) / max(sum_comb(np.array([n])), 1e-12)
    expected = idx
    max_idx = 0.5 * (sum_comb(cont.sum(1)) + sum_comb(cont.sum(0)))
    actual = sum_comb(cont)
    return (actual - expected) / max(max_idx - expected, 1e-12)


def dist_profile(x):
    """Compact distribution profile for one numeric vector."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    hist, _ = np.histogram(x, bins=20)
    p = hist / max(hist.sum(), 1)
    ent = float(-(p[p > 0] * np.log(p[p > 0])).sum())
    return {
        "n": int(len(x)),
        "mean": float(x.mean()), "std": float(x.std()),
        "skew": float(sstats.skew(x)), "kurt": float(sstats.kurtosis(x)),
        "p5": float(np.percentile(x, 5)), "p25": float(np.percentile(x, 25)),
        "p50": float(np.percentile(x, 50)), "p75": float(np.percentile(x, 75)),
        "p95": float(np.percentile(x, 95)),
        "entropy": ent,
    }


def drift_stat(a, b):
    """Shift magnitude between two samples, in pooled-std units (L1)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    s = np.sqrt((a.var() + b.var()) / 2) + 1e-12
    return float(abs(a.mean() - b.mean()) / s)


def partial_corr(C, i, j, cond):
    """Partial correlation of i,j given cond, from correlation matrix C."""
    idx = [i, j] + list(cond)
    sub = C[np.ix_(idx, idx)]
    try:
        inv = np.linalg.inv(sub + 1e-9 * np.eye(len(idx)))
    except np.linalg.LinAlgError:
        return 0.0
    r = -inv[0, 1] / np.sqrt(max(inv[0, 0] * inv[1, 1], 1e-12))
    return float(np.clip(r, -1, 1))


def fisher_z_test(r, n, k):
    """p-value for partial correlation r with n samples, k conditioned vars."""
    if abs(r) >= 1.0:
        return 0.0
    z = 0.5 * np.log((1 + r) / (1 - r))
    dof = n - k - 3
    if dof <= 0:
        return 1.0
    stat = abs(z) * np.sqrt(dof)
    return float(2 * (1 - sstats.norm.cdf(stat)))


def dag_precision_recall(found, truth):
    """Edge sets as (src, dst) tuples. Returns (precision, recall)."""
    f, t = set(found), set(truth)
    if not f:
        return 0.0, 0.0
    tp = len(f & t)
    return tp / len(f), tp / max(len(t), 1)
