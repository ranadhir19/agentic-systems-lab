"""Agent coordination workflow (LangGraph-style state machine, implemented
directly — no langgraph dependency).

Flow:
    change_analysis
        -> high confidence (>0.7) -> causality_analysis
        -> low confidence          -> similarity_search
    causality_analysis -> similarity_search   (corroborate)
    similarity_search  -> resolution_recommend
    resolution_recommend -> learning_update -> END

Each node appends a trace entry; the final state carries the recommended
action, confidence scores, and which path was taken.
"""
from __future__ import annotations

import numpy as np

from .synth import Incident


class SREWorkflow:
    def __init__(self, change_agent, causal_graph, similarity_agent,
                 resolution_agent, pipeline, confidence_threshold: float = 0.7):
        self.change_agent = change_agent
        self.causal_graph = causal_graph
        self.similarity_agent = similarity_agent
        self.resolution_agent = resolution_agent
        self.pipeline = pipeline
        self.threshold = confidence_threshold

    def run(self, incident: Incident, changes=None, corpus=None) -> dict:
        state = {"incident": incident, "trace": [], "confidences": {}}
        state = self._change_analysis(state, changes)
        if state["confidences"]["change"] > self.threshold:
            state["trace"].append("branch:high_confidence_change->causality")
            state = self._causality_analysis(state)
        else:
            state["trace"].append("branch:low_confidence_change->similarity")
        state = self._similarity_search(state, corpus)
        state = self._resolution_recommend(state)
        state = self._learning_update(state)
        state["trace"].append("END")
        return state

    # -- nodes ---------------------------------------------------------------
    def _change_analysis(self, state: dict, changes) -> dict:
        inc = state["incident"]
        enriched = self.pipeline.enrich([inc], changes or [])[0]
        conf = enriched.root_confidence
        risk = 0.0
        if enriched.root_change is not None and self.change_agent is not None:
            risk = float(self.change_agent.predict_proba(
                enriched.root_change.features().reshape(1, -1))[0])
        state["change_context"] = {
            "root_change": enriched.root_change.id if enriched.root_change else None,
            "risk": risk,
            "candidates": [(c.change.id, round(c.score, 3))
                           for c in enriched.candidates[:3]],
        }
        state["confidences"]["change"] = conf
        state["trace"].append(
            f"change_analysis: root_change={state['change_context']['root_change']} "
            f"risk={risk:.2f} conf={conf:.2f}")
        return state

    def _causality_analysis(self, state: dict) -> dict:
        inc = state["incident"]
        hyps = self.causal_graph.predict(inc.symptoms, top_k=3)
        state["causal_hypotheses"] = [(c, round(s, 3)) for c, s in hyps]
        state["confidences"]["causality"] = hyps[0][1] if hyps else 0.0
        state["trace"].append(
            f"causality_analysis: hypotheses={state['causal_hypotheses']}")
        return state

    def _similarity_search(self, state: dict, corpus) -> dict:
        inc = state["incident"]
        if corpus:
            res = self.similarity_agent.search(inc, corpus, k=3)
            state["similar_incidents"] = [(c.id, c.root_cause, round(d, 3))
                                          for c, d in res]
        else:
            state["similar_incidents"] = []
        state["trace"].append(
            f"similarity_search: {len(state['similar_incidents'])} neighbors")
        return state

    def _resolution_recommend(self, state: dict) -> dict:
        inc = state["incident"]
        recs = self.resolution_agent.recommend(inc, top_k=2)
        state["recommended_actions"] = [(a, round(r, 3), t) for a, r, t in recs]
        # corroborate with causal hypotheses when available
        state["trace"].append(f"resolution_recommend: {state['recommended_actions']}")
        return state

    def _learning_update(self, state: dict) -> dict:
        # In production this collects ground truth post-resolution and
        # retrains; here it records what *would* be collected.
        inc = state["incident"]
        state["training_data_collected"] = {
            "incident_id": inc.id,
            "fields": ["symptoms", "change_link", "root_cause",
                       "resolution_outcome"],
        }
        state["trace"].append("learning_update: queued for retraining")
        return state
