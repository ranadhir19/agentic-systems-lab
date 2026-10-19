"""Semantic extraction layers L0 (structural) through L4 (temporal).

Each extractor takes raw synthetic inputs and emits a persistent semantic
artifact — a compact, versionable structure from which the raw data can be
discarded. Artifacts are plain dicts/lists of JSON-safe values.
"""
from __future__ import annotations

import numpy as np

from .common import kmeans, dist_profile, adjusted_rand_index


# ---------------------------------------------------------------------------
# L0 — structural semantics: schema, entities, relations
# ---------------------------------------------------------------------------
def extract_l0(records):
    """Infer entities (keys ending in _id), attribute types, and relations.

    Relations are mined as: entity A co-occurs with entity B in records,
    and B's cardinality given A suggests a hierarchy (e.g. many txns share
    one server -> txn --belongs-to--> server).
    """
    if not records:
        return {"entities": {}, "relations": []}
    keys = list(records[0].keys())
    entities, attrs = {}, {}
    for k in keys:
        vals = [r[k] for r in records]
        if k.endswith("_id"):
            entities[k[:-3]] = {"key": k, "cardinality": len(set(vals))}
        else:
            kind = "numeric" if all(isinstance(v, (int, float)) for v in vals) \
                else "categorical"
            attrs[k] = {"type": kind,
                        "distinct": len(set(vals)) if kind == "categorical"
                        else None}
    relations = []
    ekeys = list(entities.keys())
    for i, a in enumerate(ekeys):
        for b in ekeys[i + 1:]:
            ka, kb = entities[a]["key"], entities[b]["key"]
            # does many-a share one-b? (a belongs to b)
            groups = {}
            for r in records:
                groups.setdefault(r[kb], set()).add(r[ka])
            avg_fanout = np.mean([len(v) for v in groups.values()])
            if avg_fanout > 1.5:
                relations.append({"src": a, "dst": b, "type": "belongs_to",
                                  "fanout": round(float(avg_fanout), 2)})
            # reverse direction
            groups = {}
            for r in records:
                groups.setdefault(r[ka], set()).add(r[kb])
            avg_fanout = np.mean([len(v) for v in groups.values()])
            if avg_fanout > 1.5:
                relations.append({"src": b, "dst": a, "type": "belongs_to",
                                  "fanout": round(float(avg_fanout), 2)})
    return {"entities": entities, "attributes": attrs,
            "relations": relations}


# ---------------------------------------------------------------------------
# L1 — statistical semantics: distribution profiles + correlations
# ---------------------------------------------------------------------------
NUMERIC_HINTS = ("amount", "latency", "load", "queue", "cpu", "memory")


def extract_l1(records, numeric_keys=None):
    """Per-field distribution profiles and the correlation matrix."""
    if numeric_keys is None:
        numeric_keys = [k for k in records[0]
                        if any(h in k for h in NUMERIC_HINTS)
                        and isinstance(records[0][k], (int, float))]
    profiles = {k: dist_profile([r[k] for r in records]) for k in numeric_keys}
    X = np.array([[r[k] for k in numeric_keys] for r in records])
    C = np.corrcoef(X, rowvar=False)
    corrs = {}
    for i in range(len(numeric_keys)):
        for j in range(i + 1, len(numeric_keys)):
            corrs[f"{numeric_keys[i]}|{numeric_keys[j]}"] = \
                round(float(C[i, j]), 4)
    return {"profiles": profiles, "correlations": corrs,
            "fields": numeric_keys}


# ---------------------------------------------------------------------------
# L2 — behavioral semantics: archetypes + Markov transition models
# ---------------------------------------------------------------------------
def behavior_features(records):
    """Per-user behavior feature vectors from transaction records."""
    users = {}
    for r in records:
        u = users.setdefault(r["user_id"],
                             {"amounts": [], "errors": 0, "n": 0,
                              "hours": []})
        u["amounts"].append(r["amount"])
        u["errors"] += r["error"]
        u["n"] += 1
        u["hours"].append(r["ts_hour"] % 24)
    ids, feats = [], []
    for uid, u in sorted(users.items()):
        amt = np.array(u["amounts"])
        ids.append(uid)
        feats.append([np.log1p(amt).mean(), np.log1p(amt).std(),
                      u["errors"] / max(u["n"], 1), u["n"],
                      np.mean(np.sin(2 * np.pi * np.array(u["hours"]) / 24))])
    F = np.array(feats)
    F = (F - F.mean(0)) / (F.std(0) + 1e-9)
    return ids, F


