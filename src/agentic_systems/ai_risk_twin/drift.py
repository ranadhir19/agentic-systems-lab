"""Post-deployment drift detection.

The approved AI Use-Case Twin is the baseline. Runtime telemetry (the
*observed* architecture: which components actually called what) is
compared against it. Any observed edge that was not in the approved twin
is drift — e.g. an agent that begins calling an unapproved API — and
raises an alert graded by severity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from .twin import Twin


@dataclass
class DriftAlert:
    edge: Tuple[str, str, str]     # (src, dst, method/rel)
    severity: str
    detail: str


def _edge_key(e: Dict) -> Tuple[str, str, str]:
    return (e.get("src", ""), e.get("dst", ""),
            (e.get("method") or e.get("rel") or "").upper())


def detect_drift(approved: Twin,
                 observed_edges: List[Dict]) -> List[DriftAlert]:
    """Compare runtime-observed edges against the approved twin."""
    approved_keys = {_edge_key(e) for e in approved.edges}
    approved_pairs = {(s, d) for s, d, _ in approved_keys}
    alerts: List[DriftAlert] = []
    for e in observed_edges:
        key = _edge_key(e)
        if key in approved_keys:
            continue
        src, dst, _ = key
        comp = approved.components.get(dst, {})
        if (src, dst) not in approved_pairs:
            pii = (e.get("data") or "").lower() in (
                "pii", "confidential", "restricted")
            if comp.get("attrs", {}).get("external") or \
                    comp.get("kind") == "external_api" or not comp:
                severity = "critical" if (pii or not comp) else "high"
            else:
                severity = "high"
            alerts.append(DriftAlert(
                edge=key, severity=severity,
                detail=(f"Observed {src} -> {dst} was not in the approved "
                        f"twin (method/rel {key[2] or 'n/a'}). Unapproved "
                        "data/control flow.")))
        else:
            alerts.append(DriftAlert(
                edge=key, severity="medium",
                detail=(f"Observed {src} -> {dst} with unapproved "
                        f"method/rel {key[2]}; approved methods differ.")))
    return alerts
