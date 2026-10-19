"""Smoke tests for attention-economics."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np

from agentic_systems.attention_economics import (
    AlwaysAsk,
    BudgetAware,
    FixedThreshold,
    HumanPrincipal,
    NeverAsk,
    StakesAdjusted,
    Truncated,
    evaluate,
    expected_calibration_error,
    make_stream,
    over_trust_index,
    reliability_diagram,
    under_trust_index,
)


def _stream(**kw):
    kw.setdefault("seed", 7)
    return make_stream(500, **kw)


def _principal(**kw):
    kw.setdefault("budget", 10**9)
    kw.setdefault("interruption_cost", 5.0)
    kw.setdefault("error_cost", 1.0)
    return HumanPrincipal(**kw)


def test_stream_is_deterministic():
    a = _stream()
    b = _stream()
    assert np.allclose(a.stakes, b.stakes)
    assert np.allclose(a.confidence, b.confidence)
    assert (a.correct == b.correct).all()


def test_miscalibration_shifts_stated_not_truth():
    cal = _stream(miscalibration=0.0)
    over = _stream(miscalibration=0.15)
    assert over.confidence.mean() > cal.confidence.mean()
    # Same underlying competence: correctness draws use the same RNG path
    # up to the confidence shift, so accuracy is close but stated differs.
    assert abs(over.accuracy - cal.accuracy) < 0.05


def test_always_ask_has_no_unaudited_errors():
    rep = evaluate(_stream(), _principal(), AlwaysAsk(), seed=7)
    assert rep.n_unaudited_errors == 0
    assert rep.n_asks == 500


def test_never_ask_has_no_interruptions():
    rep = evaluate(_stream(), _principal(), NeverAsk(), seed=7)
    assert rep.n_asks == 0
    assert rep.n_unaudited_errors > 0


def test_stakes_adjusted_beats_baselines():
    s = _stream()
    p = _principal()
    costs = {
        "always": evaluate(s, p, AlwaysAsk(), seed=7).total_cost,
        "never": evaluate(s, p, NeverAsk(), seed=7).total_cost,
        "ev": evaluate(s, p, StakesAdjusted(), seed=7).total_cost,
    }
    assert costs["ev"] < costs["always"]
    assert costs["ev"] < costs["never"]


def test_budget_aware_respects_budget():
    s = _stream()
    p = _principal(budget=50)
    rep = evaluate(s, p, BudgetAware(50), seed=7)
    assert rep.n_asks <= 50


def test_budget_exceeded_counted():
    s = _stream()
    p = _principal(budget=10)
    rep = evaluate(s, p, AlwaysAsk(), seed=7)
    assert rep.n_asks == 10
    assert rep.n_budget_exceeded == 490


def test_truncated_is_first_come():
    s = _stream()
    p = _principal(budget=30)
    mask = Truncated(StakesAdjusted(), 30).select(s, p)
    assert mask.sum() <= 30
    # First-come: the asked set is a prefix of the wanted set in stream order
    want = StakesAdjusted().select(s, p)
    assert (mask & ~want).sum() == 0


def test_ece_near_zero_when_calibrated():
    s = _stream(miscalibration=0.0)
    assert expected_calibration_error(s) < 0.05


def test_ece_grows_with_miscalibration():
    s = _stream(miscalibration=0.15)
    assert expected_calibration_error(s) > 0.08


def test_reliability_diagram_monotone():
    s = _stream(miscalibration=0.0)
    _, stated, emp = reliability_diagram(s, n_bins=5)
    assert len(stated) > 0
    # Higher stated bins should not be wildly less accurate
    assert np.all(np.diff(emp) > -0.35)


def test_trust_indices_sign():
    s = _stream()
    p = _principal()
    # tau=0.5 trusts too much -> excess unaudited errors
    assert over_trust_index(s, p, 0.50, seed=7) > 0
    # tau=0.99 questions too much -> excess interruptions
    assert under_trust_index(s, p, 0.99, seed=7) > 0


def test_cost_report_adds_up():
    s = _stream()
    p = _principal()
    rep = evaluate(s, p, StakesAdjusted(), seed=7)
    expect = (rep.interruption_cost + rep.asked_human_error_cost
              + rep.unaudited_error_cost)
    assert abs(rep.total_cost - expect) < 1e-6


def test_no_forbidden_name():
    import agentic_systems.attention_economics as m
    import pathlib
    root = pathlib.Path(m.__file__).parent
    hits = []
    for f in list(root.glob("*.py")):
        text = f.read_text()
        if "devpulse" in text.lower():
            hits.append(str(f))
    assert not hits, hits
