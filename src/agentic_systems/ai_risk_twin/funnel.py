"""The dynamic assessment funnel.

Instead of a static 125-question questionnaire, the funnel filters by
what the architecture actually contains:

    125 questions in the bank
      -> triggered by architecture patterns (agent -> agentic risk,
         external API -> third-party risk, write op -> IAM/excessive
         agency, RAG -> poisoning, ...)
      -> auto-answered from parsed artifacts (models, agents, write ops,
         identities, ...)
      -> evidence-required (needs an uploaded artifact: DPA, SOC 2, ...)
      -> user clarification (needs human context)

Each stage shrinks the remaining work. The funnel also records *why* a
question survived each stage, so the assessment is auditable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .evidence import Evidence, EvidenceLevel
from .knowledge import AUTO, TRIGGERS, Question, Twin


@dataclass
class FunnelAnswer:
    qid: str
    text: str
    category: str
    answer: str
    via: str                      # "auto" | "evidence" | "clarification"


@dataclass
class FunnelReport:
    bank: int
    relevant: List[Question]
    auto_answered: List[FunnelAnswer]
    evidence_required: List[Question]
    clarification: List[Question]

    @property
    def counts(self) -> Dict[str, int]:
        return {
            "bank": self.bank,
            "relevant": len(self.relevant),
            "auto_answered": len(self.auto_answered),
            "evidence_required": len(self.evidence_required),
            "clarification": len(self.clarification),
        }


def run_funnel(twin: Twin, bank: List[Question],
               provided_evidence: Optional[Dict[str, Evidence]] = None
               ) -> FunnelReport:
    """Run the dynamic funnel over the question bank."""
    provided = provided_evidence or {}
    relevant = [q for q in bank if TRIGGERS[q.trigger](twin)]

    auto_answered: List[FunnelAnswer] = []
    remaining: List[Question] = []
    for q in relevant:
        answered = False
        if q.auto is not None:
            ans = AUTO[q.auto](twin)
            if ans:
                auto_answered.append(FunnelAnswer(
                    qid=q.qid, text=q.text, category=q.category,
                    answer=ans, via="auto"))
                answered = True
        if not answered and q.evidence_kind in provided:
            ev = provided[q.evidence_kind]
            auto_answered.append(FunnelAnswer(
                qid=q.qid, text=q.text, category=q.category,
                answer=(f"resolved by {ev.reference} "
                        f"({ev.level.name})"), via="evidence"))
            answered = True
        if not answered:
            remaining.append(q)

    evidence_required = [q for q in remaining if q.evidence_kind is not None]
    clarification = [q for q in remaining if q.evidence_kind is None]
    return FunnelReport(bank=len(bank), relevant=relevant,
                        auto_answered=auto_answered,
                        evidence_required=evidence_required,
                        clarification=clarification)
