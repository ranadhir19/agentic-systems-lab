"""Leadership Insights: turn integrated enterprise data into leadership decisions.

Jira + ServiceNow + GitHub + Workday + Planview are each useful alone, but
the decisions leadership actually needs — where is delivery bottlenecked,
where is money wasted on licenses, which clients are about to escalate,
who is about to quit — only emerge when the sources are joined.

Public API:
    generators: EnterpriseGenerator, generate_enterprise
    integrate:  EntityResolver, build_unified
    cto:        dora_metrics, pr_analytics, detect_bottlenecks
    cfo:        license_report, reclaim_opportunities
    client:     resolution_timelines, csat_drivers, EscalationPredictor
    hr:         productivity_satisfaction, skill_gaps, retention_risk
    cross:      CrossSourceEngine, run_insights
"""

from .generators import EnterpriseGenerator, generate_enterprise
from .integrate import EntityResolver, build_unified, resolution_scores
from .cto import dora_metrics, pr_analytics, detect_bottlenecks
from .cfo import license_report, reclaim_opportunities
from .client import resolution_timelines, csat_drivers, EscalationPredictor
from .hr import (productivity_satisfaction, skill_gaps, retention_risk,
                 retention_scores)
from .cross import CrossSourceEngine, run_insights

__all__ = [
    "EnterpriseGenerator",
    "generate_enterprise",
    "EntityResolver",
    "build_unified",
    "resolution_scores",
    "dora_metrics",
    "pr_analytics",
    "detect_bottlenecks",
    "license_report",
    "reclaim_opportunities",
    "resolution_timelines",
    "csat_drivers",
    "EscalationPredictor",
    "productivity_satisfaction",
    "skill_gaps",
    "retention_risk",
    "retention_scores",
    "CrossSourceEngine",
    "run_insights",
]
