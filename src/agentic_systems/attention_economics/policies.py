"""Escalation policies: who decides whether the human is interrupted.

The rational benchmark: asking has expected value

    V(ask) = (1 - c) * stakes * error_cost - interruption_cost
             - (1 - human_accuracy) * stakes * error_cost
           = (human_accuracy - c) * stakes * error_cost - interruption_cost

i.e. the expected error cost avoided, minus the human's own error rate,
minus the interruption price. The stakes-adjusted policy asks exactly
when V(ask) > 0, which is the per-decision optimal rule. (Ignoring the
human's fallibility -- the textbook version -- over-asks; the experiments
measure the difference.) The budget-aware policy solves the knapsack:
with unit-cost interruptions, asking the highest-value decisions first
is optimal under a hard attention budget.
"""

from __future__ import annotations

import numpy as np

from .principal import HumanPrincipal
from .world import DecisionStream


class EscalationPolicy:
    name = "base"

    def select(self, stream: DecisionStream, principal: HumanPrincipal) -> np.ndarray:
        """Return a boolean ask-mask, one entry per decision."""
        raise NotImplementedError


class AlwaysAsk(EscalationPolicy):
    name = "always-ask"

    def select(self, stream, principal):
        return np.ones(len(stream), dtype=bool)


class NeverAsk(EscalationPolicy):
    name = "never-ask"

    def select(self, stream, principal):
        return np.zeros(len(stream), dtype=bool)


class FixedThreshold(EscalationPolicy):
    """Ask whenever stated confidence falls below a fixed threshold."""

    def __init__(self, tau: float):
        self.tau = tau
        self.name = f"fixed-tau={tau:.2f}"

    def select(self, stream, principal):
        return stream.confidence < self.tau


class StakesAdjusted(EscalationPolicy):
    """Ask iff the expected value of asking is positive.

    V(ask) = (h - c) * stakes * error_cost - interruption_cost > 0
    where h is the human's accuracy -- a fallible human is priced in.
    """

    name = "stakes-adjusted"

    def select(self, stream, principal):
        value = (
            (principal.accuracy - stream.confidence)
            * stream.stakes
            * principal.error_cost
            - principal.interruption_cost
        )
        return value > 0.0


class BudgetAware(EscalationPolicy):
    """Knapsack over attention: ask the highest-value decisions first.

    Each interruption costs one unit of budget, so the greedy
    highest-value-first order is optimal. Only positive-value asks
    are ever worth making.
    """

    def __init__(self, budget: int):
        self.budget = budget
        self.name = f"budget-aware(B={budget})"

    def select(self, stream, principal):
        value = (
            (principal.accuracy - stream.confidence)
            * stream.stakes
            * principal.error_cost
            - principal.interruption_cost
        )
        order = np.argsort(-value)  # highest value first
        mask = np.zeros(len(stream), dtype=bool)
        taken = 0
        for i in order:
            if taken >= self.budget:
                break
            if value[i] <= 0.0:
                break
            mask[i] = True
            taken += 1
        return mask


class Truncated(EscalationPolicy):
    """Wrap another policy: first-come asks until the budget is exhausted.

    This is what a naive implementation does -- it asks in stream order
    and stops when attention runs out, starving later (possibly
    higher-stakes) decisions. Used to show what breaks under exhaustion.
    """

    def __init__(self, inner: EscalationPolicy, budget: int):
        self.inner = inner
        self.budget = budget
        self.name = f"truncated({inner.name},B={budget})"

    def select(self, stream, principal):
        want = self.inner.select(stream, principal)
        idx = np.flatnonzero(want)
        mask = np.zeros(len(stream), dtype=bool)
        mask[idx[: self.budget]] = True
        return mask
