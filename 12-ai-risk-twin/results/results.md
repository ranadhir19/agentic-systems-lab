# CISO AI Risk Twin — results

All numbers from deterministic runs (seed 0).

## Exp A — worked example end-to-end

Inconsistencies (doc claim vs architecture): 2
- support_agent: claimed 'read-only'; observed write edge support_agent -> transaction_api (POST)
- support_agent: claimed 'no external data sharing'; observed external components: helpdesk_llm

Findings: 29 (13 design, 16 information; 5 critical, 9 high, 11 medium, 4 low)

Critical finding titles:
- Excessive agency
- High-stakes action w/o human
- PII to external LLM

Evidence-level histogram (finding evidence items):
- L3_ARTIFACT: 38
- L4_ENTERPRISE: 12

Readiness: architecture 0.8333, evidence 0.0, control 0.0, confidence 0.8082 -> score 0.4104, **NOT READY**
Blocking reasons:
- 5 critical design finding(s) without evidenced control
- 16 mandatory evidence item(s) unresolved
- 2 architecture/documentation inconsistenc(ies)

## Exp B — dynamic funnel (125-question bank)

| architecture | relevant | auto-answered | evidence-required | clarification |
|---|---|---|---|---|
| simple_chatbot | 65 | 3 | 40 | 22 |
| rag_assistant | 86 | 7 | 45 | 34 |
| agentic_platform | 121 | 9 | 59 | 53 |

## Exp C — evidence-level sensitivity

| vendor pack | confidence | evidence completeness | readiness score |
|---|---|---|---|
| none | 0.8082 | 0.0 | 0.4104 |
| L1_assertion | 0.8138 | 0.0 | 0.4118 |
| L2_vendor_doc | 0.8156 | 0.125 | 0.4435 |
| L4_enterprise | 0.8242 | 0.125 | 0.4456 |

## Exp D — fix-and-rerun

Resolved 7, introduced 2, still open 21; severity delta -20.
Resolved rules: AG-01, AG-02, DP-01, HO-01, IAM-02
Introduced:
- DP-01 Unclassified data flows ['support_agent->human_approval']
- DP-01 Unclassified data flows ['human_approval->transaction_api']

## Exp E — drift detection

- **critical** support_agent -> shadow_analytics: Observed support_agent -> shadow_analytics was not in the approved twin (method/rel SENDS). Unapproved data/control flow.
