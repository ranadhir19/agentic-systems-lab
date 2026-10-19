"""The human principal: scarce attention, fallible judgment.

The principal is interrupted when the escalation policy asks. Each
interruption costs `interruption_cost` (context-switching, time). When
asked, the human resolves the decision correctly with probability
`accuracy`; a human error still incurs the error cost. The attention
budget caps how many interruptions one episode may contain -- asks beyond
the budget are ignored (the agent must act alone), which is how attention
exhaustion is modeled.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HumanPrincipal:
    budget: int = 10**9          # max interruptions per episode
    interruption_cost: float = 5.0
    error_cost: float = 1.0      # multiplier on stakes when an error slips through
    accuracy: float = 0.95       # P(human resolves correctly when asked)

    def error_price(self, stakes: float) -> float:
        return stakes * self.error_cost
