"""Delegation integrity quickstart: a confused-deputy attack, blocked.

An agent with database credentials reads a quarterly report. Hidden in
the report text is an instruction to copy customer PII to an external
bucket. The naive policy obeys it (attack succeeds); provenance
tagging refuses to treat data-channel content as instructions, and
scope attenuation denies the write even if attempted.

Run:  python3 examples/17_delegation_integrity_quickstart.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import numpy as np

from agentic_systems.delegation_integrity import (
    USER,
    AuthorityToken,
    attribute_action,
    delegate,
    run_deputy_trial,
    verify_chain,
)


def main() -> None:
    rng = np.random.default_rng(7)
    print("Confused deputy: hidden instruction in a quarterly report")
    for policy in ("naive", "provenance", "scope", "combined"):
        r = run_deputy_trial(rng, policy)
        status = "ATTACK SUCCEEDED" if r["attack_succeeded"] \
            else f"blocked ({r['blocked_by']})"
        print(f"  policy={policy:10s} variant={r['variant']:10s} -> {status}")
    assert run_deputy_trial(np.random.default_rng(7), "naive")[
        "attack_succeeded"]
    assert not run_deputy_trial(np.random.default_rng(7), "combined")[
        "attack_succeeded"]

    print()
    print("Delegation chain A->B->C with attenuation")
    root = AuthorityToken(
        token_id="t0", issuer="user", holder="A", principal=USER,
        scope=frozenset({("read_doc", "docs"), ("write_db", "internal_db")}),
        issued_at=0, expires_at=100, parent_id=None, attenuated=False)
    t1 = delegate(root, "B", frozenset({("read_doc", "docs")}),
                  ttl=60, now=0, token_id="t1", strict=True)
    t2 = delegate(t1, "C", frozenset({("read_doc", "docs")}),
                  ttl=30, now=0, token_id="t2", strict=True)
    res = verify_chain([root, t1, t2], now=10)
    print(f"  chain ok={res['ok']} violations={res['violations']}")
    assert res["ok"]
    print(f"  action by C attributes to principal: {attribute_action(t2)}")
    assert attribute_action(t2) == USER

    print()
    print("quickstart green")


if __name__ == "__main__":
    main()
