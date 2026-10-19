"""CTO lens: DORA metrics, PR analytics, bottleneck detection."""
from __future__ import annotations

import numpy as np
import pandas as pd


def dora_metrics(unified):
    """Deployment frequency, lead time, MTTR, change failure rate per team."""
    gh, snow = unified["github"], unified["snow"]
    weeks = (gh.merged.max() - gh.merged.min()).days / 7.0
    rows = []
    for team in sorted(gh.team.unique()):
        g = gh[gh.team == team]
        deploys = g[g.merged.notna()]
        dep_freq = len(deploys) / weeks if weeks else 0.0
        lead_p50 = deploys.lead_h.median()
        # Change failure rate: deploy-days followed by an incident within 24h
        # on a service owned by the team.
        svcs = unified["snow"][unified["snow"].team == team].service.unique()
        deploy_days = set(deploys.merged.dt.date)
        fails = 0
        for d in deploy_days:
            day_end = pd.Timestamp(d) + pd.Timedelta(days=1)
            inc = snow[(snow.service.isin(svcs)) &
                       (snow.opened >= pd.Timestamp(d)) &
                       (snow.opened < day_end)]
            if len(inc):
                fails += 1
        cfr = fails / len(deploy_days) if deploy_days else 0.0
        s = snow[snow.team == team]
        mttr = s.resolve_h.median() if len(s) else np.nan
        rows.append({"team": team,
                     "deploys_per_week": round(dep_freq, 2),
                     "lead_time_p50_h": round(float(lead_p50), 1),
                     "change_fail_rate": round(cfr, 3),
                     "mttr_h": round(float(mttr), 1) if pd.notna(mttr) else None,
                     "n_prs": len(g), "n_incidents": len(s)})
    return pd.DataFrame(rows).set_index("team")


def pr_analytics(unified):
    """Review latency / cycle time distributions per team."""
    gh = unified["github"]
    rows = []
    for team in sorted(gh.team.unique()):
        g = gh[gh.team == team]
        rows.append({"team": team,
                     "review_p50_h": round(g.review_h.median(), 1),
                     "review_p95_h": round(g.review_h.quantile(0.95), 1),
                     "review_mean_h": round(g.review_h.mean(), 1),
                     "cycle_p50_h": round(g.lead_h.median(), 1)})
    return pd.DataFrame(rows).set_index("team")


def detect_bottlenecks(unified, review_p95_h_threshold=24.0):
    """Flag teams whose review latency starves deployment frequency.

    A bottleneck team has p95 review latency above the threshold AND
    deployment frequency below the org median.
    """
    dora = dora_metrics(unified)
    pr = pr_analytics(unified)
    med_freq = dora.deploys_per_week.median()
    out = []
    for team in dora.index:
        slow = pr.loc[team, "review_p95_h"] > review_p95_h_threshold
        rare = dora.loc[team, "deploys_per_week"] < med_freq
        out.append({"team": team,
                    "review_p95_h": pr.loc[team, "review_p95_h"],
                    "deploys_per_week": dora.loc[team, "deploys_per_week"],
                    "org_median_deploys": round(med_freq, 2),
                    "bottleneck": bool(slow and rare)})
    df = pd.DataFrame(out).set_index("team")
    return df
