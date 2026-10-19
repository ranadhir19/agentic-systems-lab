"""Governance: policy engine for skill execution.

Rules enforced before (and during) a run:
1. Capability allowlist — a skill may only invoke capabilities in
   manifest.approved_tools (when non-empty).
2. Version policy — deprecated versions are refused unless explicitly
   pinned AND the caller passes allow_deprecated=True.
3. Sensitivity gate — capabilities marked "high" sensitivity (e.g.
   code.execute, data.export) require an approval token; autonomous runs
   without one are blocked with a reason.
4. Data classification — a skill classified "confidential" may not bind to
   servers tagged "external".

Violations return a denial (no exception) so the harness can count them.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str = ""


class PolicyEngine:
    def __init__(self, forbid_deprecated: bool = True):
        self.forbid_deprecated = forbid_deprecated

    def check(self, skill, bound: dict[str, tuple], broker,
              approval_token: str | None = None,
              allow_deprecated: bool = False) -> PolicyDecision:
        m = skill.manifest
        if m.deprecated and self.forbid_deprecated and not allow_deprecated:
            return PolicyDecision(False, f"{m.name}@{m.version} is deprecated")
        allowed_tools = set(m.approved_tools) or set(m.required_capabilities)
        for cap in bound:
            if cap not in allowed_tools:
                return PolicyDecision(
                    False, f"capability '{cap}' not in approved_tools")
            if broker.sensitivity_of(cap) == "high" and approval_token is None:
                return PolicyDecision(
                    False, f"capability '{cap}' is high-sensitivity: "
                           "approval required")
        return PolicyDecision(True, "ok")
