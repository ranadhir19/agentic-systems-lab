"""Long-horizon task model.

A task is a sequence of N steps. Each step draws one of three outcomes:

- ``clean``    -- correct output, state stays healthy
- ``corrupt``  -- recoverable error: output is wrong but the failure is
                  *latent*. Corruption persists (``corrupted`` flag) and
                  poisons downstream steps: while corrupted, the per-step
                  fatal probability is inflated by ``cascade``. This is the
                  compounding mechanism behind long-horizon decay.
- ``fatal``    -- unrecoverable-at-this-step error: the current attempt
                  aborts immediately.

Success is judged by a perfect final grader (``detect_final = 1.0``):
the task succeeds iff no fatal ever occurred and no corruption was
ever left unrepaired. Intermediate verification (checkpoints) is
*fallible* (``detect_check < 1.0``) -- an agent's own judgment call --
which is why corruption can predate a rollback point and become
unrecoverable. That asymmetry (perfect final grading, imperfect
intermediate verification) is the core honest assumption of the model.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskSpec:
    """Parameters of the long-horizon task family."""
    n_steps: int
    p_fatal: float = 0.01      # per-step fatal-error probability (healthy state)
    p_err: float = 0.03        # per-step latent-corruption probability
    cascade: float = 2.0       # fatal prob multiplier while corrupted: pf*(1+cascade)
    detect_check: float = 0.8  # P(checkpoint verification spots corruption)


@dataclass
class RunReport:
    """Outcome of one task execution."""
    success: bool
    cost: float            # step-units of work (executions + verifications + diagnoses)
    steps: int             # nominal task length attempted
    verifications: int
    redos: int
    failure_cause: str | None  # "fatal" | "corruption" | "redo_exhausted" | "unrecoverable" | None


def draw_step(rng, p_fatal: float, p_err: float) -> str:
    """Draw one step outcome: 'clean', 'corrupt', or 'fatal'."""
    r = rng.random()
    if r < p_fatal:
        return "fatal"
    if r < p_fatal + p_err:
        return "corrupt"
    return "clean"


def theoretical_per_step_q(spec: TaskSpec) -> float:
    """Baseline per-step success prob (no cascade effect: any corruption
    already dooms the baseline task, so inflation is unobservable there)."""
    return (1.0 - spec.p_fatal) * (1.0 - spec.p_err)
