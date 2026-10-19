"""Baseline memory systems for comparison.

- IndependentMemory: no sharing; each agent keeps its own observations.
- NaiveSharedMemory: shared store, last-write-wins (naive vector-DB-like).
- ProvenanceMemory: versioned store with provenance; query returns the
  majority value within a recency window (a reasonable weak heuristic).

All implement the same admit/query interface as MemoryFabric.
"""
from __future__ import annotations

from collections import Counter


class IndependentMemory:
    name = "independent"

    def __init__(self):
        self._stores: dict[str, dict] = {}
        self.admissions = 0

    def admit(self, agent_id, model_family, subject, predicate, value,
              confidence, evidence, ts, access="internal"):
        self.admissions += 1
        self._stores.setdefault(agent_id, {})[(subject, predicate)] = value
        return ("admitted", None)

    def query(self, agent_id, subject, predicate, at):
        return self._stores.get(agent_id, {}).get((subject, predicate))


class NaiveSharedMemory:
    """Last-write-wins shared store."""
    name = "vector-db (last-write-wins)"

    def __init__(self):
        self._store: dict = {}
        self.admissions = 0

    def admit(self, agent_id, model_family, subject, predicate, value,
              confidence, evidence, ts, access="internal"):
        self.admissions += 1
        self._store[(subject, predicate)] = value
        return ("admitted", None)

    def query(self, agent_id, subject, predicate, at):
        return self._store.get((subject, predicate))


class ProvenanceMemory:
    """Versioned store; query = majority value in a recency window."""
    name = "provenance (majority vote)"

    def __init__(self, window: int = 10):
        self.window = window
        self._versions: dict[tuple[str, str], list] = {}
        self.admissions = 0

    def admit(self, agent_id, model_family, subject, predicate, value,
              confidence, evidence, ts, access="internal"):
        self.admissions += 1
        self._versions.setdefault((subject, predicate), []).append(
            (value, ts, agent_id))
        return ("admitted", None)

    def query(self, agent_id, subject, predicate, at):
        versions = self._versions.get((subject, predicate), [])
        recent = [v for (v, t, _) in versions if 0 <= at - t <= self.window]
        if not recent:
            return None
        counts = Counter(recent)
        top = counts.most_common()
        best = max(top, key=lambda kv: kv[1])[1]
        tied = [v for v, c in top if c == best]
        if len(tied) == 1:
            return tied[0]
        # tie -> newest among tied
        for v, t, _ in reversed(versions):
            if v in tied and 0 <= at - t <= self.window:
                return v
        return tied[0]
