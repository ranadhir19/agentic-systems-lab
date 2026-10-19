"""Client-service lens: resolution timelines, CSAT drivers, escalation risk."""
from __future__ import annotations

import numpy as np
import pandas as pd


def resolution_timelines(unified):
    """Resolution time and escalation rate per service / severity."""
    s = unified["snow"]
    rows = []
    for (svc, sev), g in s.groupby(["service", "severity"]):
        rows.append({"service": svc, "severity": sev,
                     "n": len(g),
                     "resolve_p50_h": round(g.resolve_h.median(), 1),
                     "escalation_rate": round(g.escalated.mean(), 3),
                     "csat_mean": round(g.csat.mean(), 2)})
    return pd.DataFrame(rows)


def csat_drivers(unified):
    """What moves CSAT? Correlations with resolution time, escalation, team."""
    s = unified["snow"].dropna(subset=["csat"]).copy()
    s["escalated_i"] = s.escalated.astype(int)
    s["log_resolve"] = np.log1p(s.resolve_h)
    out = {
        "corr_csat_logresolve": round(s.csat.corr(s.log_resolve), 3),
        "corr_csat_escalated": round(s.csat.corr(s.escalated_i), 3),
        "csat_escalated_mean": round(s[s.escalated].csat.mean(), 2),
        "csat_clean_mean": round(s[~s.escalated].csat.mean(), 2),
    }
    by_team = s.groupby("team").agg(csat=("csat", "mean"),
                                     esc_rate=("escalated", "mean"),
                                     n=("csat", "size")).round(2)
    out["by_team"] = by_team
    return out


class EscalationPredictor:
    """Tiny numpy logistic model: P(escalation | severity, repeat, service).

    Features: severity (1-4, inverted so higher = worse), whether the
    service had another incident in the previous 7 days (repeat offender),
    and the service's historical escalation rate (aggregate target
    encoding computed on the training set only).
    """

    def __init__(self, lr=1.0, epochs=2000, seed=0):
        self.lr, self.epochs = lr, epochs
        self.rng = np.random.default_rng(seed)
        self.w = None
        self.svc_rate = {}
        self.global_rate = 0.0
        self.feat_mu = None
        self.feat_sd = None

    def _features(self, df):
        sev = (5 - df.severity.values).astype(float) / 4.0
        opened = df.opened.values.astype("datetime64[h]").astype(float)
        repeat = np.zeros(len(df))
        svc = df.service.values
        for i in range(len(df)):
            mask = (svc == svc[i]) & (opened < opened[i]) & \
                   (opened >= opened[i] - 7 * 24)
            repeat[i] = 1.0 if mask.sum() > 1 else 0.0
        svc_r = np.array([self.svc_rate.get(s, self.global_rate)
                          for s in svc])
        X = np.column_stack([np.ones(len(df)), sev, repeat, svc_r])
        return X

    def fit(self, df):
        self.svc_rate = df.groupby("service").escalated.mean().to_dict()
        self.global_rate = float(df.escalated.mean())
        X = self._features(df)
        # Standardize non-intercept features (fit on train only).
        self.feat_mu = X[:, 1:].mean(axis=0)
        self.feat_sd = X[:, 1:].std(axis=0) + 1e-9
        Z = np.column_stack([X[:, [0]], (X[:, 1:] - self.feat_mu) / self.feat_sd])
        y = df.escalated.values.astype(float)
        self.w = self.rng.normal(0, 0.1, Z.shape[1])
        for _ in range(self.epochs):
            p = 1 / (1 + np.exp(-Z @ self.w))
            grad = Z.T @ (p - y) / len(y)
            self.w -= self.lr * grad
        return self

    def _standardize(self, X):
        return np.column_stack([X[:, [0]],
                                (X[:, 1:] - self.feat_mu) / self.feat_sd])

    def predict_proba(self, df):
        Z = self._standardize(self._features(df))
        return 1 / (1 + np.exp(-Z @ self.w))

    def best_threshold(self, df):
        """Threshold maximizing F1 on the given frame (tune on train)."""
        p = self.predict_proba(df)
        y = df.escalated.values.astype(bool)
        best_t, best_f1 = 0.5, -1.0
        for t in np.arange(0.05, 0.6, 0.01):
            pred = p >= t
            tp = int((pred & y).sum())
            fp = int((pred & ~y).sum())
            fn = int(((~pred) & y).sum())
            prec = tp / (tp + fp) if tp + fp else 0.0
            rec = tp / (tp + fn) if tp + fn else 0.0
            f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
            if f1 > best_f1:
                best_t, best_f1 = t, f1
        return round(float(best_t), 2), round(float(best_f1), 3)

    def scores(self, df, threshold=0.5):
        """Precision/recall/F1 at ``threshold`` on the given frame."""
        p = self.predict_proba(df)
        y = df.escalated.values.astype(bool)
        pred = p >= threshold
        tp = int((pred & y).sum())
        fp = int((pred & ~y).sum())
        fn = int(((~pred) & y).sum())
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        return {"precision": round(prec, 3), "recall": round(rec, 3),
                "f1": round(f1, 3), "n": len(df)}
