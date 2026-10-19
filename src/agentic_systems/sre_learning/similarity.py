"""Similarity Agent: learns what "similar" means to the SRE team.

Approach: incident -> feature vector (symptom one-hots, metric-signature
stats, service tier, change features or zeros). For a pair, the input is
the absolute difference vector; a logistic model learns P(same root
cause | pair) — i.e. it learns a *weighted* L1 distance where the
weights say which dimensions matter. This is a lightweight,
interpretable analogue of Siamese contrastive learning.

Baseline: TF-IDF cosine over symptom + postmortem text.

Active learning: pairs with |p - 0.5| smallest are queued for human
labeling; the experiment measures accuracy gain per labeling budget vs
random labeling.
"""
from __future__ import annotations

import numpy as np

from .synth import CAUSES, Incident


def _symptom_vocab() -> list[str]:
    vocab = []
    for spec in CAUSES.values():
        for s in spec["symptoms"]:
            if s not in vocab:
                vocab.append(s)
    return vocab


SYMPTOMS = _symptom_vocab()
TIER = {"api-gateway": 0.9, "checkout": 1.0, "payments": 1.0, "ledger": 0.9,
        "inventory": 0.6, "search": 0.5, "reco": 0.4, "notify": 0.3}


def incident_vector(inc: Incident) -> np.ndarray:
    sym = np.array([1.0 if s in inc.symptoms else 0.0 for s in SYMPTOMS])
    sig = inc.metric_sig
    stats = np.array([sig.mean(), sig.max(), sig.std(),
                      float(np.argmax(sig)) / len(sig)])
    tier = np.array([TIER.get(inc.service, 0.5)])
    sev = np.array([inc.severity / 4.0])
    return np.concatenate([sym, stats, tier, sev])


class SimilarityAgent:
    def __init__(self, seed: int = 7):
        self.rng = np.random.default_rng(seed)
        self.w: np.ndarray | None = None
        self.b: float = 0.0
        self._vecs: dict[int, np.ndarray] = {}
        self._causes: dict[int, str] = {}

    # -- training ---------------------------------------------------------
    def _pair_xy(self, pairs: list[tuple[Incident, Incident, int]]):
        X, y = [], []
        for a, b, label in pairs:
            va = self._vec(a)
            vb = self._vec(b)
            X.append(np.abs(va - vb))
            y.append(label)
        return np.stack(X), np.array(y, dtype=float)

    def _vec(self, inc: Incident) -> np.ndarray:
        if inc.id not in self._vecs:
            self._vecs[inc.id] = incident_vector(inc)
            self._causes[inc.id] = inc.root_cause
        return self._vecs[inc.id]

    def fit(self, pairs: list[tuple[Incident, Incident, int]],
            iters: int = 1500, l2: float = 0.5) -> "SimilarityAgent":
        X, y = self._pair_xy(pairs)
        n, d = X.shape
        w = np.zeros(d)
        b = 0.0
        lr = 0.5
        for _ in range(iters):
            z = X @ w + b
            p = 1 / (1 + np.exp(-np.clip(z, -30, 30)))
            w -= lr * (X.T @ (p - y) / n + l2 * w / n)
            b -= lr * (p - y).mean()
            lr *= 0.999
        # distance should grow with difference: flip sign if needed
        self.w, self.b = -w, -b  # store as distance weights (positive => dissimilar)
        # keep raw for probability
        self._w_raw, self._b_raw = w, b
        return self

    def pair_proba(self, a: Incident, b: Incident) -> float:
        d = np.abs(self._vec(a) - self._vec(b))
        z = d @ self._w_raw + self._b_raw
        return float(1 / (1 + np.exp(-np.clip(z, -30, 30))))

    def distance(self, a: Incident, b: Incident) -> float:
        return float(np.abs(self._vec(a) - self._vec(b)) @ np.abs(self.w))

    # -- retrieval ---------------------------------------------------------
    def search(self, query: Incident, corpus: list[Incident],
               k: int = 5) -> list[tuple[Incident, float]]:
        scored = [(c, self.distance(query, c)) for c in corpus
                  if c.id != query.id]
        scored.sort(key=lambda t: t[1])
        return scored[:k]

    def precision_at_k(self, queries: list[Incident], corpus: list[Incident],
                       k: int = 5) -> float:
        hits = 0
        for q in queries:
            res = self.search(q, corpus, k=k)
            if res and sum(1 for c, _ in res if c.root_cause == q.root_cause):
                # at least one same-cause hit counts; use mean precision
                hits += sum(1 for c, _ in res if c.root_cause == q.root_cause) / k
        return hits / len(queries) if queries else 0.0

    # -- active learning -----------------------------------------------------
    def uncertain_pairs(self, pool: list[tuple[Incident, Incident]],
                        budget: int) -> list[tuple[Incident, Incident]]:
        scored = [(abs(self.pair_proba(a, b) - 0.5), (a, b)) for a, b in pool]
        scored.sort(key=lambda t: t[0])
        return [p for _, p in scored[:budget]]


