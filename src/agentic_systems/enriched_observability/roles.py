"""Role-specific enriched views.

Each role receives only the decision-relevant slice of the enriched
chain. `relevance_score` implements the experiment-(e) rubric: for each
role a set of required facts is defined; score = fraction of required
facts present minus a penalty for irrelevant fields. The raw-dump
baseline (everything for everyone) scores poorly because of the noise
penalty.
"""
from __future__ import annotations

ROLES = ["cto", "sre_director", "devops_lead", "eng_manager", "engineer"]

# Required facts per role (keys into the analytic context).
REQUIRED = {
    "cto": {"revenue_at_risk_m_per_hr", "impact_score", "recommended_action",
            "failure_probability"},
    "sre_director": {"slo_success_now", "error_budget_burn_per_h",
                     "time_to_breach_min", "recommended_action",
                     "failure_probability"},
    "devops_lead": {"deploy_correlated", "recommended_action",
                    "root_cause_confidence", "failure_probability"},
    "eng_manager": {"mttr_proxy_min", "affected_services",
                    "recommended_action", "impact_score"},
    "engineer": {"root_cause_narrative", "correlated_raw_signals",
                 "recommended_action", "root_cause_confidence"},
}

# Fields that are noise for a role (penalized if present).
IRRELEVANT = {
    "cto": {"correlated_raw_signals", "root_cause_narrative", "z_series"},
    "sre_director": {"revenue_at_risk_m_per_hr", "correlated_raw_signals"},
    "devops_lead": {"revenue_at_risk_m_per_hr", "csat_now"},
    "eng_manager": {"z_series", "correlated_raw_signals"},
    "engineer": {"revenue_at_risk_m_per_hr", "csat_now"},
}


def build_context(data: dict, chain: list[dict], analytics: dict) -> dict:
    """Assemble the full analytic context from pipeline outputs."""
    app = analytics.get("application", {})
    sre = analytics.get("sre", {})
    biz = analytics.get("business", {})
    ctx = {
        "revenue_at_risk_m_per_hr": round(
            float(biz.get("revenue_loss_per_hr_now", 0.0)), 2),
        "impact_score": biz.get("impact_score", 0.0),
        "recommended_action": biz.get("recommended_action",
                                      app.get("recommended_action", "")),
        "failure_probability": max(
            a.get("failure_probability", 0.0) for a in analytics.values()
        ) if analytics else 0.0,
        "slo_success_now": round(float(sre.get("slo_success_now", 1.0)), 4),
        "error_budget_burn_per_h": round(
            float(sre.get("error_budget_burn_per_h", 0.0)), 2),
        "time_to_breach_min": sre.get("time_to_breach_min"),
        "deploy_correlated": app.get("deploy_correlated", False),
        "root_cause_confidence": max(
            a.get("root_cause_confidence", 0.0) for a in analytics.values()
        ) if analytics else 0.0,
        "mttr_proxy_min": sre.get("mttr_proxy_min", 0),
        "affected_services": ["checkout", "payment-service", "cdn-edge"],
        "root_cause_narrative": analytics.get("application", {}).get(
            "narrative", ""),
        "correlated_raw_signals": [f"{c['layer']}:{c['metric']}"
                                   for c in chain],
        "csat_now": round(float(biz.get("csat_now", 85.0)), 1),
        "chain_length": len(chain),
    }
    return ctx


# Which context keys each role's view keeps.
VIEW_KEYS = {
    "cto": ["revenue_at_risk_m_per_hr", "impact_score", "failure_probability",
            "recommended_action", "chain_length"],
    "sre_director": ["slo_success_now", "error_budget_burn_per_h",
                     "time_to_breach_min", "failure_probability",
                     "recommended_action", "chain_length"],
    "devops_lead": ["deploy_correlated", "root_cause_confidence",
                    "failure_probability", "recommended_action"],
    "eng_manager": ["mttr_proxy_min", "affected_services", "impact_score",
                    "recommended_action"],
    "engineer": ["root_cause_narrative", "correlated_raw_signals",
                 "root_cause_confidence", "recommended_action"],
}


def render_role_view(role: str, ctx: dict) -> dict:
    """Return the role's enriched slice of the context."""
    return {k: ctx[k] for k in VIEW_KEYS[role] if k in ctx}


def relevance_score(role: str, view: dict) -> float:
    """Rubric score in [0,1]: required facts present minus noise penalty."""
    req = REQUIRED[role]
    irr = IRRELEVANT[role]
    have = set(view)
    recall = len(req & have) / max(1, len(req))
    penalty = 0.1 * len(irr & have)
    return round(max(0.0, recall - penalty), 3)


def raw_dump_view(ctx: dict) -> dict:
    """Baseline: every role sees everything (noisy)."""
    return dict(ctx)
