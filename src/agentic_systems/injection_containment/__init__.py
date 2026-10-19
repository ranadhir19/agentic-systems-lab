"""Injection Containment: stop prompt-injection payloads from propagating
across agent delegation chains.

Single-agent injection defenses do not cover the multi-agent propagation
path: a poisoned tool output flows into agent A, becomes B's delegated
subtask, and is acted on with C's credentials. This library simulates
that path with provenance tracking and measures four containment
defenses plus the semantic mosaic effect.

Public API:
    content:    Content, summarize, SYSTEM/USER/TOOL/DOCUMENT/WEB
    payloads:   PAYLOADS, CARRIERS, build_carrier_content, CANARIES
    parse:      extract_candidates, adoptable
    chain:      Chain, ChainResult, AgentState, ROLE_TOOLS
    defenses:   ProvenanceFirewall, PrivilegeBoundary, OutputSanitizer,
                TripwireCanary
    mosaic:     TILES, run_mosaic_trial, per_source_guard,
                aggregation_detector
"""

from .chain import AgentState, Chain, ChainResult, ROLE_TOOLS
from .content import (DOCUMENT, SYSTEM, TOOL, USER, WEB, Content,
                      summarize)
from .defenses import (OutputSanitizer, PrivilegeBoundary,
                       ProvenanceFirewall, TripwireCanary)
from .mosaic import (TILES, aggregation_detector, per_source_guard,
                     run_mosaic_trial)
from .parse import adoptable, extract_candidates
from .payloads import (CANARIES, CARRIERS, LEGITIMATE, PAYLOADS,
                       build_carrier_content, build_legitimate_content)

__all__ = [
    "AgentState",
    "CANARIES",
    "CARRIERS",
    "DOCUMENT",
    "SYSTEM",
    "TOOL",
    "USER",
    "WEB",
    "Chain",
    "ChainResult",
    "Content",
    "LEGITIMATE",
    "OutputSanitizer",
    "PAYLOADS",
    "PrivilegeBoundary",
    "ProvenanceFirewall",
    "ROLE_TOOLS",
    "TILES",
    "TripwireCanary",
    "adoptable",
    "aggregation_detector",
    "build_carrier_content",
    "build_legitimate_content",
    "extract_candidates",
    "per_source_guard",
    "run_mosaic_trial",
    "summarize",
]
