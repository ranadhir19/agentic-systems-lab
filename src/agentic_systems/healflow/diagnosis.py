"""Causal failure diagnosis.

When a step fails, the diagnoser doesn't just blame the step that raised —
it walks the dependency chain backwards, re-verifying each completed
step's postconditions against its stored outputs. The first step (walking
back) whose contract is violated is the *culprit*; the repair targets the
culprit, not the symptom. This is what separates diagnosis from retry:
retry re-executes the symptom, diagnosis fixes the cause.
"""
from __future__ import annotations

from dataclasses import dataclass

from .faults import ToolFailed, ToolOutage
from .repair import SCHEMA_PREDS


@dataclass
class Diagnosis:
    cause: str              # transient_outage|persistent_outage|schema_change
                            # |bad_intermediate|precondition_violated
    culprit_id: str
    repair: str             # retry|substitute|rollback_recompute
                            # |compensate_abort|escalate
    steps: int              # diagnosis steps taken
    detail: str = ""


class Diagnoser:
    def __init__(self, predicates: dict, substitutes: dict):
        self.predicates = predicates
        self.substitutes = substitutes

    def _step(self, workflow, step_id: str):
        return next(s for s in workflow.steps if s.id == step_id)

    def diagnose(self, rs, failed_step, error, failed_preds,
                 retries_used: int, max_retries: int) -> Diagnosis:
        steps = 1  # classification itself
        # --- exceptions: the tool itself is the culprit -------------------
        if isinstance(error, (ToolOutage, ToolFailed)):
            if retries_used >= max_retries:
                cause = "persistent_outage"
            else:
                cause = "transient_outage"
            repair = self._repair_for(failed_step, cause, rs)
            return Diagnosis(cause, failed_step.id, repair, steps,
                             f"{type(error).__name__} on {failed_step.tool}")

        # --- contract violation: walk back to the culprit -----------------
        culprit = failed_step
        for sid in reversed(rs.completed):
            steps += 1
            step = self._step(rs.workflow, sid)
            bad = [p for p in step.post
                   if not self.predicates[p](rs, rs.outputs.get(sid))]
            if bad:
                culprit = step
                break
        if any(p in SCHEMA_PREDS for p in failed_preds):
            cause = "schema_change"
        elif culprit.id != failed_step.id:
            cause = "bad_intermediate"
        elif failed_preds and all(
                p in failed_step.pre for p in failed_preds):
            cause = "precondition_violated"
        else:
            cause = "bad_intermediate"
        repair = self._repair_for(culprit, cause, rs)
        return Diagnosis(cause, culprit.id, repair, steps,
                         f"contract {failed_preds} -> culprit {culprit.id}")

    def _repair_for(self, step, cause: str, rs) -> str:
        if cause == "transient_outage":
            return "retry"
        if cause == "schema_change":
            if step.substitutable and step.tool in self.substitutes:
                return "substitute"
            return "escalate"
        if cause in ("bad_intermediate", "precondition_violated"):
            return "rollback_recompute"
        if cause == "persistent_outage":
            # external side effects already committed? compensate first.
            if any(self._step(rs.workflow, sid).external
                   for sid in rs.completed):
                return "compensate_abort"
            if step.substitutable and step.tool in self.substitutes:
                return "substitute"
            return "escalate"
        return "escalate"