def extract_l2(records, sequences, k=5, seed=0):
    """Archetype clusters (k-means on behavior features) + one Markov
    transition matrix per archetype over the action vocabulary."""
    uids, F = behavior_features(records)
    labels, centroids = kmeans(F, k, seed=seed)
    arch_of = dict(zip(uids, labels))
    # map sequence users u0000.. onto clustered users by index modulo
    actions = sorted({a for s in sequences for a in s})
    aidx = {a: i for i, a in enumerate(actions)}
    trans = np.zeros((k, len(actions), len(actions)))
    counts = np.zeros(k)
    for u, seq in enumerate(sequences):
        uid = f"u{u % 1000:04d}"
        a = arch_of.get(uid, u % k)
        counts[a] += 1
        for x, y in zip(seq, seq[1:]):
            trans[a, aidx[x], aidx[y]] += 1
    for a in range(k):
        row = trans[a].sum(1, keepdims=True)
        trans[a] = np.divide(trans[a], row, out=np.zeros_like(trans[a]),
                             where=row > 0)
    return {
        "k": k,
        "archetype_of_user": {u: int(l) for u, l in arch_of.items()},
        "centroids": centroids.tolist(),
        "actions": actions,
        "transition_matrices": trans.tolist(),
        "members_per_archetype": [int((labels == j).sum())
                                  for j in range(k)],
    }


# ---------------------------------------------------------------------------
# L3 — relational semantics: typed edges with strength + confidence
# ---------------------------------------------------------------------------
def extract_l3(records, min_support=30):
    """Mine (server -> service) impact edges: strength = lift of error/
    high-latency co-occurrence, confidence from support counts."""
    lat = np.array([r["latency_ms"] for r in records])
    thresh = float(np.percentile(lat, 90))
    base_rate = float(np.mean(lat > thresh))
    edges = []
    pairs = {}
    for r in records:
        key = (r["server_id"], r["service"])
        d = pairs.setdefault(key, {"n": 0, "bad": 0})
        d["n"] += 1
        d["bad"] += (r["latency_ms"] > thresh)
    for (srv, svc), d in sorted(pairs.items()):
        if d["n"] < min_support:
            continue
        rate = d["bad"] / d["n"]
        lift = rate / max(base_rate, 1e-9)
        # Wilson-ish confidence proxy: lift * sqrt(support)
        conf = float(min(1.0, lift * np.sqrt(d["n"]) / 10.0))
        if lift > 1.5:
            edges.append({"src": srv, "dst": svc, "type": "impacts",
                          "strength": round(float(lift), 3),
                          "confidence": round(conf, 3),
                          "support": d["n"]})
    return {"edges": edges, "p90_latency_ms": thresh,
            "base_bad_rate": round(base_rate, 4)}


# ---------------------------------------------------------------------------
# L4 — temporal semantics: trend, seasonality, cascades, decay
# ---------------------------------------------------------------------------
def _spikes(x, thresh=3.0):
    z = (np.asarray(x, float) - np.mean(x)) / (np.std(x) + 1e-9)
    return np.where(np.abs(z) > thresh)[0]


def extract_l4(series):
    """Temporal signature per series: linear trend, dominant FFT period,
    and spike-triggered cascades (source spikes -> target response lag)."""
    names = list(series.keys())
    sig = {}
    for name in names:
        x = np.asarray(series[name], dtype=float)
        n = len(x)
        t = np.arange(n)
        slope = float(np.polyfit(t, x, 1)[0])
        xc = x - x.mean()
        spec = np.abs(np.fft.rfft(xc)) ** 2
        freqs = np.fft.rfftfreq(n, d=1.0)
        spec[0] = 0.0
        dom = float(1.0 / freqs[spec.argmax()]) if spec.max() > 0 else 0.0
        sig[name] = {"trend_per_h": round(slope, 6),
                     "dominant_period_h": round(dom, 1),
                     "mean": round(float(x.mean()), 4),
                     "std": round(float(x.std()), 4)}
    cascades = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            for src, dst in ((a, b), (b, a)):
                sp = _spikes(series[src])
                if len(sp) < 2:
                    continue
                xd = np.asarray(series[dst], float)
                zd = (xd - xd.mean()) / (xd.std() + 1e-9)
                best_lag, best_resp = 0, 0.0
                for lag in range(0, 13):
                    idx = sp + lag
                    idx = idx[idx < len(zd)]
                    resp = float(zd[idx].mean()) if len(idx) else 0.0
                    if abs(resp) > abs(best_resp):
                        best_resp, best_lag = resp, lag
                if abs(best_resp) > 1.0 and best_lag > 0:
                    cascades.append({"src": src, "dst": dst,
                                     "lag_h": best_lag,
                                     "response": round(best_resp, 3)})
    # deduplicate mirrored pairs, keep stronger
    seen, uniq = set(), []
    for c in sorted(cascades, key=lambda c: -abs(c["response"])):
        key = (c["src"], c["dst"])
        if key not in seen:
            seen.add(key)
            uniq.append(c)
    return {"series": sig, "cascades": uniq}
