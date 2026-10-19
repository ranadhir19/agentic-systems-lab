"""Data pipeline: extract -> enrich -> per-agent training datasets.

The enrichment step is the "magic": link each incident to candidate
changes in the 24h window before it via temporal + service + topology
correlation scoring, then select the most likely change. Ground truth is
kept so experiments can measure linking accuracy honestly.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .synth import Change, Incident, World, _dependents


@dataclass
class ChangeCandidate:
    change: Change
    score: float
    evidence: dict = field(default_factory=dict)


@dataclass
class EnrichedIncident:
    incident: Incident
    candidates: list[ChangeCandidate] = field(default_factory=list)
    root_change: Change | None = None
    root_confidence: float = 0.0


def _temporal_score(dt_h: float) -> float:
    """Exponential decay: recent changes score higher. dt in hours."""
    if dt_h < 0 or dt_h > 24:
        return 0.0
    return float(np.exp(-dt_h / 8.0))


def _service_score(inc_service: str, ch_service: str) -> float:
    if inc_service == ch_service:
        return 1.0
    if ch_service in _dependents(inc_service):
        return 0.6  # change upstream of the incident service
    return 0.15


class DataPipeline:
    """Extract -> transform -> enrich -> train pipeline over a World."""

    def __init__(self, world: World, change_agent=None):
        self.world = world
        self.change_agent = change_agent  # optional risk prior for scoring

    # -- extraction ------------------------------------------------------
    def extract(self, t_end: float | None = None):
        chs = [c for c in self.world.changes
               if t_end is None or c.t <= t_end]
        incs = [i for i in self.world.incidents
                if t_end is None or i.t_start <= t_end]
        return chs, incs

    # -- enrichment ------------------------------------------------------
    def enrich(self, incidents: list[Incident],
               changes: list[Change]) -> list[EnrichedIncident]:
        by_id = {c.id: c for c in changes}
        enriched = []
        for inc in incidents:
            cands = []
            for ch in changes:
                if ch.t >= inc.t_start:
                    continue
                dt = inc.t_start - ch.t
                ts = _temporal_score(dt)
                if ts <= 0:
                    continue
                ss = _service_score(inc.service, ch.service)
                prior = 0.5
                if self.change_agent is not None:
                    prior = float(self.change_agent.predict_proba(
                        ch.features().reshape(1, -1))[0])
                score = ts * ss * (0.3 + 0.7 * prior)
                cands.append(ChangeCandidate(
                    change=ch, score=score,
                    evidence={"dt_h": round(dt, 2), "temporal": round(ts, 3),
                              "service": round(ss, 3),
                              "risk_prior": round(prior, 3)}))
            cands.sort(key=lambda c: -c.score)
            root, conf = None, 0.0
            if cands and cands[0].score > 0.05:
                root, conf = cands[0].change, cands[0].score
            enriched.append(EnrichedIncident(inc, cands, root, conf))
        return enriched

    # -- per-agent datasets ----------------------------------------------
    def build_training_datasets(self, enriched: list[EnrichedIncident],
                                changes: list[Change]) -> dict:
        """Split the world into the four agents' training views."""
        return {
            "change_agent": {
                "X": self.world.feature_matrix(changes),
                "y": self.world.labels(changes),
                "changes": changes,
            },
            "causality_agent": {
                "postmortems": [e.incident.postmortem for e in enriched
                                if e.incident.postmortem],
                "incidents": [e.incident for e in enriched],
            },
            "similarity_agent": {
                "incidents": [e.incident for e in enriched],
            },
            "resolution_agent": {
                "incidents": [e.incident for e in enriched],
            },
        }

    # -- evaluation helper -------------------------------------------------
    def linking_accuracy(self, enriched: list[EnrichedIncident]) -> dict:
        """Fraction of change-caused incidents where enrichment picked the
        true causal change (top-1 and top-3). Organic incidents are excluded
        from the denominator (there is no true change to find)."""
        linked, correct, correct3, total = 0, 0, 0, 0
        for e in enriched:
            if e.incident.change_id < 0:
                continue
            total += 1
            if e.root_change is not None:
                linked += 1
                if e.root_change.id == e.incident.change_id:
                    correct += 1
            top3 = [c.change.id for c in e.candidates[:3]]
            if e.incident.change_id in top3:
                correct3 += 1
        return {"total": total, "linked": linked, "correct": correct,
                "accuracy": correct / total if total else 0.0,
                "top3_accuracy": correct3 / total if total else 0.0,
                "link_rate": linked / total if total else 0.0}
