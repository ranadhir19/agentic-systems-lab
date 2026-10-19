"""Agents for long-horizon tasks: one baseline and four mitigations.

All mitigations share one private segmented-execution core
(``_segmented_run``); the named agents are configurations of it, plus
the voting agent which is a genuinely different mechanism (per-step
redundancy instead of verify-and-rollback). The unified view is
deliberate -- the design space of "verify every k steps and roll back"
is continuous, and the named agents are points in it:

- baseline:            no intermediate verification at all
- checkpoints(k):      verify every k steps, rollback + full redo on detection
- hierarchy(s):        planner splits into sub-tasks of size s; workers get
                       narrower specs so per-step error is multiplied by
                       ``spec_factor`` (< 1); sub-task boundaries are verified
- recovery(k):         checkpoints + diagnosis (targeted redo from the
                       corrupted step instead of the segment start) +
                       step-level retries on fatal errors
- voting(n):           each step executed n times, majority vote wins

Cost model (step-units): executing a step costs 1.0, a verification
costs ``verify_cost``, a diagnosis costs ``diag_cost``. Redoing work
re-pays step costs. The headline metric is cost-per-successful-task.
"""
from __future__ import annotations

from .tasks import TaskSpec, RunReport, draw_step

STEP_COST = 1.0


def run_baseline(spec: TaskSpec, rng) -> RunReport:
    """Linear executor: no intermediate checks. Any fatal or any latent
    corruption fails the task (the final grader is perfect)."""
    cost = 0.0
    corrupted = False
    for i in range(spec.n_steps):
        pf = spec.p_fatal * (1.0 + spec.cascade if corrupted else 1.0)
        out = draw_step(rng, pf, spec.p_err)
        cost += STEP_COST
        if out == "fatal":
            return RunReport(False, cost, spec.n_steps, 0, 0, "fatal")
        if out == "corrupt":
            corrupted = True
    if corrupted:
        return RunReport(False, cost, spec.n_steps, 0, 0, "corruption")
    return RunReport(True, cost, spec.n_steps, 0, 0, None)


def _segmented_run(
    spec: TaskSpec,
    rng,
    segment: int,
    pe_mult: float = 1.0,
    r_max: int = 3,
    verify_cost: float = 2.0,
    diag_acc: float = 0.0,
    diag_cost: float = 0.0,
    step_retries: int = 0,
) -> RunReport:
    """Verify-and-rollback core.

    Executes the task in segments of ``segment`` steps. After each
    segment, state is verified (cost ``verify_cost``); corruption is
    spotted with probability ``spec.detect_check``. On a fatal error or
    a detected corruption, execution rolls back to the segment start and
    redoes the segment (fresh RNG draws), up to ``r_max`` redos per
    segment -- then the task fails.

    Corruption that *predates* the rollback point cannot be cleared by
    rolling back (tracked via ``corrupt_origin``); redos then fail again
    until the budget is exhausted. This is the honest limit of
    checkpointing under fallible verification.

    With ``diag_acc > 0`` (recovery agent), a detected corruption is
    diagnosed: with probability ``diag_acc`` the corrupted step is found
    and only steps from there are redone (targeted repair); otherwise a
    full segment redo is done and the diagnosis cost is wasted.
    ``step_retries`` retries a fatally-failed step in place before
    triggering a segment rollback.
    """
    cost = 0.0
    verifications = 0
    redos = 0
    diagnoses = 0
    n = spec.n_steps
    pe = spec.p_err * pe_mult

    step = 0            # rollback point: start of current segment
    corrupted = False   # persistent latent-corruption flag
    corrupt_origin: int | None = None

    while step < n:
        seg_end = min(step + segment, n)
        pos = step      # where (re-)execution begins inside the segment
        redo_count = 0
        while True:
            # --- execute [pos, seg_end) ---
            seg_corrupted = False
            seg_origin: int | None = None
            fatal_hard = False
            i = pos
            while i < seg_end:
                eff_corr = corrupted or seg_corrupted
                pf = spec.p_fatal * (1.0 + spec.cascade if eff_corr else 1.0)
                out = draw_step(rng, pf, pe)
                cost += STEP_COST
                if out == "fatal":
                    recovered = False
                    for _ in range(step_retries):
                        cost += STEP_COST
                        out2 = draw_step(rng, pf, pe)
                        if out2 != "fatal":
                            recovered = True
                            out = out2
                            break
                    if not recovered:
                        fatal_hard = True
                        break
                if out == "corrupt" and not seg_corrupted:
                    seg_corrupted = True
                    seg_origin = i
                i += 1

            # --- checkpoint verification ---
            verifications += 1
            cost += verify_cost
            total_corrupted = corrupted or seg_corrupted
            origin = corrupt_origin if corrupted else seg_origin
            detected = total_corrupted and rng.random() < spec.detect_check

            if fatal_hard or detected:
                redo_count += 1
                redos += 1
                if redo_count > r_max:
                    cause = "fatal" if fatal_hard else "redo_exhausted"
                    return RunReport(False, cost, n, verifications, redos,
                                     cause)
                # rollback to `step`; clear corruption only if it started
                # at or after the rollback point
                if origin is not None and origin < step:
                    pass  # predates rollback: unrecoverable by redo
                else:
                    corrupted = False
                    corrupt_origin = None
                # targeted repair via diagnosis (recovery agent)
                if (detected and diag_acc > 0.0 and origin is not None
                        and origin >= step):
                    diagnoses += 1
                    cost += diag_cost
                    if rng.random() < diag_acc:
                        pos = origin  # redo from the corrupted step only
                        continue
                pos = step  # full segment redo
                continue
            # segment accepted (corruption may persist undetected)
            if seg_corrupted:
                corrupted = True
                if corrupt_origin is None:
                    corrupt_origin = seg_origin
            break
        step = seg_end

    if corrupted:
        return RunReport(False, cost, n, verifications, redos, "corruption")
    return RunReport(True, cost, n, verifications, redos, None)


