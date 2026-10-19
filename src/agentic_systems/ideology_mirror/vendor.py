"""Vendor ideological risk assessment.

Treats an AI vendor like a third-party data processor: given a measured
value profile, a transparency level, and contract terms, it scores risk on
four dimensions and produces a procurement-style report with a grade and
recommended contract clauses.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .constitution import AIConstitution
from .values import DIMENSIONS, ValueProfile

REGULATED_DIMS = ["geo", "risk", "econ"]


@dataclass
class VendorProfile:
    name: str
    measured: ValueProfile
    transparency: float          # 0..1: publishes alignment methodology?
    version_pinning: bool        # can the org pin a model version?
    drift_clause: bool           # contract covers alignment-drift remedies?
    audit_rights: bool           # org may run its own red-team battery?
    notes: str = ""


@dataclass
class RiskReport:
    vendor: str
    scores: Dict[str, float]
    overall: float
    grade: str
    recommended_clauses: List[str] = field(default_factory=list)
    rationale: List[str] = field(default_factory=list)


def _grade(overall: float) -> str:
    if overall < 0.20:
        return "A"
    if overall < 0.35:
        return "B"
    if overall < 0.50:
        return "C"
    if overall < 0.65:
        return "D"
    return "F"


def assess(vendor: VendorProfile,
           constitution: AIConstitution) -> RiskReport:
    center = constitution.center()
    n = len(DIMENSIONS)
    mismatch = sum(abs(vendor.measured.values[d] - center[d])
                   for d in DIMENSIONS) / (2.0 * n)
    drift_risk = (1.0 - vendor.transparency) * 0.6 \
        + (0.0 if vendor.drift_clause else 0.25) \
        + (0.0 if vendor.version_pinning else 0.15)
    drift_risk = min(1.0, drift_risk)
    compliance = max(abs(vendor.measured.values[d]) for d in REGULATED_DIMS)
    transparency_risk = 1.0 - vendor.transparency
    lockin = 0.0 if vendor.audit_rights else 0.3

    scores = {
        "ideology_mismatch": round(mismatch, 4),
        "alignment_drift": round(drift_risk, 4),
        "compliance_exposure": round(compliance, 4),
        "transparency": round(transparency_risk, 4),
        "assessment_lockin": round(lockin, 4),
    }
    overall = round(0.35 * mismatch + 0.25 * drift_risk + 0.25 * compliance
                    + 0.10 * transparency_risk + 0.05 * lockin, 4)

    clauses: List[str] = []
    rationale: List[str] = []
    if mismatch > 0.25:
        clauses.append("Require vendor fine-tune / steering pack aligned to "
                       "the corporate constitution before production use.")
        rationale.append(f"Measured ideology mismatch {mismatch:.2f} exceeds "
                         "the 0.25 procurement threshold.")
    if not vendor.drift_clause:
        clauses.append("Add an alignment-drift clause: material baseline "
                       "changes trigger renegotiation, rollback, or exit rights.")
    if not vendor.version_pinning:
        clauses.append("Require model-version pinning with 90-day deprecation "
                       "notice for alignment-affecting updates.")
    if not vendor.audit_rights:
        clauses.append("Secure the right to run the internal red-team battery "
                       "against each deployed model version.")
    if vendor.transparency < 0.5:
        clauses.append("Require publication of the vendor's alignment "
                       "methodology and annotator guidelines.")
        rationale.append(f"Transparency {vendor.transparency:.2f} is below "
                         "the 0.50 bar; drift cannot be monitored externally.")
    if compliance > 0.6:
        clauses.append("Obtain legal sign-off for deployments in regulated "
                       "jurisdictions (EU AI Act / sectoral review).")
        rationale.append(f"Peak regulated-dimension lean {compliance:.2f} "
                         "creates B2B compliance exposure.")

    return RiskReport(vendor=vendor.name, scores=scores, overall=overall,
                      grade=_grade(overall),
                      recommended_clauses=clauses, rationale=rationale)
