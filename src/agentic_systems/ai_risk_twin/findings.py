"""Findings engine and readiness scoring.

Two kinds of findings:

- DESIGN findings: a security/control problem.
  (observation / concern / required action)
- INFORMATION findings: an evidence gap.
  (observation / unknown / required artifact)

Every finding carries its evidence and a confidence derived from the
evidence hierarchy. The readiness scorer combines four dimensions into a
go / no-go verdict for CISO submission:

- architecture completeness: are the twin's slots populated?
- evidence completeness: do information findings have L2+ evidence?
- control coverage: do design findings have evidenced controls?
- assessment confidence: mean finding confidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .consistency import Inconsistency
from .evidence import (Evidence, EvidenceLevel, combined_confidence,
                       level_name)
from .knowledge import Rule, Twin

SEVERITY_RANK = {"critical": 4, "high": 3, "medium": 2, "low": 1}

# Which rules a supplied evidence artifact satisfies. Supplying the
# artifact marks a matching information finding as evidenced and a
# matching design finding as controlled.
EVIDENCE_RULES = {
    "vendor_dpa": ["TP-01", "TP-02", "TP-03"],
    "soc2": ["TP-01"],
    "pen_test": ["LLM-01"],
    "eval_report": ["RM-02"],
    "incident_plan": ["RM-03"],
    "tool_manifest": ["AG-02"],
    "human_review_evidence": ["AG-01", "HO-01"],
    "retention_terms": ["TP-02"],
    "threat_model": ["AG-04", "LLM-01"],
}


@dataclass
class Finding:
    key: str                      # stable identity: rule_id + target
    rule_id: str
    source: str
    title: str
    kind: str                     # design | information
    severity: str
    observation: str
    risk: str                     # concern (design) or unknown (info)
    remedy: str                   # required action (design) or artifact (info)
    targets: List[str]
    evidence: List[Evidence] = field(default_factory=list)
    controlled: bool = False
    # Evidence supplied by the user that satisfies this finding's required
    # artifact at L2+. The base architecture evidence (L3) every finding
    # carries does NOT count: user assertions and parsed diagrams cannot
    # resolve an evidence gap on their own.
    satisfying: List[Evidence] = field(default_factory=list)

    @property
    def confidence(self) -> float:
        return combined_confidence(self.evidence)


@dataclass
class Readiness:
    architecture_completeness: float
    evidence_completeness: float
    control_coverage: float
    assessment_confidence: float
    score: float
    verdict: str                  # READY | NOT READY
    blocking: List[str]


def _finding_evidence(rule: Rule, twin: Twin,
                      target: str) -> List[Evidence]:
    """Collect the twin's own evidence relevant to a rule target."""
    out: List[Evidence] = []
    for p in twin.access_paths:
        tag = f"{p.diagram_edge['src']}->{p.diagram_edge['dst']}"
        if target in (tag, p.diagram_edge["src"], p.diagram_edge["dst"]):
            out.extend(p.evidence)
    # Every rule at minimum rests on the parsed architecture (L3).
    out.append(Evidence(EvidenceLevel.L3_ARTIFACT,
                       reference=f"arch:{rule.rid}",
                       detail="parsed architecture artifact"))
    # De-duplicate by reference, keeping the strongest level.
    best: Dict[str, Evidence] = {}
    for e in out:
        if (e.reference not in best or
                e.level > best[e.reference].level):
            best[e.reference] = e
    return list(best.values())


def run_rules(twin: Twin, rules: List[Rule],
              provided_evidence: Optional[Dict[str, Evidence]] = None
              ) -> List[Finding]:
    """Evaluate every rule against the twin; triggered rules -> findings."""
    provided = provided_evidence or {}
    findings: List[Finding] = []
    for rule in rules:
        if not _trigger(rule, twin):
            continue
        targets = rule.targets(twin) or ["twin"]
        controlled = rule.control_present(twin)
        # Evidence supplied by the user satisfies only the rules it
        # actually addresses (EVIDENCE_RULES), never the whole board.
        matched = [ev for kind, ev in provided.items()
                   if rule.rid in EVIDENCE_RULES.get(kind, [])]
        if matched and rule.kind == "design":
            controlled = True
        satisfying = [ev for ev in matched
                      if ev.level >= EvidenceLevel.L2_VENDOR_DOC]
        for target in targets:
            ev = _finding_evidence(rule, twin, target)
            ev.extend(matched)
            findings.append(Finding(
                key=f"{rule.rid}::{target}",
                rule_id=rule.rid, source=rule.source, title=rule.title,
                kind=rule.kind, severity=rule.severity,
                observation=rule.observation(twin),
                risk=rule.risk(twin), remedy=rule.remedy(twin),
                targets=[target], evidence=ev, controlled=controlled,
                satisfying=satisfying))
    findings.sort(key=lambda f: (-SEVERITY_RANK[f.severity], f.rule_id))
    return findings


def _trigger(rule: Rule, twin: Twin) -> bool:
    from .knowledge import TRIGGERS
    return TRIGGERS[rule.trigger](twin)


def score_readiness(twin: Twin, findings: List[Finding],
                    inconsistencies: List[Inconsistency]) -> Readiness:
    # Architecture completeness: six canonical slots.
    slots = [bool(twin.purpose), bool(twin.models), bool(twin.components),
             bool(twin.edges),
             any(p.identity for p in twin.access_paths),
             all(f["classification"] != "unclassified"
                 for f in twin.data_flows) if twin.data_flows else False]
    arch = sum(1 for s in slots if s) / len(slots)

    info = [f for f in findings if f.kind == "information"]
    if info:
        ev_comp = (sum(1 for f in info if f.satisfying) / len(info))
    else:
        ev_comp = 1.0

    design = [f for f in findings if f.kind == "design"]
    if design:
        control_cov = sum(1 for f in design if f.controlled) / len(design)
    else:
        control_cov = 1.0

    conf = (sum(f.confidence for f in findings) / len(findings)
            if findings else 1.0)

    score = round(0.25 * arch + 0.25 * ev_comp + 0.25 * control_cov +
                  0.25 * conf, 4)

    blocking: List[str] = []
    crit_open = [f for f in design
                 if f.severity == "critical" and not f.controlled]
    if crit_open:
        blocking.append(f"{len(crit_open)} critical design finding(s) "
                        "without evidenced control")
    if ev_comp < 1.0:
        missing = sum(1 for f in info if not f.satisfying)
        blocking.append(f"{missing} mandatory evidence item(s) unresolved")
    if inconsistencies:
        blocking.append(f"{len(inconsistencies)} architecture/documentation "
                        "inconsistencies")
    verdict = "READY" if not blocking else "NOT READY"
    return Readiness(architecture_completeness=round(arch, 4),
                     evidence_completeness=round(ev_comp, 4),
                     control_coverage=round(control_cov, 4),
                     assessment_confidence=round(conf, 4),
                     score=score, verdict=verdict, blocking=blocking)


def open_findings(findings: List[Finding]) -> List[Finding]:
    """Findings not yet resolved by an evidenced control."""
    return [f for f in findings if not f.controlled]


def summarize_findings(findings: List[Finding]) -> Dict[str, int]:
    out: Dict[str, int] = {"design": 0, "information": 0,
                           "critical": 0, "high": 0,
                           "medium": 0, "low": 0}
    for f in findings:
        out[f.kind] += 1
        out[f.severity] += 1
    out["total"] = len(findings)
    return out
