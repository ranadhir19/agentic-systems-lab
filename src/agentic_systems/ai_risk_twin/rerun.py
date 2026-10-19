"""Fix-and-rerun loop: modify the architecture, re-assess, diff findings.

The pre-check is iterative: upload architecture -> findings -> fix the
architecture (e.g. add a human-approval node) -> re-assess -> compare.
This module diffs two finding sets by stable finding key and reports
resolved, introduced, and unchanged findings, plus the severity delta.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from .findings import SEVERITY_RANK, Finding


@dataclass
class FindingDiff:
    resolved: List[Finding] = field(default_factory=list)
    introduced: List[Finding] = field(default_factory=list)
    unchanged: List[Finding] = field(default_factory=list)
    still_open: List[Finding] = field(default_factory=list)

    @property
    def counts(self) -> Dict[str, int]:
        return {
            "resolved": len(self.resolved),
            "introduced": len(self.introduced),
            "unchanged": len(self.unchanged),
            "still_open": len(self.still_open),
        }

    def severity_delta(self) -> int:
        """Net change in severity weight (negative = improvement)."""
        before = sum(SEVERITY_RANK[f.severity]
                     for f in self.resolved + self.still_open)
        after = sum(SEVERITY_RANK[f.severity]
                    for f in self.introduced + self.still_open)
        return after - before


def diff_findings(before: List[Finding],
                  after: List[Finding]) -> FindingDiff:
    before_map = {f.key: f for f in before}
    after_map = {f.key: f for f in after}
    diff = FindingDiff()
    for key, f in before_map.items():
        if key not in after_map:
            diff.resolved.append(f)
        else:
            diff.unchanged.append(f)
    for key, f in after_map.items():
        if key not in before_map:
            diff.introduced.append(f)
        else:
            diff.still_open.append(f)
    return diff
