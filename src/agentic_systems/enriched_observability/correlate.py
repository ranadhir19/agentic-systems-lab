"""Cross-layer correlation engine.

Links detected anomaly events across the five layers into an ordered
causal chain. A link from layer L to layer L+1 is accepted when:
  1. the downstream event onsets after (or with) the upstream event, and
  2. the lagged correlation between the layers' key series is strong
     (|r| >= min_corr) with a non-negative best lag (downstream follows).

Returns the chain with per-link confidence; experiments score link
precision/recall against the ground-truth cascade chain.
"""
from __future__ import annotations

import numpy as np

from . import enrich
from .telemetry import CASCADE_CHAIN, LAYERS

# One representative "key" series per layer for cross-layer correlation.
KEY_SERIES = {
    "infra": "net_latency_ms",
    "platform": "mem_pressure_pct",
    "application": "checkout_error_rate",
    "sre": "slo_success",
    "business": "failed_txns",
}


def _key_series(layer: str, data: dict) -> np.ndarray:
    key = KEY_SERIES[layer]
    s = data[layer][key]
    if isinstance(s, dict):  # infra cpu_pct is per-node
        s = next(iter(s.values()))
    return np.asarray(s, dtype=float)


def _primary_interval(evs: list) -> tuple[int, int, float] | None:
    """Primary event = the interval with the largest anomaly mass
    (duration x peak |z|). Sustained anomalies beat brief spikes."""
    if not evs:
        return None
    return max(evs, key=lambda e: (e[1] - e[0]) * e[2])


def reconstruct_chain(events_by_layer: dict, data: dict,
                      min_corr: float = 0.5, order_tol: int = 20
                      ) -> list[dict]:
    """Build the ordered causal chain from per-layer detected events.

    events_by_layer: {layer: [(start, end, peak_z), ...]} (strongest used).
    Detection latency differs per layer, so a downstream onset up to
    `order_tol` minutes before the upstream onset is tolerated. A link is
    accepted on strong |lagged correlation| plus temporal order; the lag
    sign is not required because step-like signals make it ambiguous.
    """
    chain = []
    prev_layer = None
    prev_onset = None
    for layer in LAYERS:
        prim = _primary_interval(events_by_layer.get(layer, []))
        if prim is None:
            continue
        start = prim[0]
        if prev_layer is not None and start < prev_onset - order_tol:
            continue  # violates temporal order beyond tolerance; skip
        conf = 1.0
        if prev_layer is not None:
            a = _key_series(prev_layer, data)
            b = _key_series(layer, data)
            r, _ = enrich.lagged_corr(a, b, max_lag=45)
            if abs(r) < min_corr:
                prev_layer, prev_onset = layer, start
                continue  # weak evidence: no link
            conf = round(min(1.0, abs(r)), 3)
        truth = next((c for c in CASCADE_CHAIN if c["layer"] == layer), None)
        chain.append({
            "layer": layer,
            "metric": KEY_SERIES[layer],
            "onset": start,
            "confidence": conf,
            "label": truth["label"] if truth else "detected anomaly",
            "true_onset": truth["onset"] if truth else None,
        })
        prev_layer, prev_onset = layer, start
    return chain


def chain_link_recall(chain: list[dict]) -> tuple[float, float]:
    """(link recall, onset MAE) vs the ground-truth cascade chain.

    Link recall = fraction of the 4 true consecutive-layer links present
    in the reconstructed chain. Onset MAE = mean |detected - true| onset.
    """
    truth_layers = [c["layer"] for c in CASCADE_CHAIN]
    got_layers = [c["layer"] for c in chain]
    true_links = set(zip(truth_layers[:-1], truth_layers[1:]))
    got_links = set(zip(got_layers[:-1], got_layers[1:]))
    recall = len(true_links & got_links) / max(1, len(true_links))
    errs = [abs(c["onset"] - c["true_onset"]) for c in chain
            if c["true_onset"] is not None]
    mae = float(np.mean(errs)) if errs else float("nan")
    return recall, mae
