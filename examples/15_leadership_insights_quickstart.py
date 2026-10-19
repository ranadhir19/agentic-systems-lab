"""Leadership-insights quickstart: one insight per leadership lens.

Builds a synthetic enterprise (180 days, 5 sources, 4 planted problems),
joins the sources, and prints one headline insight for the CTO, CFO,
client-service lead, and HR lead — plus one insight that only exists
because the sources were joined.

Run:  PYTHONPATH=src python3 examples/15_leadership_insights_quickstart.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agentic_systems.leadership_insights import (
    generate_enterprise, build_unified,
    detect_bottlenecks, reclaim_opportunities, csat_drivers,
    retention_risk, run_insights,
)


def main() -> None:
    data, gt = generate_enterprise(seed=7)
    u = build_unified(data)
    print(f"enterprise: {len(u['jira'])} tickets, {len(u['github'])} PRs, "
          f"{len(u['snow'])} incidents, {len(u['workday'])} employees")

    # CTO lens: where is delivery bottlenecked?
    bn = detect_bottlenecks(u)
    teams = bn[bn.bottleneck].index.tolist()
    print(f"\nCTO: bottleneck team(s) = {teams} "
          f"(p95 review {bn.loc[teams[0], 'review_p95_h']:.0f}h, "
          f"{bn.loc[teams[0], 'deploys_per_week']:.1f} deploys/wk)")
    assert teams == [gt["bottleneck_team"]]

    # CFO lens: where is money wasted?
    _, summary = reclaim_opportunities(u)
    print(f"CFO: {summary['n_seats']} idle seats = "
          f"${summary['annual_saving']:,.0f}/yr reclaimable")

    # Client-service lens: what drives CSAT?
    cd = csat_drivers(u)
    print(f"Client: CSAT vs log(resolution time) r={cd['corr_csat_logresolve']:.2f}; "
          f"escalated CSAT {cd['csat_escalated_mean']:.1f} vs "
          f"{cd['csat_clean_mean']:.1f} clean")

    # HR lens: who is at risk?
    rr = retention_risk(u)
    top = rr.head(3)
    print(f"HR: top retention risks = "
          f"{', '.join(top.person_id)} (team {top.iloc[0].team})")

    # Cross-source: the insight no single source can produce.
    ins = run_insights(u, mode="integrated")
    multi = [i for i in ins if i["n_sources"] > 1][0]
    print(f"\nJoined insight [{', '.join(multi['sources']) }]: {multi['title']}")
    print(f"  {multi['finding']}")
    print(f"  Impact: {multi['impact']}")
    print("\nAll four lenses recovered their planted problems.")


if __name__ == "__main__":
    main()
