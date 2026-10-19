"""Knowledge base: the rule engine behind the CISO AI Risk Twin.

Rules encode regulatory and framework references (NIST AI RMF, OWASP Top
10 for LLM Applications, OWASP Top 10 for Agentic AI, EU AI Act, GDPR /
privacy law, and configurable internal policies). Each rule maps a twin
pattern (its trigger) to a generated finding.

The same module hosts the 125-question assessment bank. Questions carry
trigger predicates over the twin, optional auto-answer extractors (for
facts already present in parsed artifacts), and the evidence kind that
would resolve them. The funnel (funnel.py) uses these to shrink the
assessment dynamically.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from .twin import Twin

HIGH_RISK_KEYWORDS = ("credit", "hiring", "lending", "insurance pricing",
                      "law enforcement", "recruiting", "loan")


# ---------------------------------------------------------------------------
# Trigger predicates over the twin
# ---------------------------------------------------------------------------

def _always(t: Twin) -> bool:
    return True


def _has_agent(t: Twin) -> bool:
    return t.has_kind("agent")


def _has_rag(t: Twin) -> bool:
    return t.has_kind("rag")


def _has_llm(t: Twin) -> bool:
    return bool(t.llm_nodes())


def _has_mcp(t: Twin) -> bool:
    return bool(t.mcp_servers)


def _has_vector_db(t: Twin) -> bool:
    return t.has_kind("vector_db")


def _has_external(t: Twin) -> bool:
    return bool(t.external_deps())


def _has_write(t: Twin) -> bool:
    return bool(t.write_edges())


def _has_pii(t: Twin) -> bool:
    return bool(t.pii_flows())


def _has_db(t: Twin) -> bool:
    return t.has_kind("db")


def _has_user(t: Twin) -> bool:
    return t.has_kind("user")


def _high_risk_use(t: Twin) -> bool:
    text = f"{t.purpose} {t.business_process}".lower()
    return any(k in text for k in HIGH_RISK_KEYWORDS)


def _has_iac(t: Twin) -> bool:
    return any(p.identity for p in t.access_paths)


def _agent_write(t: Twin) -> bool:
    return _has_agent(t) and any(
        e.get("src") in t.agents for e in t.write_edges())


def _external_pii(t: Twin) -> bool:
    ext = set(t.external_deps())
    return any(f["dst"] in ext for f in t.pii_flows())


def _iac_write(t: Twin) -> bool:
    return _has_iac(t) and _has_write(t)


def _rag_pii(t: Twin) -> bool:
    return _has_rag(t) and _has_pii(t)


def _llm_pii(t: Twin) -> bool:
    llms = set(t.llm_nodes())
    return any(f["dst"] in llms for f in t.pii_flows())


def _has_unverified(t: Twin) -> bool:
    return bool(t.unverified_paths())


def _has_unvalidated_tool(t: Twin) -> bool:
    for p in t.access_paths:
        if "tool:unvalidated-input" not in p.permissions:
            continue
        if any(ev.reference.startswith("mcp:") for ev in p.evidence):
            return True
    return False


def _agent_no_identity(t: Twin) -> bool:
    return any(not any(p.identity and a in p.hops
                       for p in t.access_paths)
               for a in t.agents)


def _rag_untrusted(t: Twin) -> bool:
    return any(v.get("kind") == "rag" and
               v.get("attrs", {}).get("untrusted_source")
               for v in t.components.values())


def _vector_db_pii(t: Twin) -> bool:
    return any(v.get("kind") == "vector_db" and
               v.get("attrs", {}).get("stores_pii")
               for v in t.components.values())


TRIGGERS: Dict[str, Callable[[Twin], bool]] = {
    "always": _always,
    "has_agent": _has_agent,
    "has_rag": _has_rag,
    "has_llm": _has_llm,
    "has_mcp": _has_mcp,
    "has_vector_db": _has_vector_db,
    "has_external": _has_external,
    "has_write": _has_write,
    "has_pii": _has_pii,
    "has_db": _has_db,
    "has_user": _has_user,
    "high_risk_use": _high_risk_use,
    "has_iac": _has_iac,
    "agent_write": _agent_write,
    "external_pii": _external_pii,
    "iac_write": _iac_write,
    "rag_pii": _rag_pii,
    "llm_pii": _llm_pii,
    "has_unverified": _has_unverified,
    "has_unvalidated_tool": _has_unvalidated_tool,
    "agent_no_identity": _agent_no_identity,
    "rag_untrusted": _rag_untrusted,
    "vector_db_pii": _vector_db_pii,
}


# ---------------------------------------------------------------------------
# Auto-answer extractors (facts already present in parsed artifacts)
# ---------------------------------------------------------------------------

def _auto_agents(t: Twin) -> Optional[str]:
    return ", ".join(t.agents) if t.agents else None


def _auto_models(t: Twin) -> Optional[str]:
    if not t.models:
        return None
    return ", ".join(f"{m['node']} ({m['provider']})" for m in t.models)


def _auto_mcp(t: Twin) -> Optional[str]:
    return ", ".join(t.mcp_servers) if t.mcp_servers else None


def _auto_write_ops(t: Twin) -> Optional[str]:
    w = t.write_edges()
    if not w:
        return None
    return "; ".join(f"{e['src']}->{e['dst']} "
                     f"({e.get('method', e.get('rel'))})" for e in w)


def _auto_externals(t: Twin) -> Optional[str]:
    ext = t.external_deps()
    return ", ".join(ext) if ext else None


def _auto_pii_flows(t: Twin) -> Optional[str]:
    f = t.pii_flows()
    if not f:
        return None
    return "; ".join(f"{x['src']}->{x['dst']} [{x['classification']}]"
                     for x in f)


def _auto_identities(t: Twin) -> Optional[str]:
    ids = sorted({p.identity for p in t.access_paths if p.identity})
    return ", ".join(ids) if ids else None


def _auto_purpose(t: Twin) -> Optional[str]:
    return t.purpose or None


def _auto_regulations(t: Twin) -> Optional[str]:
    return ", ".join(t.regulations) if t.regulations else None


def _auto_rag_sources(t: Twin) -> Optional[str]:
    rags = [c for c, v in t.components.items() if v.get("kind") == "rag"]
    srcs = []
    for r in rags:
        attrs = t.components[r].get("attrs", {})
        s = attrs.get("sources")
        srcs.append(f"{r}: {s}" if s else r)
    return "; ".join(srcs) if srcs else None


def _auto_vector_dbs(t: Twin) -> Optional[str]:
    v = [c for c, v in t.components.items()
         if v.get("kind") == "vector_db"]
    return ", ".join(v) if v else None


def _auto_owner(t: Twin) -> Optional[str]:
    return t.owner or None


def _auto_hitl(t: Twin) -> Optional[str]:
    h = [c for c, v in t.components.items()
         if v.get("kind") == "human_loop"]
    return ", ".join(h) if h else None


AUTO: Dict[str, Callable[[Twin], Optional[str]]] = {
    "auto_agents": _auto_agents,
    "auto_models": _auto_models,
    "auto_mcp": _auto_mcp,
    "auto_write_ops": _auto_write_ops,
    "auto_externals": _auto_externals,
    "auto_pii_flows": _auto_pii_flows,
    "auto_identities": _auto_identities,
    "auto_purpose": _auto_purpose,
    "auto_regulations": _auto_regulations,
    "auto_rag_sources": _auto_rag_sources,
    "auto_vector_dbs": _auto_vector_dbs,
    "auto_owner": _auto_owner,
    "auto_hitl": _auto_hitl,
}


# ---------------------------------------------------------------------------
# The 125-question assessment bank
# (id, text, category, trigger, auto, evidence_kind)
# ---------------------------------------------------------------------------

@dataclass
class Question:
    qid: str
    text: str
    category: str
    trigger: str
    auto: Optional[str] = None
    evidence_kind: Optional[str] = None


def _q(qid, text, cat, trigger, auto=None, ev=None) -> Question:
    return Question(qid, text, cat, trigger, auto, ev)


def build_question_bank() -> List[Question]:
    q: List[Question] = []
    # -- agentic (12) --
    q += [
        _q("AG-Q01", "Which agents exist and what is each agent's declared purpose?",
           "agentic", "has_agent", "auto_agents"),
        _q("AG-Q02", "What tools can each agent invoke, and where is the tool manifest?",
           "agentic", "has_agent", "auto_mcp", "tool_manifest"),
        _q("AG-Q03", "Is there a human approval step before state-changing agent actions?",
           "agentic", "agent_write", "auto_hitl"),
        _q("AG-Q04", "What is the maximum blast radius of a compromised agent?",
           "agentic", "agent_write", None, "threat_model"),
        _q("AG-Q05", "Are agent-to-agent delegations bounded and logged?",
           "agentic", "has_agent"),
        _q("AG-Q06", "Can the agent modify its own instructions, tools, or permissions?",
           "agentic", "has_agent"),
        _q("AG-Q07", "What identity does each agent use to access downstream systems?",
           "agentic", "has_agent", "auto_identities"),
        _q("AG-Q08", "Are agent actions logged immutably for forensics?",
           "agentic", "has_agent", None, "soc2"),
        _q("AG-Q09", "What happens when the agent's primary tool is unavailable?",
           "agentic", "has_agent", None, "incident_plan"),
        _q("AG-Q10", "Has the agent been red-teamed for prompt injection and tool abuse?",
           "agentic", "has_agent", None, "pen_test"),
        _q("AG-Q11", "Are there rate limits on agent-initiated state-changing actions?",
           "agentic", "agent_write"),
        _q("AG-Q12", "Who owns each agent operationally (on-call, runbooks)?",
           "agentic", "has_agent", "auto_owner"),
    ]
    # -- third party (12) --
    q += [
        _q("TP-Q01", "Which external model providers and APIs are used?",
           "third_party", "has_external", "auto_externals"),
        _q("TP-Q02", "Provide the vendor DPA for each external provider.",
           "third_party", "has_external", None, "vendor_dpa"),
        _q("TP-Q03", "Provide SOC 2 reports for external API vendors.",
           "third_party", "has_external", None, "soc2"),
        _q("TP-Q04", "Is customer data sent to external providers?",
           "third_party", "has_external", "auto_pii_flows"),
        _q("TP-Q05", "What data does the provider retain, and for how long?",
           "third_party", "has_external", None, "retention_terms"),
        _q("TP-Q06", "Is provider-side training on customer data contractually excluded?",
           "third_party", "has_external", None, "vendor_dpa"),
        _q("TP-Q07", "What are the provider's uptime SLAs and error budgets?",
           "third_party", "has_external", None, "soc2"),
        _q("TP-Q08", "Is there a fallback if the external provider is unavailable?",
           "third_party", "has_external", None, "incident_plan"),
        _q("TP-Q09", "Are external API and model versions pinned?",
           "third_party", "has_external"),
        _q("TP-Q10", "What PII masking is applied before external egress?",
           "third_party", "external_pii"),
        _q("TP-Q11", "Which subprocessors does each vendor use?",
           "third_party", "has_external", None, "vendor_dpa"),
        _q("TP-Q12", "What is the exit strategy if a vendor relationship ends?",
           "third_party", "has_external"),
    ]
    # -- IAM (12) --
    q += [
        _q("IM-Q01", "Which identities do the AI components use?",
           "iam", "has_iac", "auto_identities"),
        _q("IM-Q02", "Are granted permissions least-privilege for each component?",
           "iam", "has_iac"),
        _q("IM-Q03", "Is MFA enforced for human access to AI infrastructure?",
           "iam", "always", None, "soc2"),
        _q("IM-Q04", "Are machine identities rotated on a schedule?",
           "iam", "has_iac"),
        _q("IM-Q05", "Are there standing (non-expiring) write permissions?",
           "iam", "iac_write"),
        _q("IM-Q06", "Is privileged access logged to a SIEM?",
           "iam", "always", None, "soc2"),
        _q("IM-Q07", "Who approves permission grants for AI identities?",
           "iam", "has_iac"),
        _q("IM-Q08", "Are elevated permissions time-bound (just-in-time)?",
           "iam", "has_iac"),
        _q("IM-Q09", "Are training and serving identities separated?",
           "iam", "has_llm"),
        _q("IM-Q10", "Is each service principal scoped to a single component?",
           "iam", "has_iac"),
        _q("IM-Q11", "What is the break-glass procedure for AI identities?",
           "iam", "has_iac", None, "incident_plan"),
        _q("IM-Q12", "Are dormant AI identities reviewed and revoked?",
           "iam", "has_iac", None, "soc2"),
    ]
    # -- RAG (10) --
    q += [
        _q("RG-Q01", "What sources feed the RAG pipeline?",
           "rag", "has_rag", "auto_rag_sources"),
        _q("RG-Q02", "Are RAG sources trusted and integrity-checked?",
           "rag", "has_rag"),
        _q("RG-Q03", "What poisoning controls protect the retrieval corpus?",
           "rag", "has_rag", None, "threat_model"),
        _q("RG-Q04", "Is retrieved content validated before being used in prompts?",
           "rag", "has_rag"),
        _q("RG-Q05", "Can end users inject content into the retrieval corpus?",
           "rag", "has_rag", None, "threat_model"),
        _q("RG-Q06", "Is PII filtered from retrieved chunks?",
           "rag", "rag_pii"),
        _q("RG-Q07", "Is the embedding model version pinned and recorded?",
           "rag", "has_rag"),
        _q("RG-Q08", "Is the vector database access-controlled?",
           "rag", "has_vector_db"),
        _q("RG-Q09", "Are chunking strategy and overlap documented?",
           "rag", "has_rag", None, "eval_report"),
        _q("RG-Q10", "Is retrieval relevance evaluated on a held-out set?",
           "rag", "has_rag", None, "eval_report"),
    ]
    # -- LLM security (12) --
    q += [
        _q("LS-Q01", "Which models and versions are deployed?",
           "llm_security", "has_llm", "auto_models"),
        _q("LS-Q02", "Is untrusted input validated before entering prompts?",
           "llm_security", "has_llm", None, "threat_model"),
        _q("LS-Q03", "Is model output validated before downstream use?",
           "llm_security", "has_llm", None, "threat_model"),
        _q("LS-Q04", "Has prompt-injection testing been performed?",
           "llm_security", "has_llm", None, "pen_test"),
        _q("LS-Q05", "Are system prompts protected from extraction?",
           "llm_security", "has_llm", None, "pen_test"),
        _q("LS-Q06", "Are model inputs/outputs logged for audit?",
           "llm_security", "has_llm", None, "soc2"),
        _q("LS-Q07", "Is jailbreak/misuse monitored in production?",
           "llm_security", "has_llm", None, "incident_plan"),
        _q("LS-Q08", "What is the provenance of fine-tuning data?",
           "llm_security", "has_llm"),
        _q("LS-Q09", "Are model-theft protections (rate limits, quotas) in place?",
           "llm_security", "has_llm", None, "threat_model"),
        _q("LS-Q10", "Is there a deny-list for disallowed content?",
           "llm_security", "has_llm"),
        _q("LS-Q11", "Are model artifacts signed and integrity-checked?",
           "llm_security", "has_llm", None, "soc2"),
        _q("LS-Q12", "Is there a fallback model if the primary fails?",
           "llm_security", "has_llm", None, "incident_plan"),
    ]
    # -- data privacy (12) --
    q += [
        _q("DP-Q01", "What data classifications flow through the system?",
           "data_privacy", "always", "auto_pii_flows"),
        _q("DP-Q02", "In which regions does data reside and get processed?",
           "data_privacy", "has_external", None, "vendor_dpa"),
        _q("DP-Q03", "How is the right to erasure honored for RAG/training data?",
           "data_privacy", "has_pii"),
        _q("DP-Q04", "What are the data retention periods per store?",
           "data_privacy", "has_db", None, "retention_terms"),
        _q("DP-Q05", "Is PII minimized in prompts sent to models?",
           "data_privacy", "llm_pii"),
        _q("DP-Q06", "What is the lawful basis for processing personal data?",
           "data_privacy", "has_pii"),
        _q("DP-Q07", "Has a Data Protection Impact Assessment been completed?",
           "data_privacy", "has_pii"),
        _q("DP-Q08", "What cross-border transfer mechanism is used?",
           "data_privacy", "external_pii", None, "vendor_dpa"),
        _q("DP-Q09", "Which anonymization techniques are applied, and validated how?",
           "data_privacy", "has_pii"),
        _q("DP-Q10", "Who is the data controller for this processing?",
           "data_privacy", "has_pii"),
        _q("DP-Q11", "What is the breach notification procedure?",
           "data_privacy", "has_pii", None, "incident_plan"),
        _q("DP-Q12", "Are backups encrypted and access-controlled?",
           "data_privacy", "has_db", None, "soc2"),
    ]
    # -- model risk (10) --
    q += [
        _q("MR-Q01", "What are the model's performance metrics and thresholds?",
           "model_risk", "has_llm", None, "eval_report"),
        _q("MR-Q02", "Are evaluation datasets documented and versioned?",
           "model_risk", "has_llm", None, "eval_report"),
        _q("MR-Q03", "Has bias/fairness testing been performed?",
           "model_risk", "has_llm", None, "eval_report"),
        _q("MR-Q04", "Is model drift monitored in production?",
           "model_risk", "has_llm", None, "incident_plan"),
        _q("MR-Q05", "Are model cards published for deployed models?",
           "model_risk", "has_llm", None, "eval_report"),
        _q("MR-Q06", "Were challenger models benchmarked before selection?",
           "model_risk", "has_llm", None, "eval_report"),
        _q("MR-Q07", "What is the rollback procedure for a bad model release?",
           "model_risk", "has_llm", None, "incident_plan"),
        _q("MR-Q08", "Is there human evaluation of model outputs on a cadence?",
           "model_risk", "has_llm", None, "eval_report"),
        _q("MR-Q09", "Are confidence thresholds defined for automated actions?",
           "model_risk", "has_llm"),
        _q("MR-Q10", "Has adversarial robustness been tested?",
           "model_risk", "has_llm", None, "pen_test"),
    ]
    # -- transparency (8) --
    q += [
        _q("TR-Q01", "Is AI use disclosed to end users?",
           "transparency", "has_user"),
        _q("TR-Q02", "Are AI-generated outputs labeled as such?",
           "transparency", "has_user"),
        _q("TR-Q03", "Can affected users obtain an explanation of automated decisions?",
           "transparency", "has_pii"),
        _q("TR-Q04", "Are model limitations communicated to users?",
           "transparency", "has_user"),
        _q("TR-Q05", "Is generated content watermarked or traceable?",
           "transparency", "has_llm"),
        _q("TR-Q06", "Is there an audit trail of AI-influenced decisions?",
           "transparency", "has_agent", None, "soc2"),
        _q("TR-Q07", "Were transparency notices reviewed by legal?",
           "transparency", "has_user"),
        _q("TR-Q08", "Can users opt out of AI processing?",
           "transparency", "has_pii"),
    ]
    # -- human oversight (10) --
    q += [
        _q("HO-Q01", "Which decisions require human approval before execution?",
           "human_oversight", "has_agent"),
        _q("HO-Q02", "Which human-in-the-loop interfaces exist?",
           "human_oversight", "has_agent", "auto_hitl"),
        _q("HO-Q03", "Can a human override an AI decision, and how?",
           "human_oversight", "has_agent"),
        _q("HO-Q04", "Is the review queue staffed for peak load?",
           "human_oversight", "agent_write"),
        _q("HO-Q05", "Are reviewer qualifications defined for high-risk decisions?",
           "human_oversight", "high_risk_use"),
        _q("HO-Q06", "Are there time limits on human review steps?",
           "human_oversight", "agent_write"),
        _q("HO-Q07", "What happens if no reviewer is available?",
           "human_oversight", "agent_write", None, "incident_plan"),
        _q("HO-Q08", "Is reviewer fatigue / automation bias monitored?",
           "human_oversight", "high_risk_use"),
        _q("HO-Q09", "Is there an appeal process for affected users?",
           "human_oversight", "has_pii"),
        _q("HO-Q10", "Are human overrides logged immutably?",
           "human_oversight", "has_agent", None, "soc2"),
    ]
    # -- supply chain (8) --
    q += [
        _q("SC-Q01", "Is there an SBOM covering AI components?",
           "supply_chain", "always", None, "soc2"),
        _q("SC-Q02", "Are third-party libraries scanned for vulnerabilities?",
           "supply_chain", "always", None, "pen_test"),
        _q("SC-Q03", "Is model provenance verified (signed artifacts)?",
           "supply_chain", "has_llm", None, "soc2"),
        _q("SC-Q04", "Are all dependencies version-pinned?",
           "supply_chain", "always"),
        _q("SC-Q05", "What is the response plan for a compromised dependency?",
           "supply_chain", "always", None, "incident_plan"),
        _q("SC-Q06", "Is OSS license compliance checked?",
           "supply_chain", "always"),
        _q("SC-Q07", "Are vendor security assessments current?",
           "supply_chain", "has_external", None, "soc2"),
        _q("SC-Q08", "Is hardware/firmware supply chain in scope?",
           "supply_chain", "always"),
    ]
    # -- incident response (8) --
    q += [
        _q("IR-Q01", "Does an AI-specific incident response plan exist?",
           "incident_response", "always", None, "incident_plan"),
        _q("IR-Q02", "How is model misbehavior detected in production?",
           "incident_response", "has_llm", None, "incident_plan"),
        _q("IR-Q03", "Is there a kill switch for AI components?",
           "incident_response", "has_agent", None, "incident_plan"),
        _q("IR-Q04", "Is forensic data retained after AI incidents?",
           "incident_response", "always", None, "soc2"),
        _q("IR-Q05", "Were past AI incidents reviewed for lessons learned?",
           "incident_response", "always"),
        _q("IR-Q06", "Have tabletop exercises covered AI failure modes?",
           "incident_response", "always", None, "incident_plan"),
        _q("IR-Q07", "Is there a communication plan for AI failures?",
           "incident_response", "has_user", None, "incident_plan"),
        _q("IR-Q08", "Are regulatory breach-reporting duties defined?",
           "incident_response", "has_pii", None, "incident_plan"),
    ]
    # -- governance (11) --
    q += [
        _q("GV-Q01", "Who is the accountable owner of this AI use case?",
           "governance", "always", "auto_owner"),
        _q("GV-Q02", "Has an AI policy been approved at board level?",
           "governance", "always"),
        _q("GV-Q03", "Is the organizational risk appetite for AI defined?",
           "governance", "always"),
        _q("GV-Q04", "Is this use case recorded in the AI inventory?",
           "governance", "always"),
        _q("GV-Q05", "Has a conformity assessment been done for high-risk AI?",
           "governance", "high_risk_use"),
        _q("GV-Q06", "Are AI systems subject to internal audit?",
           "governance", "always", None, "soc2"),
        _q("GV-Q07", "Are AI operators trained on failure modes and limits?",
           "governance", "has_agent"),
        _q("GV-Q08", "Are third-party AI risk assessments refreshed periodically?",
           "governance", "has_external", None, "soc2"),
        _q("GV-Q09", "What is the model decommissioning procedure?",
           "governance", "has_llm"),
        _q("GV-Q10", "Was an ethics review performed for this use case?",
           "governance", "high_risk_use"),
        _q("GV-Q11", "How are regulatory changes tracked against this system?",
           "governance", "always"),
    ]
    assert len(q) == 125, f"bank must hold 125 questions, got {len(q)}"
    return q


# ---------------------------------------------------------------------------
# Finding rules: trigger patterns -> generated findings
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    rid: str
    source: str
    title: str
    severity: str              # critical | high | medium | low
    kind: str                  # design | information
    trigger: str               # key into TRIGGERS
    targets: Callable[[Twin], List[str]]
    observation: Callable[[Twin], str]
    risk: Callable[[Twin], str]        # concern (design) or unknown (info)
    remedy: Callable[[Twin], str]      # required action (design) or artifact (info)
    control_present: Callable[[Twin], bool] = field(
        default=lambda t: False)


def _targets_write(t: Twin) -> List[str]:
    return [f"{e['src']}->{e['dst']}" for e in t.write_edges()]


def _targets_agents(t: Twin) -> List[str]:
    return list(t.agents)


def _targets_external(t: Twin) -> List[str]:
    return t.external_deps()


def _targets_unverified(t: Twin) -> List[str]:
    return [f"{p.diagram_edge['src']}->{p.diagram_edge['dst']}"
            for p in t.unverified_paths()]


def _targets_mcp_tools_no_schema(t: Twin) -> List[str]:
    out = []
    for p in t.access_paths:
        for ev in p.evidence:
            if ev.reference.startswith("mcp:") and \
                    "tool:unvalidated-input" in p.permissions:
                out.append(ev.reference)
    return sorted(set(out))


def build_rules() -> List[Rule]:
    R: List[Rule] = []

    def rule(rid, source, title, severity, kind, trigger, targets,
             observation, risk, remedy, control_present=lambda t: False):
        R.append(Rule(rid, source, title, severity, kind, trigger,
                      targets, observation, risk, remedy, control_present))

    # -- Agentic --
    rule("AG-01", "OWASP Agentic AI #1", "Excessive agency",
         "critical", "design", "agent_write",
         _targets_write,
         lambda t: ("Agent(s) " + ", ".join(t.agents) +
                    " can invoke state-changing operations: " +
                    "; ".join(_targets_write(t))),
         lambda t: ("A model-driven component can initiate state changes "
                    "without a human in the loop; compromise or "
                    "mis-instruction leads directly to external effects."),
         lambda t: ("Introduce a human-approval node on every write path "
                    "or enforce strict transaction limits with dual "
                    "control."),
         control_present=lambda t: any(
             v.get("kind") == "human_loop" for v in t.components.values()))
    rule("AG-02", "OWASP Agentic AI", "Tool poisoning via unvalidated input",
         "high", "design", "has_unvalidated_tool",
         _targets_mcp_tools_no_schema,
         lambda t: ("MCP tool(s) without input validation schema: " +
                    ", ".join(_targets_mcp_tools_no_schema(t))),
         lambda t: ("An attacker who can influence tool inputs (directly "
                    "or via prompt injection) can smuggle malicious "
                    "payloads into downstream systems."),
         lambda t: ("Add strict input schemas to every MCP tool and "
                    "validate at the gateway."))
    rule("AG-03", "OWASP Agentic AI", "Agent identity not evidenced",
         "high", "information", "agent_no_identity",
         lambda t: [a for a in t.agents
                    if not any(p.identity and a in p.hops
                               for p in t.access_paths)],
         lambda t: "Agent actions cannot be attributed to a machine identity.",
         lambda t: ("Unknown: which service principal the agent acts as, "
                    "and whether its actions are attributable."),
         lambda t: ("Provide the Entra ID / IAM record binding the agent "
                    "to a service principal (L4)."))
    rule("AG-04", "NIST AI RMF (Manage)", "Unbounded agent delegation",
         "medium", "design", "has_agent", _targets_agents,
         lambda t: "No delegation depth cap is declared for agent(s).",
         lambda t: ("Recursive delegation can escape oversight and "
                    "multiply blast radius."),
         lambda t: "Declare and enforce a max delegation depth per agent.")

    # -- Third party --
    rule("TP-01", "Internal TPRM policy", "Missing vendor DPA / SOC 2",
         "high", "information", "has_external", _targets_external,
         lambda t: ("External dependencies without vendor evidence: " +
                    ", ".join(_targets_external(t))),
         lambda t: ("Unknown: data processing terms, retention, and "
                    "subprocessors for external components."),
         lambda t: ("Upload vendor DPA and SOC 2 report (L2) for each "
                    "external dependency."))
    rule("TP-02", "GDPR", "Data residency for external processing",
         "high", "information", "external_pii",
         lambda t: ["; ".join(f"{x['src']}->{x['dst']}"
                              for x in t.pii_flows()
                              if x["dst"] in set(t.external_deps()))],
         lambda t: "Personal data flows to external components.",
         lambda t: ("Unknown: processing region and transfer mechanism."),
         lambda t: ("Provide region pinning and the transfer mechanism "
                    "(SCCs / adequacy) (L2)."))
    rule("TP-03", "GDPR Art.25 / Internal 4.2", "PII to external LLM",
         "critical", "design", "external_pii",
         lambda t: [f"{x['src']}->{x['dst']}" for x in t.pii_flows()
                    if x["dst"] in set(t.external_deps())],
         lambda t: ("Personal data is sent to an external LLM: " +
                    ", ".join(f"{x['src']}->{x['dst']}"
                              for x in t.pii_flows()
                              if x["dst"] in set(t.external_deps()))),
         lambda t: ("Prompts may be retained or used for training; "
                    "data-protection-by-design is not evidenced."),
         lambda t: ("Provide evidence of PII masking/redaction before "
                    "egress, or a vendor DPA confirming zero retention "
                    "and no training use."))

    # -- IAM --
    rule("IAM-01", "Internal IAM policy", "Over-broad service principal",
         "high", "design", "has_iac",
         lambda t: [f"{p.identity}@{p.diagram_edge['dst']}"
                    for p in t.access_paths
                    if p.identity and "write" in p.permissions],
         lambda t: "Service principal(s) hold write permission.",
         lambda t: ("Write grants that exceed the documented need "
                    "violate least privilege; a compromised identity can "
                    "mutate production state."),
         lambda t: ("Scope each grant to the minimum verbs and resources; "
                    "add just-in-time elevation for writes."))
    rule("IAM-02", "Internal IAM policy", "Unverified access path",
         "high", "information", "has_unverified", _targets_unverified,
         lambda t: ("Diagram edges with no evidenced access path: " +
                    ", ".join(_targets_unverified(t)) if
                    _targets_unverified(t) else "n/a"),
         lambda t: ("Unknown: how the component actually authenticates "
                    "and what it may do."),
         lambda t: ("Resolve via IaC / Entra ID export (L3/L4)."))
    rule("IAM-03", "Internal IAM policy", "Standing privilege without TTL",
         "medium", "information", "has_iac",
         lambda t: sorted({p.identity for p in t.access_paths
                           if p.identity}),
         lambda t: "No rotation/TTL attribute found on machine identities.",
         lambda t: "Unknown: credential lifetime and rotation.",
         lambda t: "Provide rotation policy or TTL configuration (L3).")

    # -- Human oversight / EU AI Act --
    rule("HO-01", "EU AI Act (human oversight)", "High-stakes action w/o human",
         "critical", "design", "agent_write", _targets_write,
         lambda t: ("State-changing operations without human approval: " +
                    "; ".join(_targets_write(t))),
         lambda t: ("Fully automated state changes in a high-stakes "
                    "workflow breach human-oversight obligations."),
         lambda t: ("Insert a human-approval node before each write; "
                    "re-run the pre-check."),
         control_present=lambda t: any(
             v.get("kind") == "human_loop" for v in t.components.values()))
    rule("HO-02", "EU AI Act", "No review path for contested decisions",
         "medium", "information", "has_agent", _targets_agents,
         lambda t: "Agents: " + ", ".join(t.agents),
         lambda t: "Unknown: how affected users contest agent decisions.",
         lambda t: "Describe the review/appeal path (L1 acceptable).")

    # -- RAG --
    rule("RAG-01", "OWASP LLM #8", "RAG poisoning controls absent",
         "high", "design", "has_rag",
         lambda t: [c for c, v in t.components.items()
                    if v.get("kind") == "rag"],
         lambda t: "RAG pipeline declares no corpus poisoning controls.",
         lambda t: ("Poisoned documents become trusted context and steer "
                    "model behavior."),
         lambda t: ("Add source allow-listing, integrity hashes, and "
                    "ingestion review."))
    rule("RAG-02", "OWASP LLM", "Retrieval from untrusted sources",
         "high", "design", "rag_untrusted",
         lambda t: [c for c, v in t.components.items()
                    if v.get("kind") == "rag" and
                    v.get("attrs", {}).get("untrusted_source")],
         lambda t: "RAG ingests from untrusted sources.",
         lambda t: "Untrusted content is retrieved as ground truth.",
         lambda t: "Remove untrusted sources or sandbox their chunks.")

    # -- LLM security (OWASP LLM Top 10) --
    rule("LLM-01", "OWASP LLM #1", "Prompt injection surface",
         "high", "design", "has_llm", lambda t: t.llm_nodes(),
         lambda t: ("User input reaches LLM(s): " +
                    ", ".join(t.llm_nodes())),
         lambda t: ("Adversarial input can hijack model behavior and, "
                    "via tools, downstream systems."),
         lambda t: ("Add input validation, instruction hierarchy, and "
                    "prompt-injection testing."))
    rule("LLM-02", "OWASP LLM #2", "Insecure output handling",
         "high", "design", "has_llm",
         lambda t: [f"{e['src']}->{e['dst']}" for e in t.edges
                    if e["src"] in t.llm_nodes()],
         lambda t: "LLM output flows to downstream systems.",
         lambda t: "Unvalidated model output can inject content or "
                   "commands downstream.",
         lambda t: "Validate/sanitize model output at trust boundaries.")
    rule("LLM-03", "OWASP LLM #6", "Sensitive data in prompts",
         "high", "design", "llm_pii",
         lambda t: [f"{x['src']}->{x['dst']}" for x in t.pii_flows()
                    if x["dst"] in set(t.llm_nodes())],
         lambda t: "Classified data is included in model prompts.",
         lambda t: "Prompts may be logged, retained, or leak via the "
                   "model.",
         lambda t: "Minimize/redact PII in prompts; evidence the "
                   "redaction.")
    rule("LLM-04", "OWASP LLM #5", "Supply chain: unpinned model version",
         "medium", "information", "has_llm", lambda t: t.llm_nodes(),
         lambda t: "No pinned model version found for LLM node(s).",
         lambda t: "Unknown: which exact model runs in production.",
         lambda t: "Pin and record the model version (L3).")
    rule("LLM-05", "OWASP LLM", "Excessive data access for LLM",
         "medium", "design", "llm_pii",
         lambda t: [f"{x['src']}->{x['dst']}" for x in t.pii_flows()
                    if x["dst"] in set(t.llm_nodes())],
         lambda t: "LLM receives classified data beyond task need.",
         lambda t: "Over-collection amplifies breach impact.",
         lambda t: "Scope data access to the minimum required fields.")

    # -- Data --
    rule("DP-01", "Internal data classification", "Unclassified data flows",
         "medium", "information", "always",
         lambda t: [f"{x['src']}->{x['dst']}" for x in t.data_flows
                    if x["classification"] == "unclassified"],
         lambda t: "Some data flows carry no classification.",
         lambda t: "Unknown: handling obligations for these flows.",
         lambda t: "Classify every flow (L1 acceptable).")
    rule("DP-02", "GDPR Art.22", "Automated decision w/o explanation",
         "medium", "information", "has_agent", _targets_agents,
         lambda t: "Agents: " + ", ".join(t.agents),
         lambda t: ("Unknown: whether automated decisions carry "
                    "explanations for affected users."),
         lambda t: "Provide the explanation artifact or notice (L1/L3).")
    rule("DP-03", "Internal data classification", "PII in vector store",
         "high", "design", "vector_db_pii",
         lambda t: [c for c, v in t.components.items()
                    if v.get("kind") == "vector_db" and
                    v.get("attrs", {}).get("stores_pii")],
         lambda t: "Vector database stores PII embeddings.",
         lambda t: ("Embeddings are hard to erase and may leak via "
                    "similarity search."),
         lambda t: ("Add access controls and an erasure procedure, or "
                    "remove PII from the index."))

    # -- EU AI Act --
    rule("EA-01", "EU AI Act Annex III", "High-risk AI tiering",
         "high", "information", "high_risk_use",
         lambda t: [t.purpose or t.business_process],
         lambda t: ("Use case matches a high-risk category: " +
                    (t.purpose or t.business_process)),
         lambda t: ("Unknown: conformity assessment, logging, and "
                    "oversight artifacts required for high-risk AI."),
         lambda t: ("Provide the conformity assessment pack (L2/L3)."))
    rule("EA-02", "EU AI Act Art.50", "AI interaction transparency",
         "medium", "information", "has_user",
         lambda t: ["end-user interaction"],
         lambda t: "AI interacts with end users.",
         lambda t: "Unknown: whether users are told they interact with AI.",
         lambda t: "Provide the disclosure notice text (L1).")

    # -- NIST AI RMF --
    rule("RM-01", "NIST AI RMF (Map)", "Undocumented AI use case",
         "low", "information", "always",
         lambda t: ["purpose"],
         lambda t: "No documented purpose for the AI use case.",
         lambda t: "Risk cannot be mapped without a stated purpose.",
         lambda t: "Document purpose and business process (L1).")
    rule("RM-02", "NIST AI RMF (Measure)", "No evaluation evidence",
         "low", "information", "has_llm", lambda t: t.llm_nodes(),
         lambda t: "No evaluation metrics declared for model(s).",
         lambda t: "Unknown: measured performance and failure modes.",
         lambda t: "Provide eval report (L2/L3).")
    rule("RM-03", "NIST AI RMF (Manage)", "No incident response plan",
         "low", "information", "always",
         lambda t: ["incident response"],
         lambda t: "No AI incident response plan referenced.",
         lambda t: "Unknown: how AI failures are handled.",
         lambda t: "Provide the incident response plan (L1).")
    rule("RM-04", "NIST AI RMF (Govern)", "No accountable owner",
         "low", "information", "always",
         lambda t: ["ownership"],
         lambda t: "No accountable owner declared.",
         lambda t: "Accountability cannot be assigned.",
         lambda t: "Name the accountable owner (L1).")

    return R