def run_checkpoints(spec: TaskSpec, rng, k: int = 5,
                    r_max: int = 3, verify_cost: float = 2.0) -> RunReport:
    """Verify state every k steps; on detection roll back and redo the
    whole segment (bounded redos)."""
    return _segmented_run(spec, rng, segment=k, r_max=r_max,
                          verify_cost=verify_cost)


def run_hierarchy(spec: TaskSpec, rng, subtask_size: int = 10,
                  spec_factor: float = 0.5, r_max: int = 2,
                  verify_cost: float = 2.0) -> RunReport:
    """Planner decomposes the task into sub-tasks of ``subtask_size``
    steps. Workers get narrower specifications, so their per-step error
    rate is multiplied by ``spec_factor`` (the honest mechanism by which
    decomposition helps: smaller scope, fewer errors). Sub-task
    boundaries are verified; failures redo only the sub-task."""
    return _segmented_run(spec, rng, segment=subtask_size,
                          pe_mult=spec_factor, r_max=r_max,
                          verify_cost=verify_cost)


def run_recovery(spec: TaskSpec, rng, k: int = 5, r_max: int = 3,
                 verify_cost: float = 2.0, diag_acc: float = 0.85,
                 diag_cost: float = 3.0, step_retries: int = 2) -> RunReport:
    """HealFlow-style: checkpoints plus diagnosis and smallest repair.
    Detected corruption is diagnosed (accuracy ``diag_acc``); on a hit,
    only steps from the corrupted step are redone instead of the whole
    segment. Fatal step errors are retried in place up to
    ``step_retries`` times before a segment rollback."""
    return _segmented_run(spec, rng, segment=k, r_max=r_max,
                          verify_cost=verify_cost, diag_acc=diag_acc,
                          diag_cost=diag_cost, step_retries=step_retries)


def run_hierarchy_checkpoints(spec: TaskSpec, rng, subtask_size: int = 10,
                              k: int = 5, spec_factor: float = 0.5,
                              r_max: int = 3,
                              verify_cost: float = 2.0) -> RunReport:
    """Interaction: hierarchical decomposition (narrower worker specs)
    *plus* checkpoints inside each sub-task."""
    return _segmented_run(spec, rng, segment=k, pe_mult=spec_factor,
                          r_max=r_max, verify_cost=verify_cost)


def run_voting(spec: TaskSpec, rng, n: int = 3) -> RunReport:
    """Per-step redundancy: execute each step n times, majority vote
    wins. Per attempt, P(correct) = 1 - p_fatal - p_err (fatal and
    corrupt attempts are both just wrong votes -- documented lumping);
    a step with no majority is latently corrupted, which is absorbing
    (voting has no repair mechanism). Cost is n steps per nominal step.
    """
    assert n % 2 == 1, "voting needs an odd n for a clean majority"
    cost = 0.0
    corrupted = False
    q = 1.0 - spec.p_fatal - spec.p_err
    need = n // 2 + 1
    for _ in range(spec.n_steps):
        votes = 0
        for _ in range(n):
            cost += STEP_COST
            if rng.random() < q:
                votes += 1
        if votes < need:
            corrupted = True
    if corrupted:
        return RunReport(False, cost, spec.n_steps, 0, 0, "corruption")
    return RunReport(True, cost, spec.n_steps, 0, 0, None)


def theoretical_voting_per_step_q(spec: TaskSpec, n: int = 3) -> float:
    """Closed-form per-step success for voting: P(Binomial(n, q) > n/2).
    Used to validate the simulation against theory."""
    from math import comb
    q = 1.0 - spec.p_fatal - spec.p_err
    need = n // 2 + 1
    return sum(comb(n, j) * q ** j * (1 - q) ** (n - j)
               for j in range(need, n + 1))
