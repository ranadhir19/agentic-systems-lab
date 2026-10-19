"""The cost model: price every escalation decision.

Per decision:
  ask:  interruption_cost  (+ error_price if the human also errs)
  auto: 0 if the agent was right, else error_price(stakes)

total_cost = interruptions x interruption_cost
           + asked_human_errors x error_price
           + unaudited_agent_errors x error_price

Asks beyond the principal's budget are ignored (attention exhaustion):
the agent must act alone on those decisions.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .policies import EscalationPolicy
from .principal import HumanPrincipal
from .world import DecisionStream


@dataclass
class CostReport:
    policy_name: str
    total_cost: float
    n_asks: int
    interruption_cost: float
    n_unaudited_errors: int
    unaudited_error_cost: float
    n_asked_human_errors: int
    asked_human_error_cost: float
    n_budget_exceeded: int  # asks the policy wanted but the budget denied


class CostModel:
    def __init__(self, principal: HumanPrincipal, seed: int = 7):
        self.principal = principal
        self.seed = seed

    def evaluate(self, stream: DecisionStream, policy: EscalationPolicy) -> CostReport:
        rng = np.random.default_rng(self.seed)
        p = self.principal
        want = policy.select(stream, p)

        # Attention exhaustion: only the first `budget` asks go through.
        idx = np.flatnonzero(want)
        denied = max(0, len(idx) - p.budget)
        ask = np.zeros(len(stream), dtype=bool)
        ask[idx[: p.budget]] = True

        stakes = stream.stakes
        correct = stream.correct

        human_wrong = rng.random(len(stream)) >= p.accuracy

        asked = ask
        asked_err = asked & human_wrong
        asked_human_cost = float(np.sum(stakes[asked_err] * p.error_cost))
        interruption_cost = float(asked.sum() * p.interruption_cost)

        auto = ~asked
        unaudited_err = auto & (~correct)
        unaudited_cost = float(np.sum(stakes[unaudited_err] * p.error_cost))

        total = interruption_cost + asked_human_cost + unaudited_cost
        return CostReport(
            policy_name=policy.name,
            total_cost=total,
            n_asks=int(asked.sum()),
            interruption_cost=interruption_cost,
            n_unaudited_errors=int(unaudited_err.sum()),
            unaudited_error_cost=unaudited_cost,
            n_asked_human_errors=int(asked_err.sum()),
            asked_human_error_cost=asked_human_cost,
            n_budget_exceeded=int(denied),
        )


def evaluate(
    stream: DecisionStream,
    principal: HumanPrincipal,
    policy: EscalationPolicy,
    seed: int = 7,
) -> CostReport:
    return CostModel(principal, seed=seed).evaluate(stream, policy)
