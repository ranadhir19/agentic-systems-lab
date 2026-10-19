"""Processed stage: classical-AI pattern detection over raw telemetry.

For each metric series this computes:
- robust anomaly score (trailing median/MAD z-score),
- local trend (least-squares slope),
- time-to-threshold forecast (AR(1) extrapolation),
- event clusters (numpy k-means),
- lagged cross-correlation between series.

`detect_intervals` turns per-minute flags into anomaly intervals with
onset times, which feed the analytic stage and the cross-layer correlator.
"""
from __future__ import annotations

import numpy as np


def robust_z(series: np.ndarray, window: int = 60) -> np.ndarray:
    """Trailing median/MAD z-score (0.6745-scaled). Robust to incident crowding."""
    series = np.asarray(series, dtype=float)
    n = len(series)
    z = np.zeros(n)
    for t in range(n):
        lo = max(0, t - window)
        w = series[lo:t] if t - lo > 1 else series[max(0, t - 1):t + 1]
        med = np.median(w)
        mad = np.median(np.abs(w - med)) + 1e-9
        z[t] = 0.6745 * (series[t] - med) / mad
    return z


def trend_slope(series: np.ndarray, window: int = 30) -> float:
    """Least-squares slope over the trailing window."""
    w = np.asarray(series, dtype=float)[-window:]
    x = np.arange(len(w))
    x = x - x.mean()
    denom = float(np.dot(x, x)) + 1e-12
    return float(np.dot(x, w - w.mean()) / denom)


def forecast_breach(series: np.ndarray, threshold: float, window: int = 20,
                    horizon: int = 180) -> float | None:
    """Linear-trend extrapolation: predicted minutes until `threshold`.

    Fits the least-squares slope over the trailing `window` (short, so it
    reflects the current regime, not ancient history) and extrapolates.
    Returns None when the trend points away from the threshold or the
    crossing lies beyond `horizon`.
    """
    w = np.asarray(series, dtype=float)[-window:]
    if len(w) < 10:
        return None
    slope = trend_slope(w, window=len(w))
    last = float(w[-1])
    rising = threshold > last
    if rising and slope <= 1e-9:
        return None
    if not rising and slope >= -1e-9:
        return None
    h = (threshold - last) / slope
    return float(h) if 0.0 < h <= horizon else None


def kmeans_1d(x: np.ndarray, k: int, seed: int = 0,
              iters: int = 50) -> np.ndarray:
    """Numpy k-means for 1-D event grouping. Returns integer labels."""
    x = np.asarray(x, dtype=float).ravel()
    rng = np.random.default_rng(seed)
    if len(x) == 0:
        return np.zeros(0, dtype=int)
    k = max(1, min(k, len(x)))
    centers = np.sort(rng.choice(x, size=k, replace=False)).astype(float)
    labels = np.zeros(len(x), dtype=int)
    for _ in range(iters):
        d = np.abs(x[:, None] - centers[None, :])
        new_labels = d.argmin(axis=1)
        new_centers = np.array([x[new_labels == j].mean()
                                if np.any(new_labels == j) else centers[j]
                                for j in range(k)])
        if np.array_equal(new_labels, labels):
            labels = new_labels
            break
        labels, centers = new_labels, new_centers
    return labels


def lagged_corr(a: np.ndarray, b: np.ndarray,
                max_lag: int = 30) -> tuple[float, int]:
    """Max |Pearson r| between a[t] and b[t-lag]; returns (r, best_lag).

    Positive lag means b follows a.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    best_r, best_lag = 0.0, 0
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            x, y = a[:n - lag], b[lag:]
        else:
            x, y = a[-lag:], b[:n + lag]
        if len(x) < 10:
            continue
        sx, sy = x.std(), y.std()
        if sx < 1e-12 or sy < 1e-12:
            continue
        r = float(np.corrcoef(x, y)[0, 1])
        if abs(r) > abs(best_r):
            best_r, best_lag = r, lag
    return best_r, best_lag


def detect_intervals(z: np.ndarray, thresh: float = 3.0,
                     min_len: int = 5, warmup: int = 30
                     ) -> list[tuple[int, int, float]]:
    """Turn a z-score series into (start, end, peak|z|) anomaly intervals.

    Minutes before `warmup` are ignored (trailing windows are too short
    there and produce spurious flags).
    """
    flag = np.abs(z) >= thresh
    flag[:warmup] = False
    intervals = []
    t = warmup
    n = len(flag)
    while t < n:
        if flag[t]:
            s = t
            while t < n and flag[t]:
                t += 1
            if t - s >= min_len:
                intervals.append((s, t, float(np.abs(z[s:t]).max())))
        else:
            t += 1
    return intervals


def naive_threshold_intervals(series: np.ndarray, threshold: float,
                              above: bool = True,
                              min_len: int = 3) -> list[tuple[int, int]]:
    """Naive fixed-threshold baseline detector (for experiment b)."""
    flag = series >= threshold if above else series <= threshold
    intervals = []
    t, n = 0, len(flag)
    while t < n:
        if flag[t]:
            s = t
            while t < n and flag[t]:
                t += 1
            if t - s >= min_len:
                intervals.append((s, t))
        else:
            t += 1
    return intervals


def interval_mask(intervals: list, n: int) -> np.ndarray:
    m = np.zeros(n, dtype=bool)
    for s, e, *_ in intervals:
        m[s:min(e, n)] = True
    return m
