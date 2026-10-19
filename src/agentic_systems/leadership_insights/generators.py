"""Seeded synthetic enterprise data with known ground truth.

Five source systems, one fictional company ("Acme"), 180 days of history:

- Jira: sprints, tickets, cycle times
- ServiceNow: incidents, SLA timelines, escalations, CSAT
- GitHub: pull requests, review latency, lead times
- Workday: headcount, license assignments + last-used, satisfaction, skills
- Planview: portfolio epics, budgets, spend

Four injected issues (recorded in ``ground_truth`` so experiments can score
recovery):
    1. bottleneck_team = "platform": PR review latency ~48h vs ~8h elsewhere,
       which depresses that team's deployment frequency.
    2. license waste: 12 PREMIUM_ANALYTICS seats ($180/mo) idle > 60 days,
       8 ENTERPRISE_SUITE seats ($95/mo) idle > 90 days.
    3. retention risk: "mobile" team satisfaction ~2.1/5 (org ~3.8); 5 people
       flagged as true attrition risks.
    4. escalation cluster: "checkout" service incidents escalate at ~30%
       (baseline ~8%), driven by repeat incidents on that service.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd

TEAMS = ["payments", "checkout", "search", "mobile", "platform", "data"]

SERVICES = {
    "payments": ["pay-api", "ledger"],
    "checkout": ["checkout-web", "cart-svc"],
    "search": ["search-api"],
    "mobile": ["ios-app", "android-app"],
    "platform": ["auth-svc", "deploy-infra"],
    "data": ["warehouse"],
}

LICENSES = {
    "ENTERPRISE_SUITE": 95.0,
    "PREMIUM_ANALYTICS": 180.0,
    "DEV_TOOLKIT": 45.0,
}

SKILLS = ["python", "java", "go", "react", "kubernetes", "ml",
          "sql", "terraform", "ios", "android"]

FIRST = ["Ava", "Liam", "Maya", "Noah", "Zoe", "Ethan", "Priya", "Lucas",
         "Sofia", "Owen", "Nina", "Kai", "Riya", "Mateo", "Ivy", "Omar",
         "Tara", "Jonas", "Alba", "Dev", "Mira", "Finn", "Lena", "Ravi",
         "Sana", "Theo", "Uma", "Vik", "Wren", "Yusuf", "Xena", "Arjun"]
LAST = ["Sharma", "Kim", "Patel", "Garcia", "Nguyen", "Singh", "Muller",
        "Rossi", "Silva", "Khan", "Ito", "Dubois", "Ali", "Chen", "Okafor",
        "Larsen", "Costa", "Weber", "Tanaka", "Adeyemi"]

BASE = datetime(2026, 4, 1)
DAYS = 180
SPRINT_DAYS = 14
N_SPRINTS = 12


def _names(rng, n):
    seen = set()
    out = []
    while len(out) < n:
        nm = f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        if nm not in seen:
            seen.add(nm)
            out.append(nm)
    # Force a same-name collision to stress entity resolution.
    out[0] = "Alex Kim"
    out[1] = "Alex Kim"
    return out


class EnterpriseGenerator:
    """Build the full synthetic enterprise. Deterministic given ``seed``."""

    def __init__(self, seed=7):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.ground_truth = {}

    # ------------------------------------------------------------------ org
    def _people(self):
        rng = self.rng
        rows = []
        pid = 0
        for ti, team in enumerate(TEAMS):
            names = _names(rng, 10)
            for k, nm in enumerate(names):
                if nm == "Alex Kim" and k == 0:
                    email, jira, gh = "alex.kim@acme.com", "alex.kim", "akimx"
                elif nm == "Alex Kim" and k == 1:
                    email, jira, gh = "alex.k@acme.com", "alex.k", "alexk-dev"
                else:
                    local = nm.lower().replace(" ", ".")
                    email = f"{local}@acme.com"
                    jira = local
                    gh = local.replace(".", "") + (str(rng.integers(2, 99))
                                                   if rng.random() < 0.25 else "")
                sat = float(np.clip(rng.normal(2.1 if team == "mobile" else 3.8,
                                               0.55), 1.0, 5.0))
                skills = sorted(rng.choice(SKILLS, size=int(rng.integers(2, 5)),
                                           replace=False).tolist())
                rows.append({
                    "person_id": f"P{pid:03d}", "name": nm, "email": email,
                    "jira_user": jira, "github_handle": gh, "team": team,
                    "role": "engineer" if k < 8 else ("manager" if k == 8
                                                      else "sre"),
                    "satisfaction": round(sat, 2), "skills": skills,
                    "attrition_risk": False,
                })
                pid += 1
        people = pd.DataFrame(rows)
        # Injected issue 3: 5 true attrition risks on the mobile team.
        mob = people[people.team == "mobile"].nsmallest(5, "satisfaction")
        people.loc[mob.index, "attrition_risk"] = True
        self.ground_truth["retention_risk_ids"] = set(mob.person_id)
        self.ground_truth["retention_risk_team"] = "mobile"
        return people

    # ------------------------------------------------------------------ jira
    def _jira(self, people):
        rng = self.rng
        rows = []
        n = 0
        for s in range(N_SPRINTS):
            start = BASE + timedelta(days=s * SPRINT_DAYS)
            for team in TEAMS:
                members = people[people.team == team]
                for _ in range(int(rng.poisson(14))):
                    a = members.iloc[int(rng.integers(len(members)))]
                    created = start + timedelta(
                        hours=float(rng.uniform(0, SPRINT_DAYS * 24)))
                    # Platform is slower to finish work (bottleneck knock-on).
                    slow = 1.6 if team == "platform" else 1.0
                    cyc_h = float(rng.lognormal(np.log(30 * slow), 0.7))
                    resolved = created + timedelta(hours=min(cyc_h, 400))
                    rows.append({
                        "key": f"{team[:3].upper()}-{1000 + n}",
                        "team": team, "assignee_jira": a.jira_user,
                        "assignee_email": a.email,
                        "created": created, "resolved": resolved,
                        "cycle_h": round((resolved - created).total_seconds() / 3600, 1),
                        "story_points": int(rng.choice([1, 2, 3, 5, 8],
                                                       p=[.2, .3, .25, .15, .1])),
                        "ticket_type": rng.choice(["story", "bug", "task"],
                                                  p=[.55, .25, .20]),
                        "labels": sorted(rng.choice(
                            SKILLS, size=int(rng.integers(1, 3)),
                            replace=False).tolist()),
                        "sprint": s + 1,
                    })
                    n += 1
        jira = pd.DataFrame(rows)
        # One Jira row loses its email join key: the resolver must fall back
        # to handle matching for it.
        jira.loc[jira.index[5], "assignee_email"] = np.nan
        return jira

    # ---------------------------------------------------------------- github
    def _github(self, people):
        rng = self.rng
        rows = []
        n = 0
        self._rev_means = {}
        for team in TEAMS:
            members = people[people.team == team]
            # Injected issue 1: platform reviews take ~48h; others ~8h.
            rev_mean = 48.0 if team == "platform" else float(rng.uniform(6, 10))
            self._rev_means[team] = rev_mean
            for _ in range(int(rng.poisson(190))):
                a = members.iloc[int(rng.integers(len(members)))]
                opened = BASE + timedelta(
                    hours=float(rng.uniform(0, DAYS * 24)))
                rev_h = float(rng.lognormal(np.log(rev_mean), 0.6))
                merged = opened + timedelta(hours=rev_h + float(rng.uniform(1, 6)))
                rows.append({
                    "pr_id": f"PR-{n:05d}", "repo": f"{team}-svc",
                    "author_gh": a.github_handle, "author_email": a.email,
                    "team": team,
                    "opened": opened, "merged": merged,
                    "review_h": round(rev_h, 1),
                    "lead_h": round((merged - opened).total_seconds() / 3600, 1),
                    "additions": int(rng.lognormal(5, 1)),
                })
                n += 1
        gh = pd.DataFrame(rows)
        # A few GitHub rows lose their email join key as well.
        gh.loc[gh.index[11], "author_email"] = np.nan
        gh.loc[gh.index[47], "author_email"] = np.nan
        self.ground_truth["bottleneck_team"] = "platform"
        self.ground_truth["true_review_mean"] = dict(self._rev_means)
        return gh

    # ------------------------------------------------------------- servicenow
    def _snow(self):
        rng = self.rng
        rows = []
        n = 0
        for team, svcs in SERVICES.items():
            for svc in svcs:
                lam = 0.55 if svc == "checkout-web" else 0.28  # incidents/day
                t = 0.0
                hist = []  # (opened_h, resolved_h) for overlap checks
                while True:
                    t += float(rng.exponential(1.0 / lam))
                    if t > DAYS:
                        break
                    opened = BASE + timedelta(days=t)
                    sev = int(rng.choice([1, 2, 3, 4], p=[.06, .22, .42, .30]))
                    res_h = float(rng.lognormal(np.log({1: 9, 2: 5, 3: 2.5,
                                                        4: 1.2}[sev]), 0.7))
                    resolved = opened + timedelta(hours=res_h)
                    # Injected issue 4: checkout escalates ~30%, baseline ~8%.
                    # More severe incidents escalate more often, and an
                    # incident that overlaps an still-open incident on the
                    # same service (repeat offender) escalates more often —
                    # real signals for the escalation predictor to learn.
                    sev_mult = {1: 2.0, 2: 1.4, 3: 1.0, 4: 0.6}[sev]
                    esc_p = (0.30 if svc == "checkout-web" else 0.08) * sev_mult
                    overlap = any(o <= t * 24 < r and (t * 24 - o) <= 48
                                  for o, r in hist)
                    if overlap:
                        esc_p *= 1.8
                    esc_p = min(0.70, esc_p)
                    escalated = bool(rng.random() < esc_p)
                    csat = float(np.clip(
                        rng.normal(4.4 - 0.35 * np.log1p(res_h)
                                   - (0.9 if escalated else 0.0), 0.8), 1, 5))
                    rows.append({
                        "inc_id": f"INC{n:05d}", "service": svc, "team": team,
                        "opened": opened, "resolved": resolved,
                        "resolve_h": round(res_h, 2), "severity": sev,
                        "escalated": escalated,
                        "csat": round(csat, 1) if rng.random() < 0.7 else np.nan,
                    })
                    hist.append((t * 24, t * 24 + res_h))
                    n += 1
        snow = pd.DataFrame(rows)
        self.ground_truth["escalation_cluster_service"] = "checkout-web"
        return snow

    # --------------------------------------------------------------- workday
    def _workday(self, people):
        rng = self.rng
        rows = []
        waste_premium, waste_suite = [], []
        for _, p in people.iterrows():
            lic = []
            lic.append({"type": "ENTERPRISE_SUITE",
                        "last_used_days_ago": int(rng.integers(0, 30))})
            if p.role in ("engineer", "sre"):
                lic.append({"type": "DEV_TOOLKIT",
                            "last_used_days_ago": int(rng.integers(0, 14))})
            if rng.random() < 0.45:
                lic.append({"type": "PREMIUM_ANALYTICS",
                            "last_used_days_ago": int(rng.integers(0, 45))})
            rows.append({
                "employee_id": p.person_id, "name": p.name, "email": p.email,
                "team": p.team, "role": p.role,
                "satisfaction": p.satisfaction, "skills": p.skills,
                "attrition_risk": p.attrition_risk, "licenses": lic,
            })
        wd = pd.DataFrame(rows)
        # Injected issue 2: idle expensive seats.
        prem_idx = wd[wd.licenses.map(
            lambda L: any(x["type"] == "PREMIUM_ANALYTICS" for x in L))].index
        waste_p = rng.choice(prem_idx, size=12, replace=False)
        for i in waste_p:
            L = wd.at[i, "licenses"]
            for x in L:
                if x["type"] == "PREMIUM_ANALYTICS":
                    x["last_used_days_ago"] = int(rng.integers(61, 120))
            waste_premium.append(wd.at[i, "employee_id"])
        suite_idx = wd.index.difference(waste_p)
        waste_s = rng.choice(suite_idx, size=8, replace=False)
        for i in waste_s:
            L = wd.at[i, "licenses"]
            for x in L:
                if x["type"] == "ENTERPRISE_SUITE":
                    x["last_used_days_ago"] = int(rng.integers(91, 150))
            waste_suite.append(wd.at[i, "employee_id"])
        self.ground_truth["waste_premium_ids"] = set(waste_premium)
        self.ground_truth["waste_suite_ids"] = set(waste_suite)
        return wd

    # -------------------------------------------------------------- planview
    def _planview(self):
        rng = self.rng
        rows = []
        for e in range(24):
            team = TEAMS[e % len(TEAMS)]
            budget = float(rng.uniform(80, 400)) * 1000
            spend = float(budget * rng.uniform(0.55, 1.15))
            rows.append({
                "epic": f"EPIC-{e + 1:03d}", "team": team,
                "budget": round(budget), "spend": round(spend),
                "status": rng.choice(["on-track", "at-risk", "delayed"],
                                     p=[.6, .25, .15]),
            })
        return pd.DataFrame(rows)

    # ------------------------------------------------------------------ main
    def generate(self):
        people = self._people()
        data = {
            "people": people,                       # canonical identities
            "jira": self._jira(people),
            "github": self._github(people),
            "snow": self._snow(),
            "workday": self._workday(people),
            "planview": self._planview(),
        }
        return data, self.ground_truth


def generate_enterprise(seed=7):
    """Convenience entry point: returns (data, ground_truth)."""
    return EnterpriseGenerator(seed).generate()
