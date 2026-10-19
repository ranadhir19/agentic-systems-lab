"""Smoke tests for Ideology Mirror."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np

from agentic_systems.ideology_mirror import (
    ARCHETYPES,
    DIMENSIONS,
    PROFILE_ALPHA,
    PROFILE_BETA,
    SimulatedAlignedModel,
    VendorProfile,
    assess,
    battery_coverage,
    build_battery,
    build_knowledge_base,
    ci_gate,
    default_corporate_constitution,
    divergence_matrix,
    drift_magnitude,
    mean_conformance,
    pairwise_divergence,
    refusal_asymmetry,
    run_battery,
    snapshot,
    steer,
    topic_by_id,
)


def _kb():
    return build_knowledge_base()


def _battery():
    return build_battery(_kb())


def test_knowledge_base_has_eight_topics():
    kb = _kb()
    assert len(kb) == 8
    assert all(len(t.frames) == 3 and len(t.facts) == 3 for t in kb)


def test_model_responds_to_every_probe():
    rng = np.random.default_rng(7)
    rs = run_battery(SimulatedAlignedModel(PROFILE_ALPHA), _battery(), rng)
    assert len(rs) == 8
    assert all(r.probe_id for r in rs)


def test_runs_are_deterministic():
    b = _battery()
    r1 = run_battery(SimulatedAlignedModel(PROFILE_ALPHA), b,
                     np.random.default_rng(7))
    r2 = run_battery(SimulatedAlignedModel(PROFILE_ALPHA), b,
                     np.random.default_rng(7))
    assert [x.frame_name for x in r1] == [x.frame_name for x in r2]


def test_creator_effect_divergence_positive():
    b = _battery()
    ra = run_battery(SimulatedAlignedModel(PROFILE_ALPHA), b,
                     np.random.default_rng(7))
    rb = run_battery(SimulatedAlignedModel(PROFILE_BETA), b,
                     np.random.default_rng(7))
    d = pairwise_divergence(ra, rb)
    assert d["composite"] > 0.5
    assert d["mean_l1_framing"] > 0.1


def test_divergence_matrix_symmetric():
    b = _battery()
    runs = [(p.name, run_battery(SimulatedAlignedModel(p), b,
                                np.random.default_rng(7)))
            for p in ARCHETYPES]
    names, m = divergence_matrix(runs)
    assert m.shape == (3, 3)
    assert np.allclose(m, m.T)
    assert np.allclose(np.diag(m), 0.0)


def test_conformance_bounded():
    b = _battery()
    const = default_corporate_constitution()
    rs = run_battery(SimulatedAlignedModel(PROFILE_BETA), b,
                     np.random.default_rng(7))
    mc = mean_conformance(rs, const)
    assert 0.0 <= mc["mean"] <= 1.0
    assert mc["refusals"] >= 1  # beta refuses at least one must-answer probe


def test_steering_never_hurts_conformance():
    b = _battery()
    const = default_corporate_constitution()
    for p in ARCHETYPES:
        before = mean_conformance(
            run_battery(SimulatedAlignedModel(p), b, np.random.default_rng(7)),
            const)["mean"]
        after = mean_conformance(
            run_battery(steer(SimulatedAlignedModel(p), const), b,
                        np.random.default_rng(7)), const)["mean"]
        assert after >= before - 1e-9


def test_drift_gate_fails_on_injected_shift():
    b = _battery()
    v1 = SimulatedAlignedModel(PROFILE_ALPHA, version="v1")
    v2 = SimulatedAlignedModel(PROFILE_ALPHA.shift("econ", -0.9), version="v2")
    s1 = snapshot(v1, b, np.random.default_rng(7))
    s2 = snapshot(v2, b, np.random.default_rng(8))
    gate = ci_gate(s1, s2, threshold=0.15)
    assert not gate.passed
    assert gate.worst_dimension == "econ"


def test_drift_gate_passes_on_identical_versions():
    b = _battery()
    v = SimulatedAlignedModel(PROFILE_ALPHA, version="v1")
    s1 = snapshot(v, b, np.random.default_rng(7))
    s2 = snapshot(v, b, np.random.default_rng(7))
    assert drift_magnitude(s1, s2)["max"] == 0.0
    assert ci_gate(s1, s2, threshold=0.15).passed


def test_vendor_assessment_grades_and_clauses():
    const = default_corporate_constitution()
    risky = VendorProfile(name="risky", measured=PROFILE_BETA,
                          transparency=0.2, version_pinning=False,
                          drift_clause=False, audit_rights=False)
    safe = VendorProfile(name="safe", measured=PROFILE_ALPHA,
                         transparency=0.9, version_pinning=True,
                         drift_clause=True, audit_rights=True)
    rr, rs = assess(risky, const), assess(safe, const)
    assert rr.overall > rs.overall
    assert len(rr.recommended_clauses) >= len(rs.recommended_clauses)
    assert rr.grade in "ABCDF" and rs.grade in "ABCDF"


def test_refusal_asymmetry_measurable():
    b = _battery()
    rs = run_battery(SimulatedAlignedModel(PROFILE_BETA), b,
                     np.random.default_rng(7))
    ra = refusal_asymmetry(rs, b, PROFILE_BETA)
    assert ra["challenging_refusal_rate"] >= ra["supportive_refusal_rate"]


def test_battery_covers_five_value_dimensions():
    # "tone" is expressed in every response but is never a probe's primary
    # dimension; the other five dimensions are all covered as primaries.
    cov = battery_coverage(_battery())
    assert set(cov) == {"econ", "culture", "corp", "geo", "risk"}
    assert sum(cov.values()) == 8
