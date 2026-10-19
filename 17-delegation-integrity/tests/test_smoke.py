"""Smoke tests for delegation integrity."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np

from agentic_systems.delegation_integrity import (
    DATA_CHANNEL,
    INSTRUCTION_CHANNEL,
    THIRD_PARTY,
    USER,
    AuthorityToken,
    Intent,
    ambient_exceeds,
    check_intent,
    delegate,
    detect_conflict,
    resolve_conflict,
    verify_chain,
)
from agentic_systems.delegation_integrity import (
    conflicts,
    deputy,
    intent as intent_mod,
    principals,
    tokens,
)
from agentic_systems.delegation_integrity.conflicts import (
    PurchaseScenario,
    resolve_purchase,
    run_conflict_trial,
    scenario_directives,
)
from agentic_systems.delegation_integrity.deputy import (
    DeputyAgent,
    run_deputy_trial,
)
from agentic_systems.delegation_integrity.intent import Action, make_intent_scenarios
from agentic_systems.delegation_integrity.principals import Directive, Instruction


def _root_token() -> AuthorityToken:
    return AuthorityToken(
        token_id="t0", issuer="user", holder="A", principal=USER,
        scope=frozenset({("read_doc", "docs"), ("write_db", "internal_db")}),
        issued_at=0, expires_at=100, parent_id=None, attenuated=False)


def test_precedence_order():
    assert principals.PRECEDENCE[USER] > principals.PRECEDENCE[THIRD_PARTY]
    assert principals.PRECEDENCE["developer"] > principals.PRECEDENCE["deployer"]


def test_resolve_conflict_picks_highest_principal():
    ins = [
        Instruction("a", THIRD_PARTY, INSTRUCTION_CHANNEL, seq=0),
        Instruction("b", USER, INSTRUCTION_CHANNEL, seq=5),
    ]
    assert resolve_conflict(ins).principal == USER


def test_data_channel_never_authoritative():
    i = Instruction("do it", USER, DATA_CHANNEL)
    assert not principals.is_authoritative(i)
    assert principals.is_authoritative(
        Instruction("do it", USER, INSTRUCTION_CHANNEL))


def test_generic_conflict_detection():
    a = Directive("x", {"v": 1}, Instruction("a", USER))
    b = Directive("x", {"v": 2}, Instruction("b", USER))
    c = Directive("x", {"v": 1}, Instruction("c", USER))
    assert len(detect_conflict([a, b])) == 1
    assert detect_conflict([a, c]) == []


def test_strict_delegation_enforces_attenuation():
    parent = _root_token()
    child = delegate(parent, "B", frozenset({("read_doc", "docs")}),
                     ttl=50, now=0, token_id="t1", strict=True)
    assert child.scope < parent.scope
    assert child.expires_at <= parent.expires_at
    try:
        delegate(parent, "B", frozenset({("write_db", "external_bucket")}),
                 ttl=50, now=0, token_id="t2", strict=True)
        raise AssertionError("should have raised")
    except ValueError:
        pass


def test_verify_chain_catches_scope_expansion():
    parent = _root_token()
    bad = AuthorityToken(token_id="t1", issuer="A", holder="B",
                         principal=USER,
                         scope=frozenset({("write_db", "external_bucket")}),
                         issued_at=0, expires_at=50, parent_id="t0")
    res = verify_chain([parent, bad], now=10)
    assert not res["ok"] and any("scope exceeds" in v for v in res["violations"])


def test_verify_chain_catches_expiry():
    parent = _root_token()
    res = verify_chain([parent], now=101)
    assert not res["ok"]


def test_ambient_exceeds_flags_lax_delegation():
    parent = _root_token()
    wide = AuthorityToken(token_id="t1", issuer="A", holder="B",
                          principal=USER, scope=parent.scope,
                          issued_at=0, expires_at=200, parent_id="t0",
                          attenuated=False)
    assert ambient_exceeds(wide, parent)
    narrow = delegate(parent, "B", frozenset({("read_doc", "docs")}),
                      ttl=50, now=0, token_id="t2", strict=True)
    assert not ambient_exceeds(narrow, parent)


def test_naive_deputy_redirected():
    rng = np.random.default_rng(0)
    r = run_deputy_trial(rng, "naive")
    assert r["attack_succeeded"] is True


def test_provenance_blocks_deputy():
    rng = np.random.default_rng(0)
    for policy in ("provenance", "combined"):
        r = run_deputy_trial(rng, policy)
        assert r["attack_succeeded"] is False
        assert r["blocked_by"] == "provenance"


def test_scope_blocks_deputy():
    rng = np.random.default_rng(0)
    r = run_deputy_trial(rng, "scope")
    assert r["attack_succeeded"] is False
    assert r["blocked_by"] == "scope"


def test_conflict_detected_and_resolved():
    sc = PurchaseScenario(buyer_cap=100.0, merchant_demand=150.0,
                          merchant_first=True, phrasing="direct")
    directives = scenario_directives(sc)
    out = resolve_purchase(directives, sc, mode="precedence")
    assert out["conflict_detected"] is True
    assert out["charged"] == 0.0 and out["flagged"] is True


def test_no_conflict_charges_demand():
    sc = PurchaseScenario(buyer_cap=100.0, merchant_demand=80.0,
                          merchant_first=False, phrasing="direct")
    out = resolve_purchase(scenario_directives(sc), sc, mode="precedence")
    assert out["charged"] == 80.0 and out["flagged"] is False


def test_naive_first_wins_order_luck():
    rng = np.random.default_rng(3)
    results = [run_conflict_trial(rng, i, "naive") for i in range(60)]
    # Naive is right exactly when order and amounts align, not always.
    assert 0.0 < np.mean([r["correct"] for r in results]) < 1.0


def test_intent_checker_catches_violations():
    intent = Intent("buy", {"max_price": 1200.0, "vendors": ["acme"],
                            "forbidden": {"pii_broker"}})
    ok, _ = check_intent(intent, Action("buy", {"price": 900.0,
                                                "vendor": "acme"}))
    assert ok is True
    ok, reasons = check_intent(intent, Action("buy", {"price": 1500.0,
                                                      "vendor": "acme"}))
    assert ok is False and any("exceeds" in r for r in reasons)
    ok, _ = check_intent(intent, Action("refund", {"price": 10.0}))
    assert ok is False


def test_intent_scenarios_labeled():
    rng = np.random.default_rng(0)
    triples = make_intent_scenarios(rng, 60)
    assert any(lbl for _, _, lbl in triples)
    assert any(not lbl for _, _, lbl in triples)


def test_no_forbidden_name():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2]
    self = pathlib.Path(__file__).resolve()
    hits = []
    for p in list((root / "src" / "agentic_systems"
                   / "delegation_integrity").rglob("*.py")) + \
            list((root / "17-delegation-integrity").rglob("*.py")) + \
            list((root / "17-delegation-integrity").rglob("*.md")):
        if p.resolve() == self:
            continue
        # The forbidden token is checked in two halves so this file
        # itself never contains it.
        if ("devp" + "ulse") in p.read_text().lower():
            hits.append(str(p))
    assert hits == [], f"forbidden name found in {hits}"
