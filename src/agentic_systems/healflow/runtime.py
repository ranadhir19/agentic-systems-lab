"""Runtimes: HealFlow (diagnose -> smallest viable repair -> verify)
and two baselines (naive retry, LLM-style replan).

HealFlow's loop:
  1. check preconditions -> execute (checkpoint first) -> check postconditions
  2. on failure: repair-memory lookup (failure signature) or causal diagnosis
  3. apply the smallest viable repair: retry < substitute < rollback <
     compensate+abort < escalate
  4. VERIFY the repair (re-check contracts) before resuming; a repair is
     recorded to memory only after its step's contracts verify, and a
     failed verification escalates instead of cascading.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .diagnosis import Diagnoser
from .faults import ToolFailed, ToolOutage
from .repair import RepairMemory
from .workflow import RunState


@dataclass
class RunReport:
    workflow: str
    success: bool = False
    graceful: bool = False      # aborted safely (compensated), no side effects
    escalated: bool = False
    tool_calls: int = 0
    side_effects: int = 0
    diagnosis_steps: int = 0
    memory_hits: int = 0
    correct_diagnosis: bool | None = None
    repairs: list = field(default_factory=list)


class HealFlowRuntime:
    def __init__(self, injector, predicates, substitutes, use_memory=True,
                 max_retries=2):
        self.injector = injector
        self.predicates = predicates
        self.substitutes = substitutes
        self.use_memory = use_memory
        self.max_retries = max_retries
        self.diagnoser = Diagnoser(predicates, substitutes)
        self.memory = RepairMemory()

    # ------------------------------------------------------------------
    def run(self, workflow, expected_cause: str | None = None) -> RunReport:
        rs = RunState(workflow)
        rep = RunReport(workflow.name)
        substitutions: dict[str, str] = {}
        retries: dict[str, int] = {}
        pending_record: dict[str, tuple] = {}  # step_id -> memory key
        ext_calls, comp_calls = 0, 0
        idx, n_steps = 0, len(workflow.steps)

        def note_verified(step_id):
            key = pending_record.pop(step_id, None)
            if key is not None and self.use_memory:
                # the repaired step's contracts just verified: record it
                last_repair = rep.repairs[-1] if rep.repairs else None
                if last_repair:
                    self.memory.record(key, last_repair)

        # (closures for counters)
        counters = {"ext": 0, "comp": 0}
        applied = set()  # (step_id, repair) already tried: never loop a repair

        def handle2(step, error, failed_preds, phase):
            nonlocal idx
            first = retries.get(step.id, 0) == 0
            key = RepairMemory.key_for(error, failed_preds, first)
            repair, mem_hit, dsteps = None, False, 0
            if self.use_memory and first:
                hit = self.memory.lookup(key)
                if hit and self._applicable(step, hit[0]):
                    repair, mem_hit, dsteps = hit[0], True, 1
                    rep.memory_hits += 1
            if repair is None:
                diagnosis = self.diagnoser.diagnose(
                    rs, step, error, failed_preds,
                    retries.get(step.id, 0), self.max_retries)
                repair, dsteps = diagnosis.repair, diagnosis.steps
                if expected_cause is not None:
                    if diagnosis.cause == expected_cause:
                        rep.correct_diagnosis = True
                    elif rep.correct_diagnosis is None:
                        rep.correct_diagnosis = False
                culprit_id = diagnosis.culprit_id
            else:
                culprit_id = (self._walkback_culprit(rs, step)
                              if repair == "rollback_recompute" else step.id)
                dsteps += 1 if repair == "rollback_recompute" else 0
            rep.diagnosis_steps += dsteps
            # never apply the same non-retry repair twice: fall back to the
            # next viable repair (rollback -> substitute), else escalate
            if repair in ("substitute", "rollback_recompute"):
                sig = (step.id, repair)
                if sig in applied:
                    if (repair == "rollback_recompute"
                            and self._applicable(step, "substitute")
                            and (step.id, "substitute") not in applied):
                        repair = "substitute"
                        sig = (step.id, repair)
                        rs.log("repair_fallback", step=step.id,
                               to="substitute")
                    else:
                        rep.escalated = True
                        rs.log("escalated", step=step.id,
                               why="repair already attempted")
                        return "abort"
                applied.add(sig)
            rep.repairs.append(repair)
            # --- apply ---
            if repair == "retry":
                retries[step.id] = retries.get(step.id, 0) + 1
                if retries[step.id] > self.max_retries:
                    rep.escalated = True
                    rs.log("escalated", step=step.id, why="retries exhausted")
                    return "abort"
                pending_record[step.id] = key
                rs.log("repair", kind2="retry", step=step.id)
                return "retry"
            if repair == "substitute":
                substitutions[step.id] = self.substitutes[step.tool]
                pending_record[step.id] = key
                rs.log("repair", kind2="substitute", step=step.id,
                       tool=substitutions[step.id])
                return "retry"
            if repair == "rollback_recompute":
                rs.rollback(culprit_id)
                pending_record[culprit_id] = key
                rs.log("repair", kind2="rollback", to=culprit_id)
                return workflow.steps.index(next(
                    s for s in workflow.steps if s.id == culprit_id))
            if repair == "compensate_abort":
                for sid in reversed(rs.completed):
                    st = next(s for s in workflow.steps if s.id == sid)
                    if st.external and st.compensation:
                        self.injector.call(st.compensation, rs.state, {})
                        rs.tool_calls += 1
                        counters["comp"] += 1
                        rs.log("compensated", step=sid)
                # record the validated abort strategy
                if self.use_memory:
                    self.memory.record(key, repair)
                rep.graceful = True
                rs.log("aborted_gracefully", at=step.id)
                return "abort"
            rep.escalated = True
            rs.log("escalated", step=step.id, repair=repair)
            return "abort"

        while idx < n_steps:
            step = workflow.steps[idx]
            bad_pre = [p for p in step.pre
                       if not self.predicates[p](rs, None)]
            if bad_pre:
                nxt = handle2(step, None, bad_pre, "pre")
                if nxt == "abort":
                    break
                idx = nxt if isinstance(nxt, int) else idx
                continue
            rs.checkpoint(step.id)
            tool = substitutions.get(step.id, step.tool)
            try:
                out = self.injector.call(tool, rs.state, step.args)
                rs.tool_calls += 1
                if step.external:
                    counters["ext"] += 1
            except (ToolOutage, ToolFailed) as e:
                rs.log("exec_failed", step=step.id, error=type(e).__name__)
                nxt = handle2(step, e, [], "exec")
                if nxt == "abort":
                    break
                idx = nxt if isinstance(nxt, int) else idx
                continue
            rs.outputs[step.id] = out
            rs.state[step.id] = out
            bad_post = [p for p in step.post
                        if not self.predicates[p](rs, out)]
            if bad_post:
                rs.log("post_failed", step=step.id, preds=bad_post)
                nxt = handle2(step, None, bad_post, "post")
                if nxt == "abort":
                    break
                idx = nxt if isinstance(nxt, int) else idx
                continue
            note_verified(step.id)
            rs.completed.append(step.id)
            idx += 1

        rep.success = (idx == n_steps)
        rep.tool_calls = rs.tool_calls
        n_ext_steps = sum(1 for s in workflow.steps if s.external)
        rep.side_effects = max(
            0, (counters["ext"] - counters["comp"])
               - (n_ext_steps if rep.success else 0))
        return rep

    # ------------------------------------------------------------------
    def _applicable(self, step, repair: str) -> bool:
        if repair == "substitute":
            return step.substitutable and step.tool in self.substitutes
        return repair in ("retry", "rollback_recompute")

    def _walkback_culprit(self, rs, failed_step) -> str:
        for sid in reversed(rs.completed):
            step = next(s for s in rs.workflow.steps if s.id == sid)
            if any(not self.predicates[p](rs, rs.outputs.get(sid))
                   for p in step.post):
                return sid
        return failed_step.id


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------
class RetryBaseline:
    """Naive: retry the failed step up to 3x, then abort. No diagnosis,
    no checkpoints, no compensation."""

    name = "retry"

    def __init__(self, injector, predicates):
        self.injector = injector
        self.predicates = predicates

    def run(self, workflow, expected_cause=None) -> RunReport:
        rs = RunState(workflow)
        rep = RunReport(workflow.name)
        ext = 0
        for step in workflow.steps:
            ok = False
            for _ in range(3):
                try:
                    out = self.injector.call(step.tool, rs.state, step.args)
                    rs.tool_calls += 1
                    if step.external:
                        ext += 1
                except (ToolOutage, ToolFailed):
                    continue
                rs.outputs[step.id] = out
                rs.state[step.id] = out
                if all(self.predicates[p](rs, out) for p in step.post):
                    ok = True
                    break
                # postcondition failed: naive retry just tries again
                del rs.outputs[step.id]
                del rs.state[step.id]
            if not ok:
                break
        rep.success = len(rs.outputs) == len(workflow.steps)
        rep.tool_calls = rs.tool_calls
        n_ext = sum(1 for s in workflow.steps if s.external)
        rep.side_effects = max(0, ext - (n_ext if rep.success else 0))
        return rep


class ReplanBaseline:
    """LLM-replan style: on any failure, restart the whole workflow from
    scratch (up to 2 restarts). No diagnosis, no compensation — side
    effects repeat."""

    name = "replan"

    def __init__(self, injector, predicates):
        self.injector = injector
        self.predicates = predicates

    def run(self, workflow, expected_cause=None) -> RunReport:
        rep = RunReport(workflow.name)
        ext, calls = 0, 0
        for _ in range(3):  # initial + 2 replans
            rs = RunState(workflow)
            failed = False
            for step in workflow.steps:
                try:
                    out = self.injector.call(step.tool, rs.state, step.args)
                    calls += 1
                    if step.external:
                        ext += 1
                except (ToolOutage, ToolFailed):
                    failed = True
                    break
                rs.outputs[step.id] = out
                rs.state[step.id] = out
                if not all(self.predicates[p](rs, out) for p in step.post):
                    failed = True
                    break
            if not failed:
                rep.success = True
                break
        rep.tool_calls = calls
        n_ext_steps = sum(1 for s in workflow.steps if s.external)
        rep.side_effects = max(0, ext - (n_ext_steps if rep.success else 0))
        return rep
