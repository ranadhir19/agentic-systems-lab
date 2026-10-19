"""Smoke tests for injection containment."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from agentic_systems.injection_containment import (
    PAYLOADS, Chain, Content, ProvenanceFirewall, PrivilegeBoundary,
    OutputSanitizer, TripwireCanary, summarize)
from agentic_systems.injection_containment.mosaic import (
    TILES, run_mosaic_trial, per_source_guard)
from agentic_systems.injection_containment.payloads import (
    build_carrier_content, CANARIES)
import numpy as np


def test_undefended_exfiltration_succeeds():
    c = Chain(defenses=[], seed=3)
    r = c.run("exfiltration", carrier_idx=0, hops=4)
    assert r.success
    assert len(r.unauthorized_calls) > 0


def test_firewall_blocks_all_payloads():
    for kind in PAYLOADS:
        c = Chain(defenses=[ProvenanceFirewall("strict")], seed=5)
        r = c.run(kind, carrier_idx=1, hops=4)
        assert not r.success, kind
        assert len(r.blocked_events) > 0


def test_privilege_boundary_blocks_action_not_belief():
    c = Chain(defenses=[PrivilegeBoundary()], seed=11)
    r = c.run("exfiltration", carrier_idx=0, hops=4)
    assert len(r.adopted_markers) > 0  # belief not prevented
    assert len(r.unauthorized_calls) == 0  # action prevented


def test_sanitizer_misses_subtle_nudge():
    c = Chain(defenses=[OutputSanitizer()], seed=0)
    r = c.run("subtle_nudge", carrier_idx=0, hops=4)
    assert r.success  # honest gap: nudges survive sanitization
    c2 = Chain(defenses=[OutputSanitizer()], seed=0)
    r2 = c2.run("direct_override", carrier_idx=0, hops=4)
    assert not r2.success


def test_canary_detects_exfil():
    c = Chain(defenses=[TripwireCanary()], seed=3)
    r = c.run("exfiltration", carrier_idx=0, hops=4)
    assert r.success  # canary is detect-only
    assert len(r.alerts) > 0
    assert any("CANARY" in det for _, det in r.alerts)


def test_taint_survives_summarization():
    carrier = build_carrier_content("direct_override", 0)
    task = Content(text="do the research", source="user", trust=2)
    sub = summarize([task, carrier])
    assert sub.is_tainted
    assert sub.trust == 1  # min trust wins


def test_forged_attribution_beats_attributed_firewall():
    c = Chain(defenses=[ProvenanceFirewall("attributed")], seed=19)
    r = c.run("exfiltration", carrier_idx=0, hops=4, forge_attribution=True)
    assert r.success
    c2 = Chain(defenses=[ProvenanceFirewall("strict")], seed=19)
    r2 = c2.run("exfiltration", carrier_idx=0, hops=4, forge_attribution=True)
    assert not r2.success


def test_mosaic_assembles_but_per_source_guards_pass():
    rng = np.random.default_rng(7)
    r = run_mosaic_trial(rng, list(TILES))
    assert r.assembled
    assert r.per_source_blocked == 0
    assert r.detected
    assert all(per_source_guard(t) for t in TILES)


def test_combined_defense_contains_everything():
    defs = [ProvenanceFirewall("strict"), PrivilegeBoundary(),
            OutputSanitizer(), TripwireCanary()]
    for kind in PAYLOADS:
        c = Chain(defenses=defs, seed=23)
        r = c.run(kind, carrier_idx=2, hops=4)
        assert not r.success, kind
        assert len(r.unauthorized_calls) == 0


def test_no_forbidden_name():
    import agentic_systems.injection_containment as m
    import pathlib
    root = pathlib.Path(m.__file__).parent
    for p in list(root.rglob("*.py")):
        assert "devpulse" not in p.read_text().lower(), p
