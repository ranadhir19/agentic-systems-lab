"""Cross-source insight engine: findings that only exist when sources join.

Each insight declares the sources it needs. The engine can run in
``integrated`` mode (all sources) or ``siloed`` mode (each source alone),
which lets experiments measure exactly what siloed analytics misses.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .cfo import reclaim_opportunities
from .cto import dora_metrics, pr_analytics
from .hr import retention_risk


class Insight:
    def __init__(self, title, sources, finding, impact, severity="info"):
        self.title = title
        self.sources = tuple(sources)
        self.finding = finding
        self.impact = impact
        self.severity = severity

    def to_dict(self):
        return {"title": self.title, "sources": list(self.sources),
                "finding": self.finding, "impact": self.impact,
                "severity": self.severity,
                "n_sources": len(self.sources)}


class CrossSourceEngine:
    def __init__(self, unified):
        self.u = unified

    # ------------------------------------------------------------ insights
    def review_latency_vs_change_failure(self):
        """Test whether slow reviews coincide with more change failures.

        Needs GitHub (review latency) + ServiceNow (incidents after deploys).
        The engine reports the measured direction honestly — in this run
        the link is absent/negative, which is itself a finding: it rules
        out review latency as the driver and points at incident base rates.
        """
        dora = dora_metrics(self.u)
        pr = pr_analytics(self.u)
        slow = pr[pr.review_p95_h > pr.review_p95_h.median()].index
        fast = pr[~pr.index.isin(slow)].index
        slow_cfr = dora.loc[slow, "change_fail_rate"].mean()
        fast_cfr = dora.loc[fast, "change_fail_rate"].mean()
        lift = (slow_cfr - fast_cfr) / fast_cfr if fast_cfr else float("nan")
        if lift > 0.2:
            title = "Slow-review teams fail changes more often"
            severity = "warning"
        elif lift < -0.2:
            title = "Slow reviews do NOT explain change failures here"
            severity = "info"
        else:
            title = "Review latency vs change failure: no clear link"
            severity = "info"
        return Insight(
            title,
            ["github", "snow"],
            f"Teams above median p95 review latency ({pr.review_p95_h.median():.0f}h) "
            f"have change-failure rate {slow_cfr:.1%} vs {fast_cfr:.1%} for "
            f"fast reviewers (lift {lift:+.0%}).",
            f"lift {lift:+.0%} (slow vs fast)",
            severity=severity)

    def deploy_frequency_vs_incidents(self):
        """Delivery speed vs stability tradeoff per team.

        Needs GitHub (deploys) + ServiceNow (incidents).
        """
        dora = dora_metrics(self.u)
        corr = dora.deploys_per_week.corr(dora.n_incidents)
        worst = dora.sort_values("change_fail_rate", ascending=False).iloc[0]
        return Insight(
            "Speed/stability tradeoff by team",
            ["github", "snow"],
            f"Deploy frequency vs incident count correlation r={corr:.2f}. "
            f"Highest change-failure rate: {worst.name} at {worst.change_fail_rate:.1%}.",
            f"{worst.name}: {worst.change_fail_rate:.1%} change failure rate",
            severity="warning")

    def license_waste(self):
        """Idle seats, in dollars. Needs Workday only — the siloed control."""
        _, summary = reclaim_opportunities(self.u)
        return Insight(
            "Idle software licenses are burning cash",
            ["workday"],
            f"{summary['n_seats']} seats idle > 60 days.",
            f"${summary['annual_saving']:,.0f}/yr reclaimable",
            severity="warning" if summary["annual_saving"] > 5000 else "info")

    def license_waste_validated_by_activity(self):
        """Confirm idle licenses against actual engineering activity.

        Needs Workday (license last-used) + GitHub/Jira (real activity):
        a seat is only reclaimable if the person is ALSO inactive in
        engineering systems — catches stale last-used timestamps.
        """
        df, _ = reclaim_opportunities(self.u)
        gh = self.u["github"]
        j = self.u["jira"]
        cutoff = gh.merged.max() - pd.Timedelta(days=60)
        active_ids = set(gh[gh.merged > cutoff].person_id.dropna()) | \
            set(j[j.resolved > cutoff].person_id.dropna())
        confirmed = df[~df.employee_id.isin(active_ids)]
        saving = float(confirmed.annual_saving.sum()) if len(confirmed) else 0.0
        return Insight(
            "Idle licenses confirmed by engineering inactivity",
            ["workday", "github", "jira"],
            f"{len(confirmed)}/{len(df)} idle-license holders also show no "
            f"engineering activity in 60 days — safe to reclaim.",
            f"${saving:,.0f}/yr confirmed reclaimable",
            severity="warning")

    def escalation_staffing(self):
        """Escalation clusters where the owning team is stretched.

        Needs ServiceNow (escalations) + Workday (satisfaction as a
        stretch proxy) + Jira (workload).
        """
        s = self.u["snow"]
        esc = s.groupby("team").escalated.mean().sort_values(ascending=False)
        top_team, top_rate = esc.index[0], esc.iloc[0]
        org_rate = s.escalated.mean()
        sat = self.u["workday"].groupby("team").satisfaction.mean()
        return Insight(
            "Escalations concentrate where teams are stretched",
            ["snow", "workday", "jira"],
            f"{top_team} escalates at {top_rate:.1%} vs {org_rate:.1%} org-wide; "
            f"team satisfaction {sat[top_team]:.1f}/5 "
            f"(org {sat.mean():.1f}).",
            f"{top_rate / org_rate:.1f}x org escalation rate on {top_team}",
            severity="critical" if top_rate > 2 * org_rate else "warning")

    def retention_cost(self):
        """Retention risk translated to replacement cost.

        Needs Workday (satisfaction, risk flags). Replacing an engineer
        costs ~$75k fully loaded (recruiting + ramp).
        """
        df = retention_risk(self.u)
        at_risk = df[df.risk_score > 0.7]
        exposure = len(at_risk) * 75000
        teams = at_risk.team.value_counts()
        top = teams.index[0] if len(teams) else "none"
        return Insight(
            "Retention risk has a dollar value",
            ["workday", "jira"],
            f"{len(at_risk)} people score risk > 0.7, concentrated on "
            f"{top} ({teams.iloc[0] if len(teams) else 0} people).",
            f"${exposure:,.0f} replacement exposure",
            severity="critical" if exposure > 200000 else "warning")

    def satisfaction_productivity_link(self):
        """Satisfaction and throughput move together — or don't.

        Needs Workday (satisfaction) + Jira (points closed).
        """
        from .hr import productivity_satisfaction
        ps = productivity_satisfaction(self.u)
        c = ps["corr_points_satisfaction"]
        return Insight(
            "Satisfaction/throughput link",
            ["workday", "jira"],
            f"Person-level correlation between satisfaction and story "
            f"points/sprint: r={c:.2f}.",
            f"r={c:.2f}",
            severity="info")

    # ------------------------------------------------------------------ run
    def run(self, mode="integrated"):
        """Run all insights; in ``siloed`` mode keep only single-source ones."""
        methods = [self.review_latency_vs_change_failure,
                   self.deploy_frequency_vs_incidents,
                   self.license_waste,
                   self.license_waste_validated_by_activity,
                   self.escalation_staffing,
                   self.retention_cost,
                   self.satisfaction_productivity_link]
        out = []
        for m in methods:
            ins = m()
            if mode == "siloed" and ins.to_dict()["n_sources"] > 1:
                continue
            out.append(ins.to_dict())
        return out


def run_insights(unified, mode="integrated"):
    return CrossSourceEngine(unified).run(mode=mode)