# ---------------------------------------------------------------------------
# TF-IDF baseline over symptom + postmortem text
# ---------------------------------------------------------------------------

class TfidfBaseline:
    def __init__(self):
        self.vocab: list[str] = []
        self.idf: np.ndarray | None = None
        self._mat: dict[int, np.ndarray] = {}

    @staticmethod
    def _text(inc: Incident) -> str:
        return " ".join(inc.symptoms) + " " + inc.postmortem.lower()

    @staticmethod
    def _query_text(inc: Incident) -> str:
        # at incident onset there is no postmortem yet: symptoms only
        return " ".join(inc.symptoms)

    def _vectorize(self, text: str) -> np.ndarray:
        idx = {t: i for i, t in enumerate(self.vocab)}
        v = np.zeros(len(self.vocab))
        for t in text.split():
            if t in idx:
                v[idx[t]] += 1
        v = v * self.idf
        n = np.linalg.norm(v) + 1e-12
        return v / n

    def fit(self, incidents: list[Incident]) -> "TfidfBaseline":
        docs = [self._text(i).split() for i in incidents]
        vocab = sorted({t for d in docs for t in d})
        self.vocab = vocab
        idx = {t: i for i, t in enumerate(vocab)}
        df = np.zeros(len(vocab))
        for d in docs:
            for t in set(d):
                df[idx[t]] += 1
        self.idf = np.log((1 + len(docs)) / (1 + df)) + 1
        for inc, d in zip(incidents, docs):
            self._mat[inc.id] = self._vectorize(" ".join(d))
        self._causes = {i.id: i.root_cause for i in incidents}
        return self

    def search(self, query: Incident, corpus: list[Incident], k: int = 5):
        qv = self._vectorize(self._query_text(query))
        scored = [(c, float(qv @ self._mat[c.id])) for c in corpus
                  if c.id != query.id]
        scored.sort(key=lambda t: -t[1])
        return scored[:k]

    def precision_at_k(self, queries, corpus, k: int = 5) -> float:
        hits = 0
        for q in queries:
            res = self.search(q, corpus, k=k)
            hits += sum(1 for c, _ in res if c.root_cause == q.root_cause) / k
        return hits / len(queries) if queries else 0.0


def make_pairs(incidents: list[Incident], rng: np.random.Generator,
               n_pairs: int = 3000,
               hard_negatives: bool = False) -> list[tuple[Incident, Incident, int]]:
    """Balanced similar/dissimilar pairs with ground-truth labels.

    With hard_negatives=True, dissimilar pairs are mined to share at
    least one symptom (the genuinely ambiguous cases) instead of being
    trivially different.
    """
    by_cause: dict[str, list[Incident]] = {}
    for inc in incidents:
        by_cause.setdefault(inc.root_cause, []).append(inc)
    causes = list(by_cause)
    pairs = []
    for _ in range(n_pairs):
        if rng.random() < 0.5:
            c = causes[rng.integers(len(causes))]
            if len(by_cause[c]) < 2:
                continue
            a, b = rng.choice(by_cause[c], size=2, replace=False)
            pairs.append((a, b, 1))
        else:
            a, b = None, None
            for _try in range(20):
                c1, c2 = rng.choice(causes, size=2, replace=False)
                a = by_cause[c1][rng.integers(len(by_cause[c1]))]
                b = by_cause[c2][rng.integers(len(by_cause[c2]))]
                if not hard_negatives or set(a.symptoms) & set(b.symptoms):
                    break
            pairs.append((a, b, 0))
    return pairs
