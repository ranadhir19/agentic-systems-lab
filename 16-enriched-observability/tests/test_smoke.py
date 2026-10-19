"""Smoke tests for enriched observability."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import numpy as np

from agentic_systems.enriched_observability import (
    LAYERS, analytic, composer, correlate, detect_layer, enrich, roles,
    run_pipeline, telemetry,
)


def test_telemetry_deterministic():
    a = telemetry.simulate(7)
    b = telemetry.simulate(7)
    for layer in LAYERS:
        for k, v in a[layer].items():
            if k == "anomalies":
                assert v == b[layer][k]
            elif isinstance(v, dict):
                for sk in v:
                    assert np.array_equal(np.asarray(v[sk]),
                                          np.asarray(b[layer][k][sk]))
            else:
                assert np.array_equal(np.asarray(v),
                                      np.asarray(b[layer][k]))


def test_cascade_chain_ground_truth():
    assert [c["layer"] for c in telemetry.CASCADE_CHAIN] == LAYERS
    onsets = [c["onset"] for c in telemetry.CASCADE_CHAIN]
    assert onsets == sorted(onsets)


def test_robust_z_flags_cascade():
    data = telemetry.simulate(7)
    s = np.asarray(data["application"]["checkout_error_rate"])
    z = enrich.robust_z(s)
    assert float(np.abs(z[250:290]).max()) > 3.0


def test_detect_intervals_warmup():
    z = np.zeros(480)
    z[5:10] = 10.0  # before warmup: ignored
    assert enrich.detect_intervals(z) == []
    z[100:110] = 10.0
    ivs = enrich.detect_intervals(z)
    assert len(ivs) == 1 and ivs[0][0] == 100


def test_forecast_breach_sane():
    s = np.linspace(50, 80, 100)  # steady ramp
    fb = enrich.forecast_breach(s, 90.0)
    assert fb is not None and 0 < fb < 60
    flat = np.full(100, 50.0)
    assert enrich.forecast_breach(flat, 90.0) is None


def test_kmeans_groups():
    x = np.array([1.0, 1.1, 0.9, 10.0, 10.2, 9.8])
    lab = enrich.kmeans_1d(x, 2, seed=0)
    assert lab[0] == lab[1] == lab[2]
    assert lab[3] == lab[4] == lab[5]
    assert lab[0] != lab[3]


def test_chain_recall_perfect_on_seeds():
    for seed in (7, 11, 42):
        p = run_pipeline(seed)
        rec, _ = correlate.chain_link_recall(p["chain"])
        assert rec == 1.0, f"seed {seed}: recall {rec}"


def test_role_views_relevant():
    p = run_pipeline(7)
    for role in roles.ROLES:
        view = roles.render_role_view(role, p["context"])
        assert roles.relevance_score(role, view) >= 0.9


def test_analytic_record_shape():
    p = run_pipeline(7)
    ev = p["analytics"]["application"]
    for k in ("failure_probability", "root_cause_confidence",
              "impact_score", "recommended_action"):
        assert k in ev
    assert 0.0 <= ev["failure_probability"] <= 1.0
    assert composer.compose_layer_insight(ev)


def test_no_forbidden_name():
    import pathlib
    root = pathlib.Path(__file__).resolve().parents[2]
    forbidden = "dev" + "pulse"  # avoid self-match on the literal
    hits = []
    for pat in ("src/agentic_systems/enriched_observability",
                "16-enriched-observability", "examples"):
        base = root / pat
        if not base.exists():
            continue
        for f in base.rglob("*"):
            if f.is_file() and f.suffix in (".py", ".md"):
                if f.name == "test_smoke.py":
                    continue
                if forbidden in f.read_text().lower():
                    hits.append(str(f))
    assert not hits, hits
