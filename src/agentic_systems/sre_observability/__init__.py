"""SRE-Observability: a MAS-based unified observability platform.

Six observability layers (infra, network, platform, app, service, product)
emit telemetry. Per-layer observer agents detect anomalies; a boundary
assessment workflow quantifies observability power per layer *and* at
layer boundaries (the boundary problem); an incident-response loop
compares siloed vs unified (MAS) handling; a context-engineering step
unifies cross-layer alerts into single incident contexts; and a business-strategy
bridge optimizes the reliability-vs-innovation investment trade-off.

Public API:
    layers:     LAYERS, METRICS, SimResult, simulate
    observers:  Alert, ExportCfg, LayerObserver, observe_all,
                export_cfg, install_export_fix, reset_export_overrides
    boundary:   assess_layers, boundary_events, assess_boundaries,
                rank_boundaries
    response:   IncidentContext, build_contexts, triage, RUNBOOKS,
                SiloedResponder, UnifiedResponder
    strategy:   INITIATIVES, optimize, frontier, recommend, scorecard
"""

from .layers import LAYERS, METRICS, SimResult, simulate
from .observers import (
    Alert,
    ExportCfg,
    LayerObserver,
    export_cfg,
    install_export_fix,
    observe_all,
    reset_export_overrides,
)
from .boundary import (
    assess_boundaries,
    assess_layers,
    boundary_events,
    rank_boundaries,
)
from .response import (
    RUNBOOKS,
    IncidentContext,
    SiloedResponder,
    UnifiedResponder,
    build_contexts,
    triage,
)
from .strategy import INITIATIVES, baseline_scorecard, frontier, optimize, recommend, scorecard

__all__ = [
    "LAYERS",
    "METRICS",
    "SimResult",
    "simulate",
    "Alert",
    "ExportCfg",
    "LayerObserver",
    "export_cfg",
    "install_export_fix",
    "observe_all",
    "reset_export_overrides",
    "assess_boundaries",
    "assess_layers",
    "boundary_events",
    "rank_boundaries",
    "RUNBOOKS",
    "IncidentContext",
    "SiloedResponder",
    "UnifiedResponder",
    "build_contexts",
    "triage",
    "INITIATIVES",
    "baseline_scorecard",
    "frontier",
    "optimize",
    "recommend",
    "scorecard",
]
