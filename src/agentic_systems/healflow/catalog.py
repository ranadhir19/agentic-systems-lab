"""HealFlow sample catalog: tools, contract predicates, workflows.

Three workflows exercising different failure modes:
- order-flow:   external transaction (payment) — partial-failure compensation
- etl-flow:     schema change — tool substitution
- research-flow: corrupted intermediate — causal diagnosis + rollback
"""
from __future__ import annotations

from .faults import FaultInjector
from .workflow import WorkflowDef, StepDef


# ---------------------------------------------------------------------------
# Tools (pure functions of state)
# ---------------------------------------------------------------------------
def validate_order(state, args):
    order = state.get("order", {})
    return {"valid": bool(order.get("items"))}


def charge_payment(state, args):
    n = state.get("_charges", 0) + 1
    state["_charges"] = n
    return {"charged": True, "tx": f"tx-{n}"}


def refund_payment(state, args):
    state["_refunds"] = state.get("_refunds", 0) + 1
    return {"refunded": True}


def reserve_inventory(state, args):
    return {"reserved": True}


def send_confirmation(state, args):
    return {"sent": True}


def extract(state, args):
    return {"rows": [{"user_id": i, "val": i * 10} for i in range(5)],
            "columns": ["user_id", "val"]}


def transform(state, args):
    rows = state["extract"]["rows"]
    return {"rows": [{"user_id": r.get("user_id"), "double": r.get("val", 0) * 2}
                     for r in rows]}


def transform_v2(state, args):
    """Schema-tolerant substitute: accepts 'uid' or 'user_id'."""
    rows = state["extract"]["rows"]
    out = []
    for r in rows:
        uid = r.get("user_id", r.get("uid"))
        out.append({"user_id": uid, "double": r["val"] * 2})
    return {"rows": out}


def load(state, args):
    return {"loaded": True, "n": len(state["transform"]["rows"])}


def plan(state, args):
    return {"plan": ["outline", "draft", "cite"]}


def plan_v2(state, args):
    """Hardened substitute: validates and normalizes the plan."""
    return {"plan": ["outline", "draft", "cite"]}


def search(state, args):
    return {"results": [{"title": f"result-{i}", "url": f"u{i}"}
                        for i in range(3)]}


def search_v2(state, args):
    """Tolerant substitute: reads 'headline' or 'title'."""
    return {"results": [{"title": f"result-{i}", "url": f"u{i}"}
                        for i in range(3)]}


def synthesize(state, args):
    results = state["search"]["results"]
    titles = [r.get("title") for r in results]
    return {"report": " | ".join(t for t in titles if t),
            "citations": len(titles), "titles": titles}


TOOLS = {
    "validate_order": validate_order, "charge_payment": charge_payment,
    "refund_payment": refund_payment, "reserve_inventory": reserve_inventory,
    "send_confirmation": send_confirmation, "extract": extract,
    "transform": transform, "transform_v2": transform_v2, "load": load,
    "plan": plan, "search": search, "search_v2": search_v2,
    "synthesize": synthesize, "plan_v2": plan_v2,
}

# step_id -> substitute tool
SUBSTITUTES = {"transform": "transform_v2", "search": "search_v2",
               "plan": "plan_v2"}


# ---------------------------------------------------------------------------
# Contract predicates: (run_state, output) -> bool
# ---------------------------------------------------------------------------
def _out(rs, step_id):
    return rs.outputs.get(step_id, {})


PREDS = {
    "order_present": lambda rs, out: "order" in rs.state,
    "order_valid": lambda rs, out: _out(rs, "validate_order").get("valid") is True,
    "not_already_charged": lambda rs, out: "charge_payment" not in rs.outputs,
    "payment_charged": lambda rs, out: _out(rs, "charge_payment").get("charged") is True,
    "inventory_reserved": lambda rs, out: _out(rs, "reserve_inventory").get("reserved") is True,
    "confirmation_sent": lambda rs, out: _out(rs, "send_confirmation").get("sent") is True,
    "extract_ok": lambda rs, out: "rows" in _out(rs, "extract"),
    "schema_ok": lambda rs, out: bool(_out(rs, "transform").get("rows"))
        and all("user_id" in r and r["user_id"] is not None
                for r in _out(rs, "transform")["rows"]),
    "data_clean": lambda rs, out: all(
        v is not None for r in _out(rs, "transform").get("rows", []) for v in r.values()),
    "load_ok": lambda rs, out: _out(rs, "load").get("loaded") is True,
    "plan_ready": lambda rs, out: _out(rs, "plan").get("plan") == ["outline", "draft", "cite"],
    "search_ok": lambda rs, out: bool(_out(rs, "search").get("results"))
        and all("title" in r for r in _out(rs, "search")["results"]),
    "report_ok": lambda rs, out: "report" in _out(rs, "synthesize")
        and _out(rs, "synthesize").get("citations", 0) == 3
        and all(_out(rs, "synthesize").get("titles", [])),
}


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------
def order_flow() -> WorkflowDef:
    return WorkflowDef("order-flow", [
        StepDef("validate_order", "validate_order",
                pre=("order_present",), post=("order_valid",)),
        StepDef("charge_payment", "charge_payment",
                pre=("order_valid", "not_already_charged"),
                post=("payment_charged",),
                compensation="refund_payment", risk="high", external=True),
        StepDef("reserve_inventory", "reserve_inventory",
                pre=("payment_charged",), post=("inventory_reserved",)),
        StepDef("send_confirmation", "send_confirmation",
                pre=("inventory_reserved",), post=("confirmation_sent",)),
    ], initial_state={"order": {"items": ["book"]}})


def etl_flow() -> WorkflowDef:
    return WorkflowDef("etl-flow", [
        StepDef("extract", "extract", post=("extract_ok",)),
        StepDef("transform", "transform", pre=("extract_ok",),
                post=("schema_ok", "data_clean"), substitutable=True),
        StepDef("load", "load", pre=("schema_ok",), post=("load_ok",)),
    ])


def research_flow() -> WorkflowDef:
    return WorkflowDef("research-flow", [
        StepDef("plan", "plan", post=("plan_ready",), substitutable=True),
        StepDef("search", "search", pre=("plan_ready",), post=("search_ok",),
                substitutable=True),
        StepDef("synthesize", "synthesize", pre=("search_ok",),
                post=("report_ok",)),
    ])


def build_injector() -> FaultInjector:
    inj = FaultInjector()
    for name, fn in TOOLS.items():
        inj.register(name, fn)
    return inj
