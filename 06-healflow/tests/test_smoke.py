"""Smoke tests for HealFlow."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.catalog import (SUBSTITUTES, PREDS, build_injector, etl_flow,
                         order_flow, research_flow)
from src.runtime import HealFlowRuntime, ReplanBaseline, RetryBaseline


def _rt(**kw):
    return HealFlowRuntime(build_injector(), PREDS, SUBSTITUTES, **kw)


def test_transient_outage_recovered():
    rt = _rt()
    rt.injector.add_fault("extract", "outage", n=2)
    rep = rt.run(etl_flow(), expected_cause="transient_outage")
    assert rep.success and rep.side_effects == 0
    assert rep.correct_diagnosis is True
    assert rep.repairs == ["retry", "retry"]


def test_schema_change_substituted():
    rt = _rt()
    rt.injector.add_fault("extract", "schema_change",
                          mapping={"user_id": "uid"})
    rep = rt.run(etl_flow(), expected_cause="schema_change")
    assert rep.success and rep.repairs == ["substitute"]


def test_partial_transaction_compensated():
    rt = _rt()
    rt.injector.add_fault("reserve_inventory", "outage", n=99)
    rep = rt.run(order_flow())
    assert not rep.success and rep.graceful and rep.side_effects == 0
    assert "compensate_abort" in rep.repairs


def test_replan_double_charges():
    base = ReplanBaseline(build_injector(), PREDS)
    base.injector.add_fault("reserve_inventory", "outage", n=99)
    rep = base.run(order_flow())
    assert not rep.success and rep.side_effects >= 2


def test_retry_cannot_fix_schema_change():
    base = RetryBaseline(build_injector(), PREDS)
    base.injector.add_fault("extract", "schema_change",
                            mapping={"user_id": "uid"})
    rep = base.run(etl_flow())
    assert not rep.success


def test_repair_memory_transfer():
    rt = _rt(use_memory=True)
    rt.injector.add_fault("extract", "schema_change",
                          mapping={"user_id": "uid"})
    r1 = rt.run(etl_flow())
    assert r1.success
    rt.injector.reset()
    rt.injector.add_fault("search", "schema_change",
                          mapping={"title": "headline"})
    r2 = rt.run(research_flow())
    assert r2.success and r2.memory_hits >= 1
    # memory hit shortcuts full diagnosis
    assert r2.diagnosis_steps <= 2


def test_rollback_then_substitute_fallback():
    rt = _rt()
    rt.injector.add_fault("plan", "corrupt", n=99,
                          fn=lambda out: {"plan": ["???"]})
    rep = rt.run(research_flow(), expected_cause="bad_intermediate")
    assert rep.success
    assert rep.repairs == ["rollback_recompute", "substitute"]
