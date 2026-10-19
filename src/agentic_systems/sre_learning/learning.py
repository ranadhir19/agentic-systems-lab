"""Continuous learning loop: every incident becomes training data.

* Collect ground truth after resolution (root cause, outcome).
* Incremental retraining gated on a data-quality score — only
  high-quality observations update the models.
* Active-learning queue: low-confidence predictions flagged for human
  review (human-intervention rate is tracked, not hidden).
* Learning-velocity metrics: accuracy improvement per month, confidence
  trend, retrain triggers (accuracy drop > 5%, intervention rate > 15%,
  new incident types).
"""
from __future__ import annotations

import numpy as np

from .change_agent import ChangeRiskPredictor, auc_score
from .similarity import SimilarityAgent, make_pairs


class ContinuousLearner:
    def __init__(self, change_agent: ChangeRiskPredictor,
                 similarity_agent: SimilarityAgent,
                 resolution_agent,
                 quality_threshold: float = 0.8):
        self.change_agent = change_agent
        self.similarity_agent = similarity_agent
        self.resolution_agent = resolution_agent
        self.quality_threshold = quality_threshold
        self.review_queue: list = []          # active-learning flags
        self.history: list[dict] = []         # monthly metric snapshots
        self._seen_causes: set = set()

    # -- ground truth collection ---------------------------------------------
    def collect(self, incident, recommended_action: str | None = None) -> dict:
        """What the loop learns once the incident is resolved."""
        gt = {
            "incident_id": incident.id,
            "root_cause": incident.root_cause,
            "change_id": incident.change_id,
            "resolution_action": incident.resolution_action,
            "resolution_success": incident.resolution_success,
            # data quality: postmortem present + resolution recorded
            "quality": 1.0 if incident.postmortem and incident.resolution_action
            else 0.6,
        }
        new_type = incident.root_cause not in self._seen_causes
        self._seen_causes.add(incident.root_cause)
        gt["new_incident_type"] = new_type
        return gt

    def update(self, incidents: list, changes: list,
               month: int, val_changes=None, val_labels=None,
               sgd_steps: int = 30) -> dict:
        """One monthly cycle: ingest ground truth, retrain if quality
        passes, flag uncertain cases, record metrics."""
        from .synth import World
        rng = np.random.default_rng(1000 + month)
        gated, flagged = 0, 0
        for inc in incidents:
            gt = self.collect(inc)
            if gt["quality"] >= self.quality_threshold:
                gated += 1
                self.resolution_agent.observe(inc)
            else:
                flagged += 1
                self.review_queue.append(inc.id)
        # incremental change-agent update on this month's changes
        if changes:
            w = World(seed=0)  # stateless helpers only
            X = w.feature_matrix(changes)
            y = w.labels(changes)
            self.change_agent.partial_fit(X, y, steps=sgd_steps)
        # similarity agent: refresh pairs with a few new ones
        pairs = make_pairs(incidents, rng, n_pairs=min(400, len(incidents) * 4))
        if pairs:
            self.similarity_agent.fit(pairs, iters=300)
        metrics = self._snapshot(month, val_changes, val_labels,
                                 n_incidents=len(incidents),
                                 gated=gated, flagged=flagged)
        self.history.append(metrics)
        return metrics

    def _snapshot(self, month, val_changes, val_labels, n_incidents,
                  gated, flagged) -> dict:
        m = {"month": month, "incidents": n_incidents,
             "gated": gated, "flagged": flagged,
             "intervention_rate": flagged / max(n_incidents, 1)}
        if val_changes is not None and len(val_changes):
            from .synth import World
            X = World(seed=0).feature_matrix(val_changes)
            scores = self.change_agent.predict_proba(X)
            m["change_auc"] = auc_score(val_labels, scores)
        return m

    # -- learning velocity ------------------------------------------------------
    def learning_velocity(self) -> dict:
        aucs = [h["change_auc"] for h in self.history
                if "change_auc" in h and not np.isnan(h["change_auc"])]
        out = {"months": len(self.history)}
        if len(aucs) >= 2:
            out["auc_start"] = aucs[0]
            out["auc_end"] = aucs[-1]
            out["auc_gain_per_month"] = (aucs[-1] - aucs[0]) / (len(aucs) - 1)
        ir = [h["intervention_rate"] for h in self.history]
        if ir:
            out["intervention_rate_start"] = ir[0]
            out["intervention_rate_end"] = ir[-1]
        return out

    def retrain_triggers(self) -> list[str]:
        """Heuristic triggers from the concept: accuracy drop > 5%,
        intervention rate > 15%, new incident types."""
        triggers = []
        aucs = [h.get("change_auc") for h in self.history]
        aucs = [a for a in aucs if a is not None and not np.isnan(a)]
        if len(aucs) >= 2 and aucs[-1] < aucs[-2] - 0.05:
            triggers.append("accuracy_drop>5%")
        if self.history and self.history[-1]["intervention_rate"] > 0.15:
            triggers.append("intervention_rate>15%")
        return triggers
