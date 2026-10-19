"""Artifact ingestors for the CISO AI Risk Twin.

The Risk Twin is evidence-seeking, not answer-seeking: it ingests the
engineering artifacts developers already have and reconstructs the system
from them. This module normalizes four artifact kinds into typed evidence
facts:

- ArchSpec:      structured architecture spec (nodes + edges). In a full
                 deployment this would be produced by vision/OCR parsing of
                 a diagram; here the diagram is supplied as structured data.
- IaCConfig:     infrastructure-as-code-like resources (identities, role
                 assignments, network rules).
- MCPManifest:   tool manifests exposed by MCP servers.
- DocClaims:     assertions extracted from design documents.

Each ingestor returns a list of EvidenceFact records carrying an evidence
level (see evidence.py): parsed artifacts are L3, user assertions L1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .evidence import Evidence, EvidenceLevel


@dataclass
class EvidenceFact:
    """One normalized, attributable fact extracted from an artifact."""
    kind: str                      # e.g. "node", "edge", "role_assignment"
    payload: Dict[str, Any]        # the normalized fact
    source: str                    # which artifact produced it
    evidence: Evidence             # evidence level + reference


@dataclass
class ArchSpec:
    nodes: List[Dict[str, Any]]     # {id, kind, attrs}
    edges: List[Dict[str, Any]]     # {src, dst, rel, method?, data?, attrs?}


@dataclass
class IaCConfig:
    resources: List[Dict[str, Any]]  # {type, name, attrs}


@dataclass
class MCPManifest:
    server_id: str
    tools: List[Dict[str, Any]]       # {name, method, path, input_schema?, auth?}


@dataclass
class DocClaims:
    claims: List[Dict[str, Any]]     # {subject, claim, detail?}


def _ev(level: EvidenceLevel, ref: str) -> Evidence:
    return Evidence(level=level, reference=ref,
                    detail="parsed from supplied artifact")


def ingest_arch(spec: ArchSpec, name: str = "architecture") -> List[EvidenceFact]:
    facts: List[EvidenceFact] = []
    for n in spec.nodes:
        facts.append(EvidenceFact(
            kind="node", payload=dict(n), source=name,
            evidence=_ev(EvidenceLevel.L3_ARTIFACT,
                        f"{name}:node:{n.get('id')}")))
    for e in spec.edges:
        facts.append(EvidenceFact(
            kind="edge", payload=dict(e), source=name,
            evidence=_ev(EvidenceLevel.L3_ARTIFACT,
                        f"{name}:edge:{e.get('src')}->{e.get('dst')}")))
    return facts


def ingest_iac(cfg: IaCConfig, name: str = "iac") -> List[EvidenceFact]:
    facts: List[EvidenceFact] = []
    for r in cfg.resources:
        kind = {"service_principal": "identity",
                "role_assignment": "role_assignment",
                "network_rule": "network_rule"}.get(r.get("type"), "resource")
        facts.append(EvidenceFact(
            kind=kind, payload=dict(r), source=name,
            evidence=_ev(EvidenceLevel.L3_ARTIFACT,
                        f"{name}:{r.get('type')}:{r.get('name')}")))
    return facts


def ingest_mcp(manifest: MCPManifest) -> List[EvidenceFact]:
    facts = [EvidenceFact(
        kind="mcp_server", payload={"server_id": manifest.server_id},
        source="mcp_manifest",
        evidence=_ev(EvidenceLevel.L3_ARTIFACT,
                    f"mcp:{manifest.server_id}"))]
    for t in manifest.tools:
        facts.append(EvidenceFact(
            kind="mcp_tool", payload=dict(t, server_id=manifest.server_id),
            source="mcp_manifest",
            evidence=_ev(EvidenceLevel.L3_ARTIFACT,
                        f"mcp:{manifest.server_id}:{t.get('name')}")))
    return facts


def ingest_doc_claims(claims: DocClaims,
                      name: str = "design_doc") -> List[EvidenceFact]:
    facts: List[EvidenceFact] = []
    for c in claims.claims:
        facts.append(EvidenceFact(
            kind="doc_claim", payload=dict(c), source=name,
            evidence=Evidence(level=EvidenceLevel.L1_ASSERTION,
                              reference=f"{name}:claim:{c.get('subject')}",
                              detail="user assertion in design document")))
    return facts


def ingest_all(spec: Optional[ArchSpec] = None,
               iac: Optional[IaCConfig] = None,
               manifests: Optional[List[MCPManifest]] = None,
               docs: Optional[DocClaims] = None) -> List[EvidenceFact]:
    """Ingest every supplied artifact into one flat fact list."""
    facts: List[EvidenceFact] = []
    if spec is not None:
        facts.extend(ingest_arch(spec))
    if iac is not None:
        facts.extend(ingest_iac(iac))
    for m in manifests or []:
        facts.extend(ingest_mcp(m))
    if docs is not None:
        facts.extend(ingest_doc_claims(docs))
    return facts
