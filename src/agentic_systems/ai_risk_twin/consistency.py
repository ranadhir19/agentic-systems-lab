"""Consistency checking: design-document claims vs the architecture graph.

The twin's doc claims are user assertions (L1). The architecture edges are
parsed artifacts (L3). When they disagree, the artifact wins and an
inconsistency is recorded — the system never lets a claim override what
the architecture actually shows.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from .twin import Twin, is_write_edge


@dataclass
class Inconsistency:
    subject: str
    claim: str
    observed: str
    detail: str


_READ_ONLY_ALIASES = {"read-only", "readonly", "read only"}
_NO_PII_ALIASES = {"no pii", "no-pii", "no personal data"}


def _norm(text: str) -> str:
    return text.strip().lower()


def check_consistency(twin: Twin) -> List[Inconsistency]:
    """Compare every doc claim against the parsed architecture."""
    out: List[Inconsistency] = []
    for c in twin.doc_claims:
        subject = c.get("subject", "")
        claim = _norm(c.get("claim", ""))
        if claim in _READ_ONLY_ALIASES:
            writes = [e for e in twin.edges
                      if e.get("src") == subject and is_write_edge(e)]
            for e in writes:
                out.append(Inconsistency(
                    subject=subject, claim=c.get("claim", ""),
                    observed=(f"write edge {e['src']} -> {e['dst']} "
                              f"({e.get('method', e.get('rel'))})"),
                    detail=("Document asserts read-only, but the "
                            "architecture shows a state-changing "
                            "operation.")))
        if claim in _NO_PII_ALIASES:
            pii = [f for f in twin.data_flows
                   if f["classification"] in ("pii", "confidential",
                                              "restricted")]
            for f in pii:
                out.append(Inconsistency(
                    subject=subject, claim=c.get("claim", ""),
                    observed=(f"data flow {f['src']} -> {f['dst']} "
                              f"classified {f['classification']}"),
                    detail=("Document asserts no personal data, but a "
                            "classified data flow exists.")))
        if claim.startswith("no external"):
            exts = twin.external_deps()
            if exts:
                out.append(Inconsistency(
                    subject=subject, claim=c.get("claim", ""),
                    observed=f"external components: {', '.join(exts)}",
                    detail=("Document asserts no external dependencies, "
                            "but external components are present.")))
    return out


def claim_coverage(twin: Twin) -> Dict[str, float]:
    """Fraction of claims that are consistent with the architecture."""
    total = len(twin.doc_claims)
    if total == 0:
        return {"total": 0, "inconsistent": 0, "coverage": 1.0}
    bad = len(check_consistency(twin))
    return {"total": total, "inconsistent": bad,
            "coverage": round(1.0 - bad / total, 4)}
