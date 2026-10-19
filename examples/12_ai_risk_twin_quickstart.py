"""CISO AI Risk Twin quickstart: architecture-first risk pre-check.

Runs the worked example end to end: a support agent whose design doc
claims it is "read-only", while the architecture shows
POST /holdTransaction — and customer PII flowing to an external LLM.
The twin flags the inconsistency, raises design and information
findings, scores readiness, and shows the fix-and-rerun loop.

Run:  python3 examples/12_ai_risk_twin_quickstart.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agentic_systems import ai_risk_twin as rt


def main() -> None:
    twin = rt.worked_example()
    bank = rt.build_question_bank()
    rules = rt.build_rules()

    # 1. Consistency: doc claims vs architecture (artifact wins).
    inc = rt.check_consistency(twin)
    print(f"inconsistencies: {len(inc)}")
    for i in inc:
        print(f"  CONFLICT  doc says {i.claim!r} but {i.observed}")

    # 2. Findings from the knowledge-base rule engine.
    findings = rt.open_findings(rt.run_rules(twin, rules))
    s = rt.summarize_findings(findings)
    print(f"findings: {s['total']} "
          f"({s['design']} design, {s['information']} information; "
          f"{s['critical']} critical)")
    for f in findings:
        if f.severity == "critical":
            print(f"  CRITICAL  [{f.rule_id}] {f.title}")
    assert any(f.rule_id == "TP-03" for f in findings), \
        "PII -> external LLM finding must fire"

    # 3. Dynamic funnel: 125 questions shrink by architecture.
    fr = rt.run_funnel(twin, bank)
    c = fr.counts
    print(f"funnel: {c['bank']} -> {c['relevant']} relevant -> "
          f"{c['auto_answered']} auto-answered -> "
          f"{c['evidence_required']} evidence-required -> "
          f"{c['clarification']} clarification")

    # 4. Readiness: go / no-go for CISO submission.
    r = rt.score_readiness(twin, findings, inc)
    print(f"readiness: {r.score:.4f} -> {r.verdict}")
    for b in r.blocking:
        print(f"  BLOCKED  {b}")
    assert r.verdict == "NOT READY"

    # 5. Fix-and-rerun: add human approval, re-assess, diff.
    fixed = rt.worked_example_fixed()
    d = rt.diff_findings(findings,
                         rt.open_findings(rt.run_rules(fixed, rules)))
    print(f"fix-and-rerun: {d.counts['resolved']} resolved, "
          f"{d.counts['introduced']} introduced, "
          f"severity delta {d.severity_delta():+d}")
    assert d.counts["resolved"] >= 4, "the fix must resolve findings"

    # 6. Drift: runtime observation vs the approved twin.
    obs = [{"src": e["src"], "dst": e["dst"],
            "method": e.get("method"), "rel": e.get("rel")}
           for e in twin.edges]
    obs.append({"src": "support_agent", "dst": "shadow_analytics",
                "rel": "sends", "data": "pii"})
    alerts = rt.detect_drift(twin, obs)
    print(f"drift alerts: {len(alerts)}")
    for a in alerts:
        print(f"  {a.severity.upper():8s} {a.edge[0]} -> {a.edge[1]}")
    assert any(a.severity == "critical" for a in alerts)

    print("Pre-check complete: evidence-seeking assessment, no questionnaire.")


if __name__ == "__main__":
    main()
