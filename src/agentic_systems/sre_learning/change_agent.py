"""Change Intelligence Agent: predicts P(incident | change features).

Model: L2-regularized logistic regression implemented in numpy (no
sklearn available in this environment). Supports batch fit and online
partial_fit (SGD) for the continuous-learning loop.

Explanations are honest linear contributions: for a logistic model,
contribution_i = w_i * (x_i - mean_i) is the exact per-feature shift in
log-odds versus the average change. Reported as shares of total absolute
contribution — a linear analogue of SHAP values, labeled as such.
"""
from __future__ import annotations

import numpy as np

FEATURE_NAMES = [
    "is_config", "is_infra", "is_db_migration", "service_criticality",
    "blast_radius", "night_deploy", "author_inexperience",
    "change_complexity", "low_test_coverage",
]


class ChangeRiskPredictor:
    def __init__(self, l2: float = 1.0, lr: float = 0.5, seed: int = 7):
        self.l2 = l2
        self.lr = lr
        self.rng = np.random.default_rng(seed)
        self.w: np.ndarray | None = None
        self.b: float = 0.0
        self.feature_means: np.ndarray | None = None
        self.n_seen: int = 0

    # -- training ---------------------------------------------------------
    def fit(self, X: np.ndarray, y: np.ndarray, iters: int = 2000) -> "ChangeRiskPredictor":
        n, d = X.shape
        self.feature_means = X.mean(axis=0)
        Xs = X - self.feature_means
        w = np.zeros(d)
        b = float(np.log(max(y.mean(), 1e-6) / max(1 - y.mean(), 1e-6)))
        lr = self.lr
        for it in range(iters):
            z = Xs @ w + b
            p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
            grad_w = Xs.T @ (p - y) / n + self.l2 * w / n
            grad_b = (p - y).mean()
            w -= lr * grad_w
            b -= lr * grad_b
            lr *= 0.9995
        self.w, self.b = w, b
        self.n_seen = n
        return self

    def partial_fit(self, X: np.ndarray, y: np.ndarray, steps: int = 50) -> "ChangeRiskPredictor":
        """Online SGD update for the continuous-learning loop."""
        if self.w is None:
            return self.fit(X, y, iters=steps * 10)
        if self.feature_means is None:
            self.feature_means = X.mean(axis=0)
        Xs = X - self.feature_means
        lr = self.lr * 0.1
        for _ in range(steps):
            idx = self.rng.integers(len(X))
            xi, yi = Xs[idx], y[idx]
            p = 1 / (1 + np.exp(-np.clip(xi @ self.w + self.b, -30, 30)))
            err = p - yi
            self.w -= lr * (err * xi + self.l2 * self.w / max(self.n_seen, 1))
            self.b -= lr * err
        self.n_seen += len(X)
        return self

    # -- inference ---------------------------------------------------------
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        Xs = X - self.feature_means
        z = Xs @ self.w + self.b
        return 1 / (1 + np.exp(-np.clip(z, -30, 30)))

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return (self.predict_proba(X) >= threshold).astype(int)

    # -- explanation ---------------------------------------------------------
    def explain(self, x: np.ndarray, top_k: int = 3) -> dict:
        """Linear log-odds contributions vs the average change."""
        contrib = self.w * (x - self.feature_means)
        total = float(np.abs(contrib).sum()) + 1e-12
        order = np.argsort(-np.abs(contrib))[:top_k]
        parts = [(FEATURE_NAMES[i], float(contrib[i]),
                  float(abs(contrib[i]) / total)) for i in order]
        p = float(self.predict_proba(x.reshape(1, -1))[0])
        return {"risk": p, "contributions": parts,
                "method": "linear log-odds contribution vs feature mean "
                          "(exact for logistic models; a linear analogue "
                          "of SHAP values)"}

    def risk_sentence(self, x: np.ndarray) -> str:
        e = self.explain(x)
        top = ", ".join(f"{n} ({s:.0%})" for n, _, s in e["contributions"])
        level = "High" if e["risk"] > 0.66 else "Medium" if e["risk"] > 0.33 else "Low"
        return (f"{level} risk ({e['risk']:.2f}) — primarily due to {top}")


# ---------------------------------------------------------------------------
# Metrics (numpy)
# ---------------------------------------------------------------------------

def auc_score(y_true: np.ndarray, y_score: np.ndarray) -> float:
    """Mann-Whitney U statistic = P(score(pos) > score(neg))."""
    y_true = np.asarray(y_true)
    pos = y_score[y_true == 1]
    neg = y_score[y_true == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    wins = (pos[:, None] > neg[None, :]).sum()
    ties = (pos[:, None] == neg[None, :]).sum()
    return float((wins + 0.5 * ties) / (len(pos) * len(neg)))


def precision_recall(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    tp = int(((y_pred == 1) & (y_true == 1)).sum())
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    fn = int(((y_pred == 0) & (y_true == 1)).sum())
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": prec, "recall": rec,
            "f1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0}


def calibration_bins(y_true: np.ndarray, y_score: np.ndarray,
                     n_bins: int = 5) -> list[tuple[float, float, int]]:
    """(mean predicted, empirical rate, count) per bin."""
    out = []
    edges = np.linspace(0, 1, n_bins + 1)
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (y_score > lo) & (y_score <= hi) if lo > 0 else (y_score <= hi)
        if m.sum():
            out.append((float(y_score[m].mean()), float(y_true[m].mean()),
                        int(m.sum())))
    return out
