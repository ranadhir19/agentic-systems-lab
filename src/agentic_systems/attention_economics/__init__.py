"""Attention economics: the cost of asking vs the cost of being wrong.

A stream of decisions arrives. Each decision has stakes (what an unaudited
agent error costs) and the agent's stated confidence. The human principal
has a scarce attention budget: every interruption costs context-switching,
but every uncaught error costs stakes. This module simulates that economy
so escalation policies can be priced, compared, and optimized.

All randomness is seeded; every number in the results is reproducible.
"""

from .world import Decision, DecisionStream, make_stream
from .principal import HumanPrincipal
from .policies import (
    EscalationPolicy,
    AlwaysAsk,
    NeverAsk,
    FixedThreshold,
    StakesAdjusted,
    BudgetAware,
    Truncated,
)
from .calibration import (
    reliability_diagram,
    expected_calibration_error,
    trust_sweep,
    over_trust_index,
    under_trust_index,
)
from .cost import CostModel, CostReport, evaluate

__all__ = [
    "Decision",
    "DecisionStream",
    "make_stream",
    "HumanPrincipal",
    "EscalationPolicy",
    "AlwaysAsk",
    "NeverAsk",
    "FixedThreshold",
    "StakesAdjusted",
    "BudgetAware",
    "Truncated",
    "reliability_diagram",
    "expected_calibration_error",
    "trust_sweep",
    "over_trust_index",
    "under_trust_index",
    "CostModel",
    "CostReport",
    "evaluate",
]
