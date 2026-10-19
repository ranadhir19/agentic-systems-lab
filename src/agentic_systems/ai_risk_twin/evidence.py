"""Evidence hierarchy for the CISO AI Risk Twin.

Every fact and every finding carries an evidence level. The engine
distinguishes assertion from verification: a finding grounded in a user
assertion (L1) carries a high uncertainty penalty, while one grounded in
enterprise system evidence (L4) or runtime telemetry (L5) resolves with
high confidence.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import List, Optional


class EvidenceLevel(IntEnum):
    L0_ASSUMPTION = 0   # AI inference / assumption
    L1_ASSERTION = 1    # user assertion (typed in a form / design doc)
    L2_VENDOR_DOC = 2   # vendor documentation (DPA, SOC 2 report)
    L3_ARTIFACT = 3     # architecture / IaC artifacts
    L4_ENTERPRISE = 4   # enterprise system evidence (Entra ID, IAM policy)
    L5_TELEMETRY = 5    # runtime / telemetry evidence (logs, traces)


# Uncertainty penalty per level: higher penalty = less trustworthy.
UNCERTAINTY = {
    EvidenceLevel.L0_ASSUMPTION: 0.90,
    EvidenceLevel.L1_ASSERTION: 0.60,
    EvidenceLevel.L2_VENDOR_DOC: 0.40,
    EvidenceLevel.L3_ARTIFACT: 0.25,
    EvidenceLevel.L4_ENTERPRISE: 0.10,
    EvidenceLevel.L5_TELEMETRY: 0.05,
}

LEVEL_NAMES = {
    EvidenceLevel.L0_ASSUMPTION: "L0 assumption",
    EvidenceLevel.L1_ASSERTION: "L1 user assertion",
    EvidenceLevel.L2_VENDOR_DOC: "L2 vendor documentation",
    EvidenceLevel.L3_ARTIFACT: "L3 architecture/IaC artifact",
    EvidenceLevel.L4_ENTERPRISE: "L4 enterprise system",
    EvidenceLevel.L5_TELEMETRY: "L5 runtime telemetry",
}


@dataclass
class Evidence:
    level: EvidenceLevel
    reference: str
    detail: str = ""

    @property
    def confidence(self) -> float:
        return 1.0 - UNCERTAINTY[self.level]


def combined_confidence(items: List[Evidence]) -> float:
    """Confidence of a set of evidence items.

    Independent corroboration raises confidence: the best item sets the
    floor and each additional distinct-level item closes part of the
    remaining uncertainty gap.
    """
    if not items:
        return 0.0
    conf = max(e.confidence for e in items)
    seen = {items[0].level}
    for e in sorted(items, key=lambda x: x.confidence, reverse=True)[1:]:
        if e.level not in seen:
            seen.add(e.level)
            conf = conf + (1.0 - conf) * 0.5 * e.confidence
    return round(min(conf, 0.99), 4)


def level_name(level: EvidenceLevel) -> str:
    return LEVEL_NAMES[level]
