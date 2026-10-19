"""Causality Agent: builds a causal knowledge graph from postmortem
causal statements, then predicts root-cause paths for new incidents.

Extraction is deterministic (the synthetic postmortems carry explicit
"Causal: X caused Y" statements — standing in for an LLM causal parser
in production). Edges carry confidence = frequency-weighted support.

Prediction scores each candidate root cause by the best directed path
from the cause to the observed symptoms: path score = product of edge
confidences, times a symptom-coverage term. The correlation-only
baseline scores causes by raw symptom co-occurrence, ignoring direction
and multi-hop chains — the experiment measures whether the graph's
structure adds value beyond co-occurrence.
"""
from __future__ import annotations

import re
from collections import defaultdict

import numpy as np

_CAUSAL_RE = re.compile(r"Causal:\s*(.+?)\s+caused\s+(.+?)\s+on\s+(\S+)\.", re.IGNORECASE)
_TRIGGER_RE = re.compile(r"Causal:\s*change\s+(\d+)\s+\((\w+)\s+on\s+(\S+)\)\s+triggered\s+(\S+)\.", re.IGNORECASE)


class CausalKnowledgeGraph:
    def __init__(self):
        # (src, dst) -> {"count": int, "weight": float}
        self.edges: dict[tuple[str, str], dict] = {}
        self.nodes: set[str] = set()
        # symptom -> cause co-occurrence counts (for the baseline)
        self.cooccur: dict[tuple[str, str], int] = defaultdict(int)
        self.cause_counts: dict[str, int] = defaultdict(int)

    # -- learning ---------------------------------------------------------
    def ingest_postmortem(self, text: str, reliability: float = 1.0):
        for m in _CAUSAL_RE.finditer(text):
            src, dst = m.group(1).strip(), m.group(2).strip()
            self._add_edge(src, dst, reliability)
            self.cooccur[(dst, src)] += 1
            self.cause_counts[src] += 1
        for m in _TRIGGER_RE.finditer(text):
            ch_id, ch_type, svc, cause = m.groups()
            self._add_edge(f"change:{ch_type}", cause, reliability)
            self.cause_counts[cause] += 1

    def _add_edge(self, src: str, dst: str, w: float):
        self.nodes.add(src)
        self.nodes.add(dst)
        e = self.edges.setdefault((src, dst), {"count": 0, "weight": 0.0})
        e["count"] += 1
        e["weight"] += w

    def edge_confidence(self, src: str, dst: str) -> float:
        e = self.edges.get((src, dst))
        if not e:
            return 0.0
        # saturating confidence in [0,1)
        return 1.0 - np.exp(-e["weight"] / 3.0)

    def fit(self, postmortems: list[str]) -> "CausalKnowledgeGraph":
        for pm in postmortems:
            if pm:
                self.ingest_postmortem(pm)
        return self

    # -- inference ---------------------------------------------------------
    def _best_path_score(self, cause: str, symptoms: list[str],
                         max_hops: int = 3) -> float:
        """Max over directed paths cause -> ... -> symptom of the
        product of edge confidences, summed over symptoms."""
        # adjacency
        adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for (s, d) in self.edges:
            c = self.edge_confidence(s, d)
            if c > 0:
                adj[s].append((d, c))
        total = 0.0
        for sym in symptoms:
            best = 0.0
            # DFS with depth cap
            stack = [(cause, 1.0, 0, {cause})]
            while stack:
                node, prod, depth, seen = stack.pop()
                if node == sym:
                    best = max(best, prod)
                    continue
                if depth >= max_hops:
                    continue
                for nxt, c in adj.get(node, []):
                    if nxt not in seen:
                        stack.append((nxt, prod * c, depth + 1, seen | {nxt}))
            total += best
        coverage = total / max(len(symptoms), 1)
        return coverage

    def predict(self, symptoms: list[str], top_k: int = 3,
                change_type: str | None = None) -> list[tuple[str, float]]:
        scored = []
        for c in self.cause_counts:
            s = self._best_path_score(c, symptoms)
            if change_type is not None:
                # change-type -> cause trigger edges disambiguate generic symptoms
                s += 0.5 * self.edge_confidence(f"change:{change_type}", c)
            scored.append((c, s))
        scored.sort(key=lambda t: -t[1])
        return scored[:top_k]

    # -- baseline ------------------------------------------------------------
    def predict_correlation_baseline(self, symptoms: list[str],
                                     top_k: int = 3) -> list[tuple[str, float]]:
        """P(cause | symptoms) from raw co-occurrence — no graph structure."""
        scored = []
        for cause in self.cause_counts:
            s = sum(self.cooccur.get((sym, cause), 0) for sym in symptoms)
            denom = sum(self.cause_counts[cause] for _ in [0]) or 1
            scored.append((cause, s / max(self.cause_counts[cause], 1)))
        scored.sort(key=lambda t: -t[1])
        return scored[:top_k]

    def top_k_accuracy(self, incidents, k: int = 3, baseline: bool = False,
                       use_change_type: bool = True,
                       change_lookup: dict | None = None) -> float:
        """change_lookup maps incident id -> change_type string (from the
        enrichment step); the graph model may use it, the baseline may not."""
        hits = 0
        for inc in incidents:
            if baseline:
                preds = [c for c, _ in
                         self.predict_correlation_baseline(inc.symptoms, top_k=k)]
            else:
                ct = (change_lookup or {}).get(inc.id) if use_change_type else None
                preds = [c for c, _ in self.predict(inc.symptoms, top_k=k,
                                                    change_type=ct)]
            if inc.root_cause in preds:
                hits += 1
        return hits / len(incidents) if incidents else 0.0
