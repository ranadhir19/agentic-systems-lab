"""CFO lens: license utilization, cost, reclaim recommendations."""
from __future__ import annotations

import pandas as pd

from .generators import LICENSES


def license_report(unified, active_days=30):
    """Utilization and cost per license type."""
    wd = unified["workday"]
    rows = []
    for ltype, cost in LICENSES.items():
        assigned, active = 0, 0
        for _, r in wd.iterrows():
            for lic in r.licenses:
                if lic["type"] == ltype:
                    assigned += 1
                    if lic["last_used_days_ago"] <= active_days:
                        active += 1
        rows.append({"license": ltype, "cost_per_mo": cost,
                     "assigned": assigned, "active": active,
                     "utilization": round(active / assigned, 3) if assigned else 0.0,
                     "monthly_cost": round(assigned * cost, 2),
                     "wasted_monthly": round((assigned - active) * cost, 2)})
    return pd.DataFrame(rows).set_index("license")


def reclaim_opportunities(unified, idle_days=60):
    """Seats idle longer than ``idle_days``: who, what, dollar savings."""
    wd = unified["workday"]
    rows = []
    for _, r in wd.iterrows():
        for lic in r.licenses:
            if lic["last_used_days_ago"] > idle_days:
                rows.append({
                    "employee_id": r.employee_id, "name": r.name,
                    "team": r.team, "license": lic["type"],
                    "idle_days": lic["last_used_days_ago"],
                    "monthly_saving": LICENSES[lic["type"]],
                    "annual_saving": LICENSES[lic["type"]] * 12,
                })
    df = pd.DataFrame(rows)
    if len(df):
        df = df.sort_values("annual_saving", ascending=False).reset_index(drop=True)
    summary = {
        "n_seats": len(df),
        "annual_saving": round(float(df.annual_saving.sum()), 2) if len(df) else 0.0,
        "monthly_saving": round(float(df.monthly_saving.sum()), 2) if len(df) else 0.0,
    }
    return df, summary
