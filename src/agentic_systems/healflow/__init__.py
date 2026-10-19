"""HealFlow: a self-healing workflow runtime.

Contracts guard every step, checkpoints make state restorable, a causal
diagnoser classifies failures, the repairer applies the smallest viable
repair (retry / substitute / skip / compensate-abort), recovery is verified
before the run is declared done, and a repair memory records what worked so
recurring faults heal faster.

Public API:
    workflow:   WorkflowDef, StepDef, RunState
    runtime:    HealFlowRuntime, RunReport, RetryBaseline, ReplanBaseline
    diagnosis:  Diagnoser, Diagnosis
    repair:     RepairMemory
    faults:     FaultInjector, ToolOutage, ToolFailed
    catalog:    build_injector, PREDS, SUBSTITUTES,
                etl_flow, order_flow, research_flow
"""

from .workflow import WorkflowDef, StepDef, RunState
from .runtime import HealFlowRuntime, RunReport, RetryBaseline, ReplanBaseline
from .diagnosis import Diagnoser, Diagnosis
from .repair import RepairMemory
from .faults import FaultInjector, ToolOutage, ToolFailed
from .catalog import (
    build_injector,
    PREDS,
    SUBSTITUTES,
    etl_flow,
    order_flow,
    research_flow,
)

__all__ = [
    "WorkflowDef",
    "StepDef",
    "RunState",
    "HealFlowRuntime",
    "RunReport",
    "RetryBaseline",
    "ReplanBaseline",
    "Diagnoser",
    "Diagnosis",
    "RepairMemory",
    "FaultInjector",
    "ToolOutage",
    "ToolFailed",
    "build_injector",
    "PREDS",
    "SUBSTITUTES",
    "etl_flow",
    "order_flow",
    "research_flow",
]
