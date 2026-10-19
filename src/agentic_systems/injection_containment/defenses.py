"""Containment defenses against injection propagation.

Each defense exposes hook methods consumed by `Chain._check`:
    on_instruction(content, agent) -> ("block"|"allow", detail) | None
    on_tool_call(agent, tool, args, content) -> verdict | None
    on_delegate(content, source_agent, target_agent) -> verdict | None
    on_exfil(agent, tool, args, content) -> verdict | None

The first defense to return a non-None verdict decides. "block" stops the
action; "allow" explicitly permits it; "flag" records an alert without
stopping (detection, not prevention).
"""
from __future__ import annotations

import re

from .content import USER, Content
from .parse import IMPERATIVE_PATTERNS, extract_candidates
from .payloads import CANARIES

# Sensitive tools: never in a default agent scope; need explicit user grant.
SENSITIVE_TOOLS = ("db_export", "approve_transfer")


class ProvenanceFirewall:
    """Tainted content cannot become instructions.

    STRICT: any instruction-looking content below USER trust is blocked.
    ATTRIBUTED: same, except content explicitly attributed to the user
    (e.g. the user's own note relayed through a document) is allowed.
    The strict/attributed gap is the false-positive tradeoff, measured in
    the experiments.
    """

    name = "provenance_firewall"

    def __init__(self, mode: str = "strict"):
        assert mode in ("strict", "attributed")
        self.mode = mode

    def on_instruction(self, content: Content, agent: str):
        if content.trust >= USER:
            return None
        if not content.is_tainted and content.trust >= USER:
            return None
        if self.mode == "attributed" and content.attributed_to_user:
            return ("allow", f"user-attributed content allowed for {agent}")
        return ("block",
                f"tainted instruction from {content.source} blocked for {agent}")


class PrivilegeBoundary:
    """Each agent's tools are scoped; sensitive tools need user re-authorization.

    A cross-boundary call (sensitive tool, no user grant) is blocked even if
    the agent was socially engineered into wanting it. This contains the
    *blast radius*: the injection may be adopted as an idea, but it cannot
    act with someone else's credentials.
    """

    name = "privilege_boundary"

    def __init__(self, user_grants: tuple = ()):
        self.user_grants = set(user_grants)

    def on_tool_call(self, agent: str, tool: str, args: str, content: Content):
        if tool in SENSITIVE_TOOLS and tool not in self.user_grants:
            return ("block",
                    f"{agent} denied {tool}: outside privilege boundary")
        return None


class OutputSanitizer:
    """Strip imperative language from untrusted content before it is used.

    Applied at delegation time (what flows downstream is cleaned) and at
    instruction-extraction time. Explicit overrides ("ignore previous
    instructions") are removed reliably; subtle nudges phrased as
    observations mostly survive — the measured gap.
    """

    name = "output_sanitizer"

    # Patterns the sanitizer reliably removes.
    STRIP = [
        re.compile(r"(?i)[^.!?]*\bignore (all )?previous instructions\b[^.!?]*[.!?]"),
        re.compile(r"(?i)[^.!?]*\b(your new )?(top )?priority is\b[^.!?]*[.!?]"),
        re.compile(r"(?i)[^.!?]*\byou (must|have to|are required to)\b[^.!?]*[.!?]"),
        re.compile(r"(?i)[^.!?]*\b(send|export)\b[^.!?]*\bhttps?://\S+[^.!?]*[.!?]"),
        re.compile(r"(?i)[^.!?]*\bapprove\b[^.!?]*\$\s?[\d,]+[^.!?]*[.!?]"),
        re.compile(r"(?i)[^.!?]*\bgranted administrator privileges\b[^.!?]*[.!?]"),
    ]

    def sanitize(self, content: Content) -> Content:
        if content.trust >= USER:
            return content
        text = content.text
        for pat in self.STRIP:
            text = pat.sub(" ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return content.with_text(text)

    def on_instruction(self, content: Content, agent: str):
        cleaned = self.sanitize(content)
        if not extract_candidates(cleaned):
            return ("block",
                    f"sanitized instruction from {content.source} for {agent}")
        return None

    def on_delegate(self, content: Content, source_agent: str,
                    target_agent: str):
        # Delegation carries the sanitized form onward.
        return None


class TripwireCanary:
    """Planted secrets that trigger alerts when exfiltrated.

    Detection, not prevention: the exfiltration may complete, but the
    tripwire fires. False positives come from legitimate mentions of
    canary-like strings in benign outputs.
    """

    name = "tripwire_canary"

    def on_exfil(self, agent: str, tool: str, args: str, content: Content):
        haystack = (args + " " + content.text).upper()
        for canary in CANARIES:
            if canary in haystack:
                return ("flag",
                        f"CANARY {canary} seen leaving via {agent}/{tool}")
        return None

    def scan_text(self, text: str) -> list[str]:
        return [c for c in CANARIES if c in text.upper()]
