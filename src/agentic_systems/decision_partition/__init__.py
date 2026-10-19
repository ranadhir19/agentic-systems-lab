"""Decision Partition: complexity-scored allocation of decisions to agents.

Given decisions classified as simple or composite, score each by the
number of distinct state groups influencing it (times a category weight),
then partition them across the minimum viable set of agents:

    score >= 10        -> dedicated agent
    5 <= score < 10    -> shared agent with similar-domain decisions
    score < 5          -> grouped into one general agent

Public API:
    decisions: Decision, SIMPLE, COMPOSITE
    scoring:   Scorer, complexity_score, complexity_level, effective_score,
               HIGH, MEDIUM, LOW
    partition: partition_decisions, Partition, AgentAssignment,
               partition_metrics, cross_agent_handoffs, assignment_churn,
               default_namer
    dynamic:   DynamicPartitioner, EvidenceEvent, RepartitionRecord
    planner:   topological_stages, stage_partitions, critical_path_score,
               workflow_plan
    catalog:   insurance_claim_decisions, insurance_demo, insurance_namer
"""

from .decisions import COMPOSITE, SIMPLE, Decision
from .scoring import (
    HIGH,
    LOW,
    MEDIUM,
    Scorer,
    complexity_level,
    complexity_score,
    effective_score,
)
from .partition import (
    AgentAssignment,
    Partition,
    assignment_churn,
    cross_agent_handoffs,
    default_namer,
    partition_decisions,
    partition_metrics,
)
from .dynamic import DynamicPartitioner, EvidenceEvent, RepartitionRecord
from .planner import (
    critical_path_score,
    stage_partitions,
    topological_stages,
    workflow_plan,
)
from .catalog import (
    insurance_claim_decisions,
    insurance_demo,
    insurance_namer,
)

__all__ = [
    "Decision",
    "SIMPLE",
    "COMPOSITE",
    "Scorer",
    "complexity_score",
    "complexity_level",
    "effective_score",
    "HIGH",
    "MEDIUM",
    "LOW",
    "AgentAssignment",
    "Partition",
    "partition_decisions",
    "partition_metrics",
    "cross_agent_handoffs",
    "assignment_churn",
    "default_namer",
    "DynamicPartitioner",
    "EvidenceEvent",
    "RepartitionRecord",
    "topological_stages",
    "stage_partitions",
    "critical_path_score",
    "workflow_plan",
    "insurance_claim_decisions",
    "insurance_demo",
    "insurance_namer",
]
