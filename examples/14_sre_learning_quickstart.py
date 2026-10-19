"""SRE-Learning quickstart: train on history, then work an incident.

1. Build a small seeded world (changes + incidents + postmortems).
2. Train the four agents on the historical corpus.
3. Score a risky change with an explanation.
4. Run the full conditional workflow on a fresh incident.

Run:  PYTHONPATH=src python3 examples/14_sre_learning_quickstart.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np

from agentic_systems.sre_learning import (
    World, DataPipeline, ChangeRiskPredictor, CausalKnowledgeGraph,
    SimilarityAgent, TfidfBaseline, make_pairs, ResolutionAgent,
    SREWorkflow, auc_score,
)


def main() -> None:
    rng = np.random.default_rng(7)
    w = World(seed=7)
    changes = w.gen_changes(900, span_h=90 * 24.0)
    incidents = w.gen_incidents(changes)
    print(f"world: {len(changes)} changes, {len(incidents)} incidents")

    # --- train the four agents on history ---------------------------------
    X, y = w.feature_matrix(changes), w.labels(changes)
    change_agent = ChangeRiskPredictor().fit(X, y)
    print(f"change-risk train AUC: {auc_score(y, change_agent.predict_proba(X)):.3f}")

    # a risky change, explained
    risky = max(changes, key=lambda c: change_agent.predict_proba(
        c.features().reshape(1, -1))[0])
    print("riskiest change:", change_agent.risk_sentence(risky.features()))
    assert change_agent.predict_proba(risky.features().reshape(1, -1))[0] > 0.5

    pipe = DataPipeline(w, change_agent=change_agent)
    enriched = pipe.enrich(incidents, changes)
    print("linking top-1/top-3:",
          f"{pipe.linking_accuracy(enriched)['accuracy']:.2f} / "
          f"{pipe.linking_accuracy(enriched)['top3_accuracy']:.2f}")

    graph = CausalKnowledgeGraph().fit(
        [i.postmortem for i in incidents if i.postmortem])
    sim = SimilarityAgent().fit(make_pairs(incidents, rng, n_pairs=1200))
    res = ResolutionAgent().fit(incidents)

    # --- work a fresh incident through the conditional workflow -----------
    fresh = max(incidents, key=lambda i: i.t_start)
    wf = SREWorkflow(change_agent, graph, sim, res, pipe)
    state = wf.run(fresh, changes=changes, corpus=incidents)
    for line in state["trace"]:
        print(" ", line)
    print("recommended:", state["recommended_actions"])
    assert state["recommended_actions"], "workflow must recommend an action"
    assert state["trace"][-1] == "END"

    print("Quickstart OK: agents trained on history, incident worked end-to-end.")


if __name__ == "__main__":
    main()
