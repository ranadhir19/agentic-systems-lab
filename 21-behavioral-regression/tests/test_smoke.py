"""Smoke tests for behavioral_regression."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from agentic_systems.behavioral_regression import (
    GROUND_TRUTH_POLICY,
    VERSIONS,
    CanaryAnalyzer,
    DriftDetector,
    ModelVersion,
    PolicyEngine,
    SimulatedAgent,
    build_battery,
    run_battery,
)

SEEDS = [7, 11, 42, 0, 99]


def _base_runs(n=120):
    bat = build_battery(n)
    return bat, [run_battery(SimulatedAgent(VERSIONS["v1"]), bat, s) for s in SEEDS]


def test_battery_deterministic():
    bat = build_battery(120)
    a = SimulatedAgent(VERSIONS["v1"])
    r1 = run_battery(a, bat, 7)
    r2 = run_battery(a, bat, 7)
    assert [x.passed for x in r1.results] == [x.passed for x in r2.results]
    assert r1.aggregate() == r2.aggregate()


def test_battery_frozen_across_versions():
    bat = build_battery(120)
    r1 = run_battery(SimulatedAgent(VERSIONS["v1"]), bat, 7)
    r3 = run_battery(SimulatedAgent(VERSIONS["v3"]), bat, 7)
    assert [x.task_id for x in r1.results] == [x.task_id for x in r3.results]


def test_detector_flags_v3_tool_regression():
    bat, base = _base_runs()
    cand = [run_battery(SimulatedAgent(VERSIONS["v3"]), bat, s) for s in SEEDS]
    rep = DriftDetector().compare(base, cand, "v3")
    flagged = {d.metric for d in rep.correctness_regressions()}
    assert "pass_tool_use" in flagged
    assert "format_compliance" in flagged


def test_detector_v2_has_no_correctness_regression():
    bat, base = _base_runs()
    cand = [run_battery(SimulatedAgent(VERSIONS["v2"]), bat, s) for s in SEEDS]
    rep = DriftDetector().compare(base, cand, "v2")
    assert rep.correctness_regressions() == []
    assert rep.improvements, "v2 should show improvements"


def test_severity_ordering():
    bat, base = _base_runs()
    det = DriftDetector()
    sev = {}
    for vn in ("v1", "v2", "v3", "v4", "v5"):
        cand = [run_battery(SimulatedAgent(VERSIONS[vn]), bat, s) for s in SEEDS]
        sev[vn] = det.compare(base, cand, vn).severity
    assert sev["v3"] > sev["v5"] > sev["v4"] > sev["v2"] >= 0.0
    assert sev["v1"] == 0.0
    assert sev["v3"] > 5 * sev["v2"], "silent break must dwarf verbosity"


def test_canary_stops_v3_at_first_stage():
    bat = build_battery(120)
    rep = CanaryAnalyzer().analyze(bat, VERSIONS["v1"], VERSIONS["v3"], seed=7)
    assert rep.stopped
    assert rep.tasks_to_flag == 40
    assert rep.stages[0].decision == "stop_rollback"


def test_canary_promotes_v2():
    bat = build_battery(120)
    rep = CanaryAnalyzer().analyze(bat, VERSIONS["v1"], VERSIONS["v2"], seed=7)
    assert not rep.stopped
    assert all(s.decision == "promote" for s in rep.stages)


def test_policy_matches_ground_truth():
    bat, base = _base_runs()
    det, pol, an = DriftDetector(), PolicyEngine(), CanaryAnalyzer()
    for vn, truth in GROUND_TRUTH_POLICY.items():
        cand = [run_battery(SimulatedAgent(VERSIONS[vn]), bat, s) for s in SEEDS]
        rep = det.compare(base, cand, vn)
        can = an.analyze(bat, VERSIONS["v1"], VERSIONS[vn], seed=7)
        dec = pol.decide(rep, can)
        assert dec.decision == truth, f"{vn}: got {dec.decision}, want {truth}"
        assert dec.rationale, "decision must carry a rationale"


def test_paired_structure_v1_vs_v1():
    # Identical versions must produce zero diffs everywhere.
    bat, base = _base_runs()
    rep = DriftDetector().compare(base, base, "v1-copy")
    assert rep.severity == 0.0
    assert rep.regressions == [] and rep.improvements == []


def test_no_forbidden_name():
    root = os.path.join(os.path.dirname(__file__), "..", "..", "src",
                        "agentic_systems", "behavioral_regression")
    for fn in os.listdir(root):
        if fn.endswith(".py"):
            src = open(os.path.join(root, fn)).read().lower()
            assert "devpulse" not in src, f"forbidden name in {fn}"
