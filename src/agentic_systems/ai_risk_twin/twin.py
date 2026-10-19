"""The AI Use-Case Twin and its three-level architecture parser.

The twin is the canonical, structured object the whole assessment reasons
over:

- purpose & business process
- AI models & providers
- agents, tools & MCP servers
- data flows & classifications
- identities, permissions & trust boundaries
- external dependencies & regulations

Parsing happens in three levels:

- L1 components: the nodes (LLMs, agents, RAG pipelines, vector DBs,
  APIs, databases, human-in-the-loop interfaces).
- L2 relationships: the edges (invokes / calls / accesses), classified
  into control flow vs data flow and read vs write operations.
- L3 security semantics: identity and permission overlays. Crucially, the
  parser does NOT trust the diagram: a diagram edge ``agent -> database``
  is resolved against IaC evidence into the actual access path
  (e.g. agent -> MCP server -> service principal -> database). An edge
  that cannot be resolved to a real path is flagged as unverified.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from .artifacts import EvidenceFact
from .evidence import Evidence, EvidenceLevel


WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass
class AccessPath:
    """A resolved, real access path for one diagram edge."""
    diagram_edge: Dict[str, Any]
    hops: List[str]                    # resolved node ids in order
    identity: Optional[str]            # service principal / identity used
    permissions: List[str]             # granted permissions on the target
    crosses_trust_boundary: bool
    verified: bool                     # False when no real path was found
    evidence: List[Evidence] = field(default_factory=list)


@dataclass
class Twin:
    purpose: str = ""
    business_process: str = ""
    models: List[Dict[str, Any]] = field(default_factory=list)
    agents: List[str] = field(default_factory=list)
    mcp_servers: List[str] = field(default_factory=list)
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    access_paths: List[AccessPath] = field(default_factory=list)
    data_flows: List[Dict[str, Any]] = field(default_factory=list)
    doc_claims: List[Dict[str, Any]] = field(default_factory=list)
    regulations: List[str] = field(default_factory=list)
    owner: str = ""
    evidence: List[Evidence] = field(default_factory=list)

    # -- L1/L2 convenience predicates used by rule triggers ----------------
    def kinds(self) -> Set[str]:
        return {c.get("kind") for c in self.components.values()}

    def has_kind(self, kind: str) -> bool:
        return kind in self.kinds()

    def write_edges(self) -> List[Dict[str, Any]]:
        return [e for e in self.edges if is_write_edge(e)]

    def read_edges(self) -> List[Dict[str, Any]]:
        return [e for e in self.edges if not is_write_edge(e)]

    def external_deps(self) -> List[str]:
        return [cid for cid, c in self.components.items()
                if c.get("attrs", {}).get("external")]

    def pii_flows(self) -> List[Dict[str, Any]]:
        return [f for f in self.data_flows
                if f.get("classification") in ("pii", "confidential",
                                               "restricted")]

    def llm_nodes(self) -> List[str]:
        return [cid for cid, c in self.components.items()
                if c.get("kind") == "llm"]

    def unverified_paths(self) -> List[AccessPath]:
        return [p for p in self.access_paths if not p.verified]


def is_write_edge(edge: Dict[str, Any]) -> bool:
    """An edge is state-changing only if it declares a write method or an
    explicit write relationship. Delegation verbs (invokes/calls/sends)
    are control flow, not writes."""
    method = (edge.get("method") or "").upper()
    if method in WRITE_METHODS:
        return True
    if method in ("GET", "HEAD", "OPTIONS"):
        return False
    return edge.get("rel") == "writes"


def build_twin(facts: List[EvidenceFact],
               purpose: str = "",
               business_process: str = "",
               regulations: Optional[List[str]] = None,
               owner: str = "") -> Twin:
    """Three-level parse of ingested facts into an AI Use-Case Twin."""
    twin = Twin(purpose=purpose, business_process=business_process,
                regulations=regulations or [], owner=owner)

    nodes = [f for f in facts if f.kind == "node"]
    edges = [f for f in facts if f.kind == "edge"]
    identities = [f for f in facts if f.kind == "identity"]
    role_assignments = [f for f in facts if f.kind == "role_assignment"]
    mcp_servers = [f for f in facts if f.kind == "mcp_server"]
    mcp_tools = [f for f in facts if f.kind == "mcp_tool"]
    doc_claims = [f for f in facts if f.kind == "doc_claim"]

    # ---- Level 1: components -------------------------------------------
    for f in nodes:
        p = f.payload
        twin.components[p["id"]] = {"kind": p.get("kind", "unknown"),
                                    "attrs": p.get("attrs", {})}
        twin.evidence.append(f.evidence)
    for f in mcp_servers:
        sid = f.payload["server_id"]
        twin.mcp_servers.append(sid)
        if sid not in twin.components:
            twin.components[sid] = {"kind": "mcp_server", "attrs": {}}
    for f in nodes:
        p = f.payload
        if p.get("kind") == "llm":
            twin.models.append({"node": p["id"],
                                "provider": p.get("attrs", {}).get("provider",
                                                                  "unknown"),
                                "external": bool(p.get("attrs", {}).get(
                                    "external"))})
        if p.get("kind") == "agent":
            twin.agents.append(p["id"])

    # ---- Level 2: relationships ----------------------------------------
    for f in edges:
        twin.edges.append(dict(f.payload))
        twin.evidence.append(f.evidence)
        p = f.payload
        data = p.get("data") or p.get("attrs", {}).get("data")
        twin.data_flows.append({
            "src": p["src"], "dst": p["dst"],
            "classification": data or "unclassified",
            "write": is_write_edge(p),
        })
    for f in doc_claims:
        twin.doc_claims.append(dict(f.payload))

    # ---- Level 3: security semantics -----------------------------------
    # Build identity -> permissions index from IaC.
    perms: Dict[str, List[str]] = {}
    id_for: Dict[str, str] = {}
    for f in identities:
        p = f.payload
        id_for[p.get("name", "")] = p.get("name", "")
    for f in role_assignments:
        p = f.payload
        ident = p.get("attrs", {}).get("identity") or p.get("identity")
        scope = p.get("attrs", {}).get("scope") or p.get("scope")
        grant = p.get("attrs", {}).get("permissions") or p.get(
            "permissions") or []
        perms.setdefault(f"{ident}@{scope}", grant if isinstance(
            grant, list) else [grant])
        twin.evidence.append(f.evidence)

    tool_index = {(t.payload.get("server_id"), t.payload.get("name")): t
                  for t in mcp_tools}

    for e in twin.edges:
        twin.access_paths.append(
            _resolve_path(e, twin.components, perms, tool_index))
    return twin


def _resolve_path(edge: Dict[str, Any],
                  components: Dict[str, Dict[str, Any]],
                  perms: Dict[str, List[str]],
                  tool_index: Dict[Tuple[str, str], EvidenceFact]
                  ) -> AccessPath:
    """Resolve a diagram edge into the real access path.

    Never trusts the diagram: the declared ``src -> dst`` hop is expanded
    through intermediate MCP servers, and permissions are looked up from
    IaC evidence. If no identity/permission evidence exists for the hop,
    the path is marked unverified instead of assumed safe.
    """
    src, dst = edge["src"], edge["dst"]
    hops = [src]
    identity: Optional[str] = None
    permissions: List[str] = []
    evidence: List[Evidence] = []
    verified = True

    dst_kind = components.get(dst, {}).get("kind")

    def _mcp_match():
        for (srv, tname), tf in tool_index.items():
            if edge.get("tool") and tname == edge["tool"]:
                return srv, tf
            epath, tpath = edge.get("path"), tf.payload.get("path")
            if epath and tpath and epath.rstrip("/") == tpath.rstrip("/"):
                return srv, tf
        return None

    def _tool_evidence(tf: EvidenceFact):
        evidence.append(tf.evidence)
        if not tf.payload.get("input_schema"):
            permissions.append("tool:unvalidated-input")

    if dst_kind == "mcp_server":
        hops.append(dst)
    elif dst_kind in ("db", "api", "external_api"):
        direct = [k for k in perms if k.endswith(f"@{dst}")]
        match = _mcp_match()
        if match and not direct:
            # No direct grant: the real path goes through the MCP server
            # evidenced by the tool manifest.
            srv, tf = match
            hops.extend([srv, dst])
            _tool_evidence(tf)
        elif direct:
            key = direct[0]
            identity = key.split("@")[0]
            permissions = perms[key]
            evidence.append(Evidence(
                EvidenceLevel.L4_ENTERPRISE, f"iac:role:{key}",
                "role assignment resolved from IaC"))
            hops.append(dst)
            if match:
                _tool_evidence(match[1])
        else:
            # Diagram claims access, but no identity grant and no tool
            # evidence exists: do not assume it is safe.
            hops.append(dst)
            verified = False
    else:
        hops.append(dst)

    src_ext = components.get(src, {}).get("attrs", {}).get("external",
                                                           False)
    dst_ext = components.get(dst, {}).get("attrs", {}).get("external",
                                                           False)
    crosses = bool(src_ext) != bool(dst_ext)
    return AccessPath(diagram_edge=edge, hops=hops, identity=identity,
                      permissions=permissions,
                      crosses_trust_boundary=crosses, verified=verified,
                      evidence=evidence)
