"""Smoke tests for SRE-Learning."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np

from agentic_systems.sre_learning import (
    World, DataPipeline, ChangeRiskPredictor, CausalKnowledgeGraph,
    SimilarityAgent, TfidfBaseline, make_pairs, ResolutionAgent,
    SREWorkflow, ContinuousLearner, auc_score,
)


def _world(seed=7):
    w = World(seed=seed)
    chs = w.gen_changes(300, span_h=60 * 24.0)
    incs = w.gen_incidents(chs)
    return w, chs, incs


def test_world_generates_labeled_data():
    w, chs, incs = _world()
    assert len(chs) == 300 and len(incs) > 20
    assert any(c.caused_incident for c in chs)
    assert any(i.postmortem for i in incs)
    assert any(i.change_id < 0 for i in incs)  # organic incidents exist


def test_change_agent_learns_and_explains():
    w, chs, _ = _world()
    X, y = w.feature_matrix(chs), w.labels(chs)
    a = ChangeRiskPredictor().fit(X, y)
    assert auc_score(y, a.predict_proba(X)) > 0.6
    e = a.explain(X[0])
    assert 0 <= e["risk"] <= 1 and len(e["contributions"]) == 3
    assert "risk" in a.risk_sentence(X[0]).lower()


def test_change_agent_partial_fit_runs():
    w, chs, _ = _world()
    X, y = w.feature_matrix(chs), w.labels(chs)
    a = ChangeRiskPredictor().fit(X[:200], y[:200])
    before = a.w.copy()
    a.partial_fit(X[200:], y[200:], steps=10)
    assert not np.allclose(before, a.w)


def test_pipeline_linking_reports_accuracy():
    w, chs, incs = _world()
    pipe = DataPipeline(w)
    enr = pipe.enrich(incs, chs)
    acc = pipe.linking_accuracy(enr)
    assert acc["total"] > 0
    assert 0 <= acc["accuracy"] <= 1 and 0 <= acc["top3_accuracy"] <= 1
    assert acc["top3_accuracy"] >= acc["accuracy"]


def test_causal_graph_beats_chance():
    w, chs, incs = _world()
    g = CausalKnowledgeGraph().fit([i.postmortem for i in incs if i.postmortem])
    assert g.top_k_accuracy(incs, k=3) > 0.5


def test_similarity_retrieves_same_cause():
    w, chs, incs = _world()
    rng = np.random.default_rng(0)
    sim = SimilarityAgent().fit(make_pairs(incs, rng, n_pairs=400))
    assert sim.precision_at_k(incs[:20], incs, k=3) > 0.5
    # active-learning queue returns the requested budget
    pool = [(a, b) for a, b, _ in make_pairs(incs, rng, n_pairs=50)]
    assert len(sim.uncertain_pairs(pool, 10)) == 10


def test_resolution_recommends_and_counterfactual_updates():
    w, chs, incs = _world()
    r = ResolutionAgent().fit(incs)
    recs = r.recommend(incs[0], top_k=1)
    assert recs and 0 <= recs[0][1] <= 1
    inc = incs[0]
    inc.resolution_success = False
    r.observe_with_counterfactual(inc, recommended=recs[0][0])  # no crash


def test_workflow_runs_end_to_end():
    w, chs, incs = _world()
    X, y = w.feature_matrix(chs), w.labels(chs)
    ca = ChangeRiskPredictor().fit(X, y)
    pipe = DataPipeline(w, change_agent=ca)
    g = CausalKnowledgeGraph().fit([i.postmortem for i in incs if i.postmortem])
    rng = np.random.default_rng(0)
    sim = SimilarityAgent().fit(make_pairs(incs, rng, n_pairs=400))
    res = ResolutionAgent().fit(incs)
    wf = SREWorkflow(ca, g, sim, res, pipe)
    state = wf.run(incs[-1], changes=chs, corpus=incs)
    assert state["trace"][-1] == "END"
    assert state["recommended_actions"]
    assert "change_analysis" in state["trace"][0]


def test_continuous_learner_monthly_cycle():
    w, chs, incs = _world()
    X, y = w.feature_matrix(chs), w.labels(chs)
    ca = ChangeRiskPredictor().fit(X, y)
    learner = ContinuousLearner(ca, SimilarityAgent(), ResolutionAgent())
    m = learner.update(incs, chs, month=1, val_changes=chs, val_labels=y)
    assert m["month"] == 1 and "change_auc" in m
    assert 0 <= m["intervention_rate"] <= 1
