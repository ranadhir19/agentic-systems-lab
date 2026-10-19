"""Injection-containment experiments (all seeded).

(a) Attack success rate vs chain depth (1-4 hops), undefended, per payload.
(b) Per-defense block rate + false-positive rate on legitimate flows.
(c) Payload robustness: residual attack rate per payload x defense.
(d) Mosaic effect: per-source guards vs aggregation detector.
(e) Defense-in-depth: combined defenses vs each alone.
(f) Forged attribution: firewall strict vs attributed under forged
    user-attribution.

Outputs: results/results.md and results/charts.png.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from agentic_systems.injection_containment import PAYLOADS, Chain
from agentic_systems.injection_containment.defenses import (
    OutputSanitizer, PrivilegeBoundary, ProvenanceFirewall, TripwireCanary,
)
from agentic_systems.injection_containment.mosaic import (
    BENIGN_TILES, TILES, run_mosaic_trial)

N = 200
PAYLOAD_KINDS = list(PAYLOADS)
LEGIT_SRCS = ("user-notes", "calendar", "runbook")


def make_defenses(name):
    if name == "none":
        return []
    if name == "firewall-strict":
        return [ProvenanceFirewall("strict")]
    if name == "firewall-attrib":
        return [ProvenanceFirewall("attributed")]
    if name == "privilege":
        return [PrivilegeBoundary()]
    if name == "sanitizer":
        return [OutputSanitizer()]
    if name == "canary":
        return [TripwireCanary()]
    if name == "combined":
        return [ProvenanceFirewall("strict"), PrivilegeBoundary(),
                OutputSanitizer(), TripwireCanary()]
    raise ValueError(name)


DEFENSES = ["none", "firewall-strict", "firewall-attrib", "privilege",
            "sanitizer", "canary", "combined"]


def run_attack(defense, kind, n=N, hops=4, forge=False, seed0=0):
    """Aggregate metrics over n seeded trials."""
    atk = adop = act = blk = alert = 0
    fid = []
    # Per-payload seed offset so payloads don't share identical RNG draws.
    offset = sum(ord(c) for c in kind) % 100003
    for i in range(n):
        c = Chain(defenses=make_defenses(defense), seed=seed0 + offset + i)
        r = c.run(kind, carrier_idx=i % 3, hops=hops,
                  forge_attribution=forge)
        atk += r.success
        adop += len(r.adopted_markers) > 0
        act += len(r.unauthorized_calls) > 0
        blk += len(r.blocked_events) > 0
        alert += len(r.alerts) > 0
        fid.append(r.fidelity)
    fid = np.array(fid)
    return dict(attack=atk / n, adopted=adop / n, action=act / n,
                blocked=blk / n, alerted=alert / n,
                fidelity=fid.mean(axis=0) if len(fid) else ())


def run_fp(defense, n=N):
    """False positives: clean runs with legitimate low-trust instructions.

    Returns per-item block rates and their mean. A (trial, item) pair
    counts at most once even if blocked at several hops. Only DIRECT
    blocks count (source exactly the legitimate item): blocks of
    downstream summaries are a separate attribution-fragility effect,
    reported in the text.
    """
    srcs = ("doc:user-notes.txt", "tool:calendar", "doc:runbook.md")
    per_item = {s: set() for s in LEGIT_SRCS}
    for i in range(n):
        c = Chain(defenses=make_defenses(defense), seed=10000 + i)
        r = c.run(None, carrier_idx=0, hops=4, legitimate=(0, 1, 2))
        for _, det in r.blocked_events:
            for s, src in zip(LEGIT_SRCS, srcs):
                if f"from {src} " in det:
                    per_item[s].add(i)
    rates = {s: len(per_item[s]) / n for s in LEGIT_SRCS}
    return rates, float(np.mean(list(rates.values())))


def exp_a():
    """ASR vs chain depth, undefended."""
    rows = {}
    for kind in PAYLOAD_KINDS:
        rows[kind] = {}
        for hops in (1, 2, 3, 4):
            m = run_attack("none", kind, hops=hops)
            rows[kind][hops] = m
    return rows


def exp_b():
    """Per-defense block/FP rates at 4 hops."""
    rows = {}
    for defense in DEFENSES:
        rows[defense] = {}
        for kind in PAYLOAD_KINDS:
            rows[defense][kind] = run_attack(defense, kind)
        per_item, fp = run_fp(defense)
        rows[defense]["fp"] = fp
        rows[defense]["fp_detail"] = per_item
    # canary detection rate: alerted given exfil attack (canary is detect-only)
    return rows


def exp_d(n=120, seed=7):
    """Mosaic: tile subsets of size k=1..4, plus benign controls."""
    rng = np.random.default_rng(seed)
    out = {}
    for k in (1, 2, 3, 4):
        asm = det = blk = 0
        for _ in range(n):
            idx = rng.choice(len(TILES), size=k, replace=False)
            tiles = [TILES[i] for i in sorted(idx)]
            r = run_mosaic_trial(rng, tiles)
            asm += r.assembled
            det += r.detected
            blk += r.per_source_blocked > 0
        out[k] = dict(assembled=asm / n, detected=det / n,
                      per_source_blocked=blk / n)
    # benign controls: benign tiles, k=3..4
    fp = 0
    for _ in range(n):
        idx = rng.choice(len(BENIGN_TILES), size=4, replace=False)
        tiles = [BENIGN_TILES[i] for i in sorted(idx)]
        r = run_mosaic_trial(rng, tiles)
        fp += r.detected
    out["benign_fp"] = fp / n
    return out


def exp_f():
    """Forged user-attribution vs firewall modes (exfiltration)."""
    rows = {}
    for defense in ("firewall-strict", "firewall-attrib"):
        rows[defense] = run_attack(defense, "exfiltration", forge=True)
    return rows


def write_markdown(a, b, d, f, path):
    fp_detail = {defense: (b[defense]["fp_detail"], b[defense]["fp"])
                 for defense in DEFENSES}
    L = []
    L.append("# Injection-containment experiment results\n")
    L.append(f"Seeded runs: N={N} trials per cell (mosaic N=120).\n")
    L.append("## (a) Attack success vs chain depth, undefended\n")
    L.append("| Payload | 1 hop | 2 hops | 3 hops | 4 hops |")
    L.append("|---|---|---|---|---|")
    for kind in PAYLOAD_KINDS:
        cells = " | ".join(f"{a[kind][h]['attack']:.2f}" for h in (1, 2, 3, 4))
        L.append(f"| {kind} | {cells} |")
    L.append("")
    L.append("Fidelity = fraction of payload keywords retained in each hop's "
             "context (mean over trials, 4 hops, undefended):")
    L.append("")
    L.append("| Payload | hop1 | hop2 | hop3 | hop4 |")
    L.append("|---|---|---|---|---|")
    for kind in PAYLOAD_KINDS:
        fid = a[kind][4]["fidelity"]
        L.append("| " + kind + " | " + " | ".join(f"{x:.2f}" for x in fid) + " |")
    L.append("")
    L.append("## (b) Per-defense results, 4 hops\n")
    L.append("| Defense | Payload | Attack | Adopted | Action | Blocked | Alerted |")
    L.append("|---|---|---|---|---|---|---|")
    for defense in DEFENSES:
        for kind in PAYLOAD_KINDS:
            m = b[defense][kind]
            L.append(f"| {defense} | {kind} | {m['attack']:.2f} | "
                     f"{m['adopted']:.2f} | {m['action']:.2f} | "
                     f"{m['blocked']:.2f} | {m['alerted']:.2f} |")
    L.append("")
    L.append("False-positive rate = P(legitimate instruction blocked at first "
             "contact), mean over 3 legitimate low-trust items:")
    L.append("")
    L.append("| Defense | user note | calendar | runbook | mean |")
    L.append("|---|---|---|---|---|")
    for defense in DEFENSES:
        pr, mean = fp_detail[defense]
        cells = " | ".join(f"{pr[s]:.2f}" for s in
                           ("user-notes", "calendar", "runbook"))
        L.append(f"| {defense} | {cells} | {mean:.2f} |")
    L.append("")
    L.append("Note: user-attribution does not survive summarization "
             "(`summarize` requires ALL inputs attributed), so an allowed "
             "user note is still blocked when it flows downstream -- "
             "attribution is fragile across delegation.")
    L.append("## (c) Payload robustness (residual attack rate per defense)\n")
    L.append("Hardest to stop = highest residual attack rate across defenses:")
    L.append("")
    L.append("| Payload | " + " | ".join(DEFENSES) + " |")
    L.append("|---|" + "|".join(["---"] * len(DEFENSES)) + "|")
    for kind in PAYLOAD_KINDS:
        cells = " | ".join(f"{b[d][kind]['attack']:.2f}" for d in DEFENSES)
        L.append(f"| {kind} | {cells} |")
    L.append("")
    L.append("## (d) Mosaic effect\n")
    L.append("| Tiles | Assembled | Per-source blocked | Detected |")
    L.append("|---|---|---|---|")
    for k in (1, 2, 3, 4):
        m = d[k]
        L.append(f"| {k} | {m['assembled']:.2f} | {m['per_source_blocked']:.2f} "
                 f"| {m['detected']:.2f} |")
    L.append(f"| benign (FP) | 0.00 | 0.00 | {d['benign_fp']:.2f} |")
    L.append("")
    L.append("## (e) Defense-in-depth (residual attack rate, 4 hops)\n")
    L.append("See chart. Combined = firewall-strict + privilege + "
             "sanitizer + canary.")
    L.append("")
    L.append("## (f) Forged user-attribution (exfiltration)\n")
    L.append("| Defense | Attack | Blocked |")
    L.append("|---|---|---|")
    for defense, m in f.items():
        L.append(f"| {defense} | {m['attack']:.2f} | {m['blocked']:.2f} |")
    L.append("")
    with open(path, "w") as fh:
        fh.write("\n".join(L) + "\n")


def make_charts(a, b, d, path):
    fig, axes = plt.subplots(2, 3, figsize=(15, 9))
    fig.suptitle("Injection containment — seeded experiments", fontsize=13)

    # 1. ASR vs hops
    ax = axes[0, 0]
    for kind in PAYLOAD_KINDS:
        ax.plot((1, 2, 3, 4), [a[kind][h]["attack"] for h in (1, 2, 3, 4)],
                marker="o", label=kind)
    ax.set_xlabel("chain depth (hops)")
    ax.set_ylabel("attack success rate")
    ax.set_title("(a) ASR vs chain depth, undefended")
    ax.legend(fontsize=8)
    ax.set_ylim(-0.05, 1.05)

    # 2. Fidelity decay
    ax = axes[0, 1]
    for kind in PAYLOAD_KINDS:
        ax.plot((1, 2, 3, 4), a[kind][4]["fidelity"], marker="o", label=kind)
    ax.set_xlabel("hop")
    ax.set_ylabel("payload keyword retention")
    ax.set_title("(a) Propagation fidelity vs depth")
    ax.legend(fontsize=8)
    ax.set_ylim(-0.05, 1.05)

    # 3. Block rate per defense (mean over payloads) + FP
    ax = axes[0, 2]
    labels = [d_ for d_ in DEFENSES if d_ != "none"]
    blk = [np.mean([b[d_][k]["blocked"] for k in PAYLOAD_KINDS]) for d_ in labels]
    fp = [b[d_]["fp"] for d_ in labels]
    x = np.arange(len(labels))
    ax.bar(x - 0.2, blk, 0.4, label="block rate")
    ax.bar(x + 0.2, fp, 0.4, label="false-positive rate")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_title("(b) Block rate vs FP rate")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 1.05)

    # 4. Residual attack per payload, selected defenses
    ax = axes[1, 0]
    sel = ["none", "firewall-strict", "privilege", "sanitizer", "combined"]
    x = np.arange(len(PAYLOAD_KINDS))
    w = 0.15
    for j, d_ in enumerate(sel):
        vals = [b[d_][k]["attack"] for k in PAYLOAD_KINDS]
        ax.bar(x + j * w, vals, w, label=d_)
    ax.set_xticks(x + w * 2)
    ax.set_xticklabels(PAYLOAD_KINDS, fontsize=8)
    ax.set_title("(c,e) Residual attack rate per payload")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 1.05)

    # 5. Mosaic
    ax = axes[1, 1]
    ks = (1, 2, 3, 4)
    asm = [d[k]["assembled"] for k in ks]
    det = [d[k]["detected"] for k in ks]
    x = np.arange(len(ks))
    ax.bar(x - 0.2, asm, 0.4, label="insight assembled")
    ax.bar(x + 0.2, det, 0.4, label="detected")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{k} tiles" for k in ks])
    ax.set_title("(d) Mosaic: assembly vs detection")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 1.05)

    # 6. Adopted vs action (exfiltration): privilege boundary's role
    ax = axes[1, 2]
    labs = ["none", "privilege", "firewall-strict", "combined"]
    adop = [b[d_]["exfiltration"]["adopted"] for d_ in labs]
    act = [b[d_]["exfiltration"]["action"] for d_ in labs]
    x = np.arange(len(labs))
    ax.bar(x - 0.2, adop, 0.4, label="instruction adopted")
    ax.bar(x + 0.2, act, 0.4, label="unauthorized action")
    ax.set_xticks(x)
    ax.set_xticklabels(labs, fontsize=8)
    ax.set_title("Exfiltration: belief vs action")
    ax.legend(fontsize=8)
    ax.set_ylim(0, 1.05)

    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    res = os.path.join(here, "..", "results")
    os.makedirs(res, exist_ok=True)
    print("exp (a): ASR vs depth ...")
    a = exp_a()
    print("exp (b): defenses ...")
    b = exp_b()
    print("exp (d): mosaic ...")
    d = exp_d()
    print("exp (f): forged attribution ...")
    f = exp_f()
    write_markdown(a, b, d, f, os.path.join(res, "results.md"))
    make_charts(a, b, d, os.path.join(res, "charts.png"))
    print("wrote results/results.md and results/charts.png")


if __name__ == "__main__":
    main()
