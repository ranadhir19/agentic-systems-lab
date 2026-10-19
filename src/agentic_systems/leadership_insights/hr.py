"""HR lens: productivity vs satisfaction, skill gaps, retention risk."""
from __future__ import annotations

import numpy as np
import pandas as pd


def productivity_satisfaction(unified):
    """Story points closed per person per sprint vs satisfaction."""
    j = unified["jira"]
    per = j.groupby("person_id").agg(points=("story_points", "sum"),
                                     team=("person_team", "first")).reset_index()
    per["points_per_sprint"] = per.points / 12.0
    wd = unified["workday"][["employee_id", "satisfaction"]].rename(
        columns={"employee_id": "person_id"})
    m = per.merge(wd, on="person_id", how="left")
    corr = m.points_per_sprint.corr(m.satisfaction)
    by_team = m.groupby("team").agg(satisfaction=("satisfaction", "mean"),
                                    points_per_sprint=("points_per_sprint",
                                                       "mean"),
                                    n=("person_id", "size")).round(2)
    return {"corr_points_satisfaction": round(float(corr), 3),
            "by_team": by_team, "person": m}


def skill_gaps(unified, top_k=5):
    """Skills demanded by tickets vs skills held by the org.

    Demand = label frequency on Jira tickets; supply = headcount holding
    the skill. Gap = demand share - supply share.
    """
    j = unified["jira"]
    demand = {}
    for _, r in j.iterrows():
        for lab in r.labels:
            demand[lab] = demand.get(lab, 0) + 1
    supply = {}
    for _, r in unified["workday"].iterrows():
        for sk in r.skills:
            supply[sk] = supply.get(sk, 0) + 1
    tot_d = sum(demand.values()) or 1
    n_people = len(unified["workday"])
    rows = []
    for sk in sorted(set(demand) | set(supply)):
        d = demand.get(sk, 0) / tot_d
        s = supply.get(sk, 0) / n_people
        rows.append({"skill": sk, "demand_share": round(d, 3),
                     "supply_share": round(s, 3),
                     "gap": round(d - s, 3)})
    df = pd.DataFrame(rows).sort_values("gap", ascending=False)
    return df.head(top_k).reset_index(drop=True), df


def retention_risk(unified):
    """Risk score per person: low satisfaction + high workload + low tenure
    signal. Here workload = story points; tenure signal is omitted (no
    tenure field) so the score is satisfaction + workload driven.
    """
    ps = productivity_satisfaction(unified)["person"]
    wd = unified["workday"]
    m = ps.merge(wd[["employee_id", "satisfaction", "attrition_risk"]].rename(
        columns={"employee_id": "person_id", "satisfaction": "sat"}),
        on="person_id", how="left")
    sat_z = (m.sat - m.sat.mean()) / (m.sat.std() or 1)
    load_z = (m.points_per_sprint - m.points_per_sprint.mean()) / \
             (m.points_per_sprint.std() or 1)
    m["risk_score"] = (-sat_z + 0.5 * load_z)
    m["risk_score"] = (m.risk_score - m.risk_score.min()) / \
                      (m.risk_score.max() - m.risk_score.min() + 1e-9)
    m = m.sort_values("risk_score", ascending=False).reset_index(drop=True)
    return m[["person_id", "team", "sat", "points_per_sprint",
              "risk_score", "attrition_risk"]]


def retention_scores(df, k=10):
    """Precision/recall of the top-k risk list vs ground-truth flags."""
    topk = df.head(k)
    tp = int(topk.attrition_risk.sum())
    total_true = int(df.attrition_risk.sum())
    prec = tp / k if k else 0.0
    rec = tp / total_true if total_true else 0.0
    return {"precision_at_k": round(prec, 3), "recall_at_k": round(rec, 3),
            "k": k, "n_true": total_true}
