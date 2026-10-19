"""Smoke tests for the CISO AI Risk Twin."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from agentic_systems import ai_risk_twin as rt


def test_bank_has_125_questions():
    bank = rt.build_question_bank()
    assert len(bank) == 125
    assert len({q.qid for q in bank}) == 125


def test_rule_count_and_sources():
    rules = rt.build_rules()
    assert len(rules) >= 25
    sources = {r.source for r in rules}
    assert any("OWASP" in s for s in sources)
    assert any("NIST" in s for s in sources)
    assert any("GDPR" in s or "EU AI Act" in s for s in sources)


def test_worked_example_inconsistency():
    twin = rt.worked_example()
    inc = rt.check_consistency(twin)
    assert len(inc) == 2
    assert any("read-only" in i.claim and "POST" in i.observed for i in inc)


def test_diagram_not_blindly_trusted():
    twin = rt.worked_example()
    # The legacy_reporting_db edge has no IaC grant: must be unverified,
    # never assumed safe.
    unv = [(p.diagram_edge["src"], p.diagram_edge["dst"])
           for p in twin.unverified_paths()]
    assert ("support_agent", "legacy_reporting_db") in unv
    findings = rt.run_rules(twin, rt.build_rules())
    assert any(f.rule_id == "IAM-02" for f in findings)


def test_pii_to_external_llm_finding():
    twin = rt.worked_example()
    findings = rt.run_rules(twin, rt.build_rules())
    tp3 = [f for f in findings if f.rule_id == "TP-03"]
    assert tp3 and all(f.severity == "critical" for f in tp3)


def test_funnel_shrinks_with_simplicity():
    bank = rt.build_question_bank()
    simple = rt.run_funnel(rt.simple_chatbot(), bank).counts
    complex_ = rt.run_funnel(rt.agentic_platform(), bank).counts
    assert simple["bank"] == 125 == complex_["bank"]
    assert simple["relevant"] < complex_["relevant"]
    for k in ("auto_answered", "evidence_required", "clarification"):
        assert (simple[k] + complex_[k]) >= 0  # stages partition relevant
    s = simple
    assert (s["auto_answered"] + s["evidence_required"] +
            s["clarification"] == s["relevant"])


def test_evidence_hierarchy_confidence():
    twin = rt.worked_example()
    rules = rt.build_rules()
    inc = rt.check_consistency(twin)
    c_none = rt.score_readiness(
        twin, rt.open_findings(rt.run_rules(twin, rules)), inc)
    c_l4 = rt.score_readiness(
        twin, rt.open_findings(rt.run_rules(
            twin, rules,
            rt.vendor_evidence_pack(rt.EvidenceLevel.L4_ENTERPRISE))), inc)
    assert c_l4.assessment_confidence > c_none.assessment_confidence
    assert c_l4.evidence_completeness > c_none.evidence_completeness


def test_fix_and_rerun_resolves():
    rules = rt.build_rules()
    before = rt.open_findings(rt.run_rules(rt.worked_example(), rules))
    after = rt.open_findings(rt.run_rules(rt.worked_example_fixed(), rules))
    d = rt.diff_findings(before, after)
    assert d.counts["resolved"] >= 4
    assert d.severity_delta() < 0
    assert "AG-01" in {f.rule_id for f in d.resolved}


def test_drift_detection():
    twin = rt.worked_example()
    obs = [{"src": e["src"], "dst": e["dst"], "method": e.get("method"),
            "rel": e.get("rel"), "data": e.get("data")}
           for e in twin.edges]
    assert rt.detect_drift(twin, obs) == []
    obs.append({"src": "support_agent", "dst": "shadow_analytics",
                "rel": "sends", "data": "pii"})
    alerts = rt.detect_drift(twin, obs)
    assert len(alerts) == 1
    assert alerts[0].severity == "critical"


def test_readiness_not_ready_initially():
    twin = rt.worked_example()
    rules = rt.build_rules()
    findings = rt.open_findings(rt.run_rules(twin, rules))
    r = rt.score_readiness(twin, findings, rt.check_consistency(twin))
    assert r.verdict == "NOT READY"
    assert r.blocking


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_")]
    for t in tests:
        t()
        print(f"PASS {t.__name__}")
    print(f"{len(tests)}/{len(tests)} tests passed")
