"""Behavioral regression: catch functional drift across model versions.

System 13 (ideology-mirror) measures *ideological* drift; this system
measures *functional* drift. The vendor ships a new model version, your
agent's task success silently changes, tool-call formats drift, and no
test catches it before production. The answer is a regression discipline
for agents: a frozen task battery, paired drift detection against the
pinned baseline, staged canary analysis, and a pin / auto-adopt /
rollback policy with rationale.

All model versions here are simulated stand-ins with parameterized
behavioral shifts (see the project README's honest limits): the measured
contribution is the methodology, not claims about any real vendor model.

Public API:
    versions:  ModelVersion, VERSIONS, GROUND_TRUTH_POLICY, SimulatedAgent,
               Task, TaskResult, CATEGORIES
    battery:   build_battery, run_battery, BatteryResult
    detector:  DriftDetector, VersionReport, MetricDiff
    canary:    CanaryAnalyzer, CanaryReport, CanaryStageResult
    policy:    PolicyEngine, PolicyDecision
"""

from .battery import BatteryResult, build_battery, run_battery
from .canary import CanaryAnalyzer, CanaryReport, CanaryStageResult
from .detector import CORRECTNESS_METRICS, DriftDetector, MetricDiff, VersionReport
from .policy import PolicyDecision, PolicyEngine
from .versions import (
    CATEGORIES,
    GROUND_TRUTH_POLICY,
    VERSIONS,
    ModelVersion,
    SimulatedAgent,
    Task,
    TaskResult,
)

__all__ = [
    "CATEGORIES",
    "GROUND_TRUTH_POLICY",
    "VERSIONS",
    "BatteryResult",
    "CanaryAnalyzer",
    "CanaryReport",
    "CanaryStageResult",
    "CORRECTNESS_METRICS",
    "DriftDetector",
    "MetricDiff",
    "ModelVersion",
    "PolicyDecision",
    "PolicyEngine",
    "SimulatedAgent",
    "Task",
    "TaskResult",
    "VersionReport",
    "build_battery",
    "run_battery",
]
