"""Scenario catalog for the CISO AI Risk Twin.

- worked_example(): the concept's end-to-end demo. The design doc claims
  the support agent is "read-only", but the architecture shows
  POST /holdTransaction; customer PII flows to an external LLM.
- worked_example_fixed(): the same architecture after the fix-and-rerun
  loop: a human-approval node gates the write path and the MCP tool gains
  an input schema.
- simple_chatbot(), rag_assistant(), agentic_platform(): three synthetic
  architectures of increasing complexity for the funnel experiment.
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from .artifacts import (ArchSpec, DocClaims, IaCConfig, MCPManifest,
                        ingest_all)
from .evidence import Evidence, EvidenceLevel
from .twin import Twin, build_twin


def _facts(spec_nodes, spec_edges, iac_resources=(), manifests=(),
           claims=(), purpose="", business_process="",
           regulations=(), owner=""):
    spec = ArchSpec(nodes=spec_nodes, edges=spec_edges)
    iac = IaCConfig(resources=list(iac_resources)) if iac_resources else None
    docs = DocClaims(claims=list(claims)) if claims else None
    facts = ingest_all(spec=spec, iac=iac,
                       manifests=list(manifests), docs=docs)
    return build_twin(facts, purpose=purpose,
                      business_process=business_process,
                      regulations=list(regulations), owner=owner)


def worked_example() -> Twin:
    """Support agent: claims read-only, architecture shows a write."""
    nodes = [
        {"id": "user", "kind": "user", "attrs": {}},
        {"id": "support_agent", "kind": "agent",
         "attrs": {"owner": "support-platform"}},
        {"id": "helpdesk_llm", "kind": "llm",
         "attrs": {"provider": "external-llm-co", "external": True}},
        {"id": "mcp_gateway", "kind": "mcp_server", "attrs": {}},
        {"id": "transaction_api", "kind": "api", "attrs": {}},
        {"id": "customer_db", "kind": "db",
         "attrs": {"data": "pii"}},
        {"id": "legacy_reporting_db", "kind": "db", "attrs": {}},
    ]
    edges = [
        {"src": "user", "dst": "support_agent", "rel": "sends",
         "data": "pii"},
        {"src": "support_agent", "dst": "helpdesk_llm", "rel": "calls",
         "data": "pii"},
        {"src": "support_agent", "dst": "mcp_gateway", "rel": "invokes"},
        {"src": "mcp_gateway", "dst": "transaction_api", "rel": "calls",
         "method": "POST", "path": "/holdTransaction",
         "tool": "holdTransaction"},
        # Diagram-level claim: agent -> transaction API (validated below).
        {"src": "support_agent", "dst": "transaction_api", "rel": "calls",
         "method": "POST", "path": "/holdTransaction"},
        {"src": "support_agent", "dst": "customer_db", "rel": "reads",
         "data": "pii"},
        # No IaC grant exists for this one: unverified by design.
        {"src": "support_agent", "dst": "legacy_reporting_db",
         "rel": "reads"},
    ]
    iac = [
        {"type": "service_principal", "name": "sp-support", "attrs": {}},
        {"type": "role_assignment", "name": "ra-custdb",
         "attrs": {"identity": "sp-support", "scope": "customer_db",
                   "permissions": ["read"]}},
        {"type": "role_assignment", "name": "ra-txn",
         "attrs": {"identity": "sp-support", "scope": "transaction_api",
                   "permissions": ["write"]}},
    ]
    manifests = [MCPManifest(server_id="mcp_gateway", tools=[
        {"name": "holdTransaction", "method": "POST",
         "path": "/holdTransaction"},
        {"name": "getCustomer", "method": "GET", "path": "/customer",
         "input_schema": {"type": "object",
                          "properties": {"id": {"type": "string"}}}},
    ])]
    claims = [
        {"subject": "support_agent", "claim": "read-only",
         "detail": "The agent only reads data; it never changes state."},
        {"subject": "support_agent", "claim": "no external data sharing",
         "detail": "Customer data stays inside the enterprise boundary."},
    ]
    return _facts(nodes, edges, iac, manifests, claims,
                  purpose="Automated customer support for payment holds",
                  business_process="Customer asks for a payment hold; the "
                                   "agent places the hold via the "
                                   "transaction API.",
                  regulations=["GDPR"])


def worked_example_fixed() -> Twin:
    """Worked example after the fix-and-rerun loop.

    Adds a human-approval node gating the write path and an input schema
    on the holdTransaction tool.
    """
    twin = worked_example()
    twin.components["human_approval"] = {"kind": "human_loop",
                                         "attrs": {"sla": "15m"}}
    twin.edges.append({"src": "support_agent", "dst": "human_approval",
                       "rel": "requires_approval"})
    twin.edges.append({"src": "human_approval", "dst": "transaction_api",
                       "rel": "approves", "method": "POST"})
    twin.data_flows.append({"src": "support_agent",
                            "dst": "human_approval",
                            "classification": "unclassified",
                            "write": False})
    twin.data_flows.append({"src": "human_approval",
                            "dst": "transaction_api",
                            "classification": "unclassified",
                            "write": True})
    # The holdTransaction tool gains an input schema in the fix.
    for p in twin.access_paths:
        if "tool:unvalidated-input" in p.permissions:
            p.permissions = [x for x in p.permissions
                             if x != "tool:unvalidated-input"]
            p.evidence.append(Evidence(
                EvidenceLevel.L3_ARTIFACT,
                "mcp:mcp_gateway:holdTransaction:schema",
                "input schema added in fix"))
    # The unverified legacy edge: access revoked in the fix.
    twin.edges = [e for e in twin.edges
                  if not (e["src"] == "support_agent" and
                          e["dst"] == "legacy_reporting_db")]
    twin.access_paths = [p for p in twin.access_paths
                         if not (p.diagram_edge["src"] == "support_agent" and
                                 p.diagram_edge["dst"] ==
                                 "legacy_reporting_db")]
    twin.data_flows = [f for f in twin.data_flows
                       if not (f["src"] == "support_agent" and
                               f["dst"] == "legacy_reporting_db")]
    return twin


def simple_chatbot() -> Twin:
    nodes = [
        {"id": "user", "kind": "user", "attrs": {}},
        {"id": "chat_llm", "kind": "llm",
         "attrs": {"provider": "external-llm-co", "external": True}},
    ]
    edges = [
        {"src": "user", "dst": "chat_llm", "rel": "sends"},
        {"src": "chat_llm", "dst": "user", "rel": "responds"},
    ]
    return _facts(nodes, edges,
                  purpose="General-purpose employee Q&A chatbot",
                  business_process="Employees ask questions; the chatbot "
                                   "answers from the model.",
                  owner="it-helpdesk")


def rag_assistant() -> Twin:
    nodes = [
        {"id": "user", "kind": "user", "attrs": {}},
        {"id": "rag_agent", "kind": "agent", "attrs": {}},
        {"id": "retriever", "kind": "rag",
         "attrs": {"sources": "internal wiki + ticket history"}},
        {"id": "vector_db", "kind": "vector_db", "attrs": {}},
        {"id": "answer_llm", "kind": "llm",
         "attrs": {"provider": "internal-llm", "external": False}},
        {"id": "doc_store", "kind": "db", "attrs": {"data": "internal"}},
    ]
    edges = [
        {"src": "user", "dst": "rag_agent", "rel": "sends"},
        {"src": "rag_agent", "dst": "retriever", "rel": "queries"},
        {"src": "retriever", "dst": "vector_db", "rel": "searches"},
        {"src": "retriever", "dst": "doc_store", "rel": "reads"},
        {"src": "rag_agent", "dst": "answer_llm", "rel": "calls"},
        {"src": "answer_llm", "dst": "user", "rel": "responds"},
    ]
    iac = [
        {"type": "service_principal", "name": "sp-rag", "attrs": {}},
        {"type": "role_assignment", "name": "ra-doc",
         "attrs": {"identity": "sp-rag", "scope": "doc_store",
                   "permissions": ["read"]}},
    ]
    return _facts(nodes, edges, iac,
                  purpose="Internal support copilot with retrieval",
                  business_process="Agent retrieves internal docs and "
                                   "drafts answers.",
                  owner="support-platform")


def agentic_platform() -> Twin:
    """Complex: close to the worked example, plus RAG and vector PII."""
    twin = worked_example()
    twin.components["retriever"] = {
        "kind": "rag", "attrs": {"sources": "ticket history",
                                 "untrusted_source": False}}
    twin.components["vector_db"] = {
        "kind": "vector_db", "attrs": {"stores_pii": True}}
    twin.edges.append({"src": "support_agent", "dst": "retriever",
                       "rel": "queries"})
    twin.edges.append({"src": "retriever", "dst": "vector_db",
                       "rel": "searches"})
    twin.data_flows.append({"src": "support_agent", "dst": "retriever",
                            "classification": "internal", "write": False})
    twin.data_flows.append({"src": "retriever", "dst": "vector_db",
                            "classification": "pii", "write": False})
    twin.purpose = ("Agentic support platform with retrieval and "
                    "payment-hold actions")
    return twin


def vendor_evidence_pack(level: EvidenceLevel) -> Dict[str, Evidence]:
    """A vendor evidence pack (DPA + SOC2 + retention terms) at a level."""
    return {
        "vendor_dpa": Evidence(level, "vendor:external-llm-co:DPA",
                               "data processing agreement"),
        "soc2": Evidence(level, "vendor:external-llm-co:SOC2",
                         "SOC 2 Type II report"),
        "retention_terms": Evidence(level, "vendor:external-llm-co:retention",
                                    "data retention schedule"),
    }
