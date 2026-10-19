"""SRE-learning experiments (all seeded).

World: 2400 changes / ~700 incidents over 180 days, seed 7.
Time split: days 0-120 train, days 120-180 test.

(a) change-risk: precision/recall/AUC + calibration on held-out test
    changes; model weights vs ground truth; Bayes-ceiling reference.
(b) change-incident linking: top-1/top-3 accuracy vs recency baseline.
(c) causality: top-k root-cause accuracy, graph vs correlation baseline.
(d) similarity: precision@k, learned metric vs TF-IDF baseline.
(e) resolution: simulated success rate vs most-frequent-action baseline.
(f) continuous learning: 6-month simulation, change-agent AUC on a fixed
    validation set, continuous vs frozen model.
(g) active learning: labeling budget vs pair-accuracy, uncertainty vs
    random sampling.

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

from agentic_systems.sre_learning import (
    World, DataPipeline, ChangeRiskPredictor, auc_score, precision_recall,
    calibration_bins, CausalKnowledgeGraph, SimilarityAgent, TfidfBaseline,
    make_pairs, ResolutionAgent, ContinuousLearner,
)
from agentic_systems.sre_learning.synth import TRUE_W

SEED = 7
DAY = 24.0
RESULTS = os.path.join(os.path.dirname(__file__), "..", "results")
os.makedirs(RESULTS, exist_ok=True)


def build_world():
    w = World(seed=SEED)
    changes = w.gen_changes(2400, span_h=180 * DAY)
    incidents = w.gen_incidents(changes)
    split = 120 * DAY
    tr_ch = [c for c in changes if c.t <= split]
    te_ch = [c for c in changes if c.t > split]
    tr_in = [i for i in incidents if i.t_start <= split]
    te_in = [i for i in incidents if i.t_start > split]
    return w, tr_ch, te_ch, tr_in, te_in, changes, incidents


def exp_a_change_risk(w, tr_ch, te_ch):
    Xtr, ytr = w.feature_matrix(tr_ch), w.labels(tr_ch)
    Xte, yte = w.feature_matrix(te_ch), w.labels(te_ch)
    agent = ChangeRiskPredictor().fit(Xtr, ytr)
    p = agent.predict_proba(Xte)
    pr = precision_recall(yte, agent.predict(Xte))
    # Bayes ceiling on test
    z = TRUE_W[0] + TRUE_W[1:] @ Xte.T
    p_true = 1 / (1 + np.exp(-z))
    out = {
        "n_train": len(tr_ch), "n_test": len(te_ch),
        "auc": auc_score(yte, p), "bayes_auc": auc_score(yte, p_true),
        **pr,
        "calibration": calibration_bins(yte, p),
        "weight_mae": float(np.abs(agent.w - TRUE_W[1:]).mean()),
    }
    return agent, out


def exp_b_linking(w, pipe, te_in, changes):
    enr = pipe.enrich(te_in, changes)
    acc = pipe.linking_accuracy(enr)
    # recency-only baseline: most recent same-service change within 24h
    correct = total = 0
    for inc in te_in:
        if inc.change_id < 0:
            continue
        total += 1
        cands = [c for c in changes
                 if c.service == inc.service and 0 < inc.t_start - c.t <= 24]
        if cands:
            best = max(cands, key=lambda c: c.t)
            correct += best.id == inc.change_id
    acc["recency_baseline"] = correct / total if total else 0.0
    return acc


def exp_c_causality(w, tr_in, te_in, changes):
    g = CausalKnowledgeGraph().fit(
        [i.postmortem for i in tr_in if i.postmortem])
    # change-type lookup from enrichment top candidate (mirrors the workflow)
    pipe = DataPipeline(w)
    enr = {e.incident.id: e for e in pipe.enrich(te_in, changes)}
    lookup_all, lookup_correct = {}, {}
    for i in te_in:
        e = enr[i.id]
        if e.candidates:
            ch = e.candidates[0].change
            lookup_all[i.id] = ch.change_type
            if ch.id == i.change_id:
                lookup_correct[i.id] = ch.change_type
    return {
        "graph_top1": g.top_k_accuracy(te_in, k=1, change_lookup=lookup_all),
        "graph_top3": g.top_k_accuracy(te_in, k=3, change_lookup=lookup_all),
        "graph_ctx_top1": g.top_k_accuracy(te_in, k=1,
                                            change_lookup=lookup_correct),
        "graph_ctx_top3": g.top_k_accuracy(te_in, k=3,
                                            change_lookup=lookup_correct),
        "corr_top1": g.top_k_accuracy(te_in, k=1, baseline=True),
        "corr_top3": g.top_k_accuracy(te_in, k=3, baseline=True),
        "n_test": len(te_in),
    }


def exp_d_similarity(tr_in, te_in, seed=SEED):
    rng = np.random.default_rng(seed)
    pairs = make_pairs(tr_in, rng, n_pairs=3000)
    sim = SimilarityAgent().fit(pairs)
    tf = TfidfBaseline().fit(tr_in)
    queries = te_in[:120]
    out = {}
    for k in (1, 3, 5):
        out[f"learned_p@{k}"] = sim.precision_at_k(queries, tr_in, k=k)
        out[f"tfidf_p@{k}"] = tf.precision_at_k(queries, tr_in, k=k)
    return sim, out


def exp_e_resolution(tr_in, te_in):
    res = ResolutionAgent().fit(tr_in)
    return {
        "agent": res.success_rate(te_in),
        "baseline": res.success_rate(te_in, baseline=True),
        "n_test": len(te_in),
    }


def exp_f_continuous():
    # own world with concept drift at day 90: night deploys get safer
    # (new automation), blast radius matters more, config risk drops
    drift_W = TRUE_W.copy()
    drift_W[6] = -0.4   # night_deploy
    drift_W[5] = 2.6    # blast_radius
    drift_W[1] = 0.2    # is_config
    w = World(seed=SEED, drift_day=90 * DAY, drift_W=drift_W)
    changes = w.gen_changes(2400, span_h=180 * DAY)
    incidents = w.gen_incidents(changes)
    # monthly buckets over 180 days
    months_ch, months_in = [], []
    for m in range(6):
        lo, hi = m * 30 * DAY, (m + 1) * 30 * DAY
        months_ch.append([c for c in changes if lo < c.t <= hi])
        months_in.append([i for i in incidents if lo < i.t_start <= hi])
    val_ch = months_ch[5]
    val_y = w.labels(val_ch)

    def fresh_agents():
        ca = ChangeRiskPredictor()
        X = w.feature_matrix(months_ch[0])
        ca.fit(X, w.labels(months_ch[0]))
        return ca, SimilarityAgent(), ResolutionAgent().fit(months_in[0])

    # continuous learner: monthly incremental updates (more SGD steps to
    # track drift)
    ca, sim, res = fresh_agents()
    learner = ContinuousLearner(ca, sim, res)
    curve = []
    Xv = w.feature_matrix(val_ch)
    curve.append(("month1", auc_score(val_y, ca.predict_proba(Xv))))
    for m in range(1, 5):
        learner.update(months_in[m], months_ch[m], month=m,
                       val_changes=val_ch, val_labels=val_y, sgd_steps=200)
        curve.append((f"month{m+1}", learner.history[-1]["change_auc"]))
    # frozen baseline: month-1 model evaluated on post-drift validation
    ca0, _, _ = fresh_agents()
    frozen = auc_score(val_y, ca0.predict_proba(Xv))
    return {"curve": curve, "frozen": frozen,
            "velocity": learner.learning_velocity(),
            "drift_day": 90}


def exp_g_active_learning(tr_in, te_in, seed=SEED):
    # hard negatives: dissimilar pairs sharing >=1 symptom (the ambiguous
    # Low-data regime (200 labeled pairs): the realistic active-learning
    # setting. Hard negatives: dissimilar pairs sharing >=1 symptom
    # (the ambiguous cases); the pair task is near-ceiling on random pairs.
    rng = np.random.default_rng(seed)
    train_pairs = make_pairs(tr_in, rng, n_pairs=200)
    pool_draw = make_pairs(te_in, rng, n_pairs=600, hard_negatives=True)
    pool = [(a, b) for a, b, _ in pool_draw]
    truth = {(a.id, b.id): l for a, b, l in pool_draw}
    held = make_pairs(te_in, np.random.default_rng(seed + 1), n_pairs=800,
                      hard_negatives=True)

    def accuracy(pairs_extra):
        sim = SimilarityAgent(seed=seed).fit(train_pairs + pairs_extra,
                                             iters=800)
        ok = sum(1 for a, b, l in held
                 if (sim.pair_proba(a, b) >= 0.5) == bool(l))
        return ok / len(held)

    base = accuracy([])
    sim0 = SimilarityAgent(seed=seed).fit(train_pairs, iters=800)
    results = {"budget_0": base}
    for budget in (25, 50, 100, 200):
        # uncertainty sampling
        unc = sim0.uncertain_pairs(pool, budget)
        extra = [(a, b, truth[(a.id, b.id)]) for a, b in unc
                 if (a.id, b.id) in truth]
        # random sampling
        idx = rng.choice(len(pool), size=min(budget, len(pool)), replace=False)
        extra_r = [(a, b, truth[(a.id, b.id)]) for k in idx
                   for a, b in [pool[k]] if (a.id, b.id) in truth]
        results[f"unc_{budget}"] = accuracy(extra)
        results[f"rnd_{budget}"] = accuracy(extra_r)
    return results


def main():
    w, tr_ch, te_ch, tr_in, te_in, changes, incidents = build_world()
    print(f"world: {len(changes)} changes, {len(incidents)} incidents "
          f"(train {len(tr_ch)}/{len(tr_in)}, test {len(te_ch)}/{len(te_in)})")

    agent, ra = exp_a_change_risk(w, tr_ch, te_ch)
    print("A:", {k: round(v, 4) if isinstance(v, float) else v
                 for k, v in ra.items() if k != "calibration"})

    pipe = DataPipeline(w, change_agent=agent)
    rb = exp_b_linking(w, pipe, te_in, changes)
    print("B:", {k: round(v, 4) if isinstance(v, float) else v
                 for k, v in rb.items()})

    rc = exp_c_causality(w, tr_in, te_in, changes)
    print("C:", {k: round(v, 4) if isinstance(v, float) else v
                 for k, v in rc.items()})

    _, rd = exp_d_similarity(tr_in, te_in)
    print("D:", {k: round(v, 4) for k, v in rd.items()})

    re_ = exp_e_resolution(tr_in, te_in)
    print("E:", {k: round(v, 4) if isinstance(v, float) else v
                 for k, v in re_.items()})

    rf = exp_f_continuous()
    print("F: curve=", [(m, round(a, 4)) for m, a in rf["curve"]],
          "frozen=", round(rf["frozen"], 4), "velocity=", rf["velocity"])

    rg = exp_g_active_learning(tr_in, te_in)
    print("G:", {k: round(v, 4) for k, v in rg.items()})

    write_results(ra, rb, rc, rd, re_, rf, rg)
    write_charts(rd, rf, rg, rb, rc, re_)
    print("wrote results/results.md and results/charts.png")


def write_results(ra, rb, rc, rd, re_, rf, rg):
    L = ["# SRE-Learning experiment results", "",
         f"World seed {SEED}: 2400 changes / 180 days; train days 0-120, "
         "test days 120-180.", "",
         "## A — change-risk prediction (held-out test changes)",
         f"AUC **{ra['auc']:.4f}** (Bayes ceiling {ra['bayes_auc']:.4f}); "
         f"precision {ra['precision']:.3f}, recall {ra['recall']:.3f}, "
         f"F1 {ra['f1']:.3f}; weight MAE vs ground truth "
         f"{ra['weight_mae']:.3f}.",
         "Calibration (mean predicted, empirical rate, n):"]
    for mp, er, n in ra["calibration"]:
        L.append(f"- {mp:.2f} -> {er:.2f} (n={n})")
    L += ["",
          "## B — change-incident linking (test incidents)",
          f"Top-1 accuracy **{rb['accuracy']:.3f}**, top-3 "
          f"**{rb['top3_accuracy']:.3f}** (n={rb['total']}); recency-only "
          f"baseline top-1 {rb['recency_baseline']:.3f}.",
          "",
          "## C — causal path prediction (top-k root-cause accuracy)",
          f"Graph + change-type (workflow): top-1 **{rc['graph_top1']:.3f}**, "
          f"top-3 **{rc['graph_top3']:.3f}**; graph + change-type on "
          f"correctly-linked only: top-1 {rc['graph_ctx_top1']:.3f}, top-3 "
          f"{rc['graph_ctx_top3']:.3f}; correlation baseline: top-1 "
          f"{rc['corr_top1']:.3f}, top-3 {rc['corr_top3']:.3f} "
          f"(n={rc['n_test']}).",
          "",
          "## D — similarity precision@k (120 test queries)",
          f"Learned metric: P@1 **{rd['learned_p@1']:.3f}**, P@3 "
          f"{rd['learned_p@3']:.3f}, P@5 {rd['learned_p@5']:.3f}; TF-IDF: "
          f"P@1 {rd['tfidf_p@1']:.3f}, P@3 {rd['tfidf_p@3']:.3f}, P@5 "
          f"{rd['tfidf_p@5']:.3f}.",
          "",
          "## E — resolution recommendation (simulated success rate)",
          f"Agent **{re_['agent']:.3f}** vs most-frequent-action baseline "
          f"{re_['baseline']:.3f} (n={re_['n_test']}).",
          "",
          "## F — continuous learning (monthly AUC on fixed validation)",
          "Month: " + ", ".join(f"{m}={a:.4f}" for m, a in rf["curve"]) +
          f"; frozen month-1 model {rf['frozen']:.4f}.",
          f"AUC gain/month {rf['velocity'].get('auc_gain_per_month', float('nan')):.4f}.",
          "",
          "## G — active learning (pair-accuracy by labeling budget)",
          "Budget: " + ", ".join(
              f"{k}={v:.4f}" for k, v in rg.items()),
          ""]
    with open(os.path.join(RESULTS, "results.md"), "w") as f:
        f.write("\n".join(L))


def write_charts(rd, rf, rg, rb, rc, re_):
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))
    # 1: continuous learning curve
    ax = axes[0, 0]
    months = [m for m, _ in rf["curve"]]
    aucs = [a for _, a in rf["curve"]]
    ax.plot(months, aucs, "o-", label="continuous learning")
    ax.axhline(rf["frozen"], color="red", ls="--", label="frozen month-1 model")
    ax.set_title("Change-agent AUC on fixed validation set")
    ax.set_ylabel("AUC")
    ax.legend(fontsize=8)
    ax.tick_params(axis="x", rotation=20)
    # 2: similarity precision@k
    ax = axes[0, 1]
    ks = [1, 3, 5]
    ax.bar([k - 0.2 for k in ks], [rd[f"learned_p@{k}"] for k in ks],
           width=0.4, label="learned metric")
    ax.bar([k + 0.2 for k in ks], [rd[f"tfidf_p@{k}"] for k in ks],
           width=0.4, label="TF-IDF baseline")
    ax.set_title("Similar-incident retrieval precision@k")
    ax.set_xticks(ks)
    ax.legend(fontsize=8)
    # 3: linking + causality bars
    ax = axes[1, 0]
    labels = ["link top-1", "link top-3", "link recency", "causal top-3",
              "corr top-3"]
    vals = [rb["accuracy"], rb["top3_accuracy"], rb["recency_baseline"],
            rc["graph_top3"], rc["corr_top3"]]
    ax.bar(labels, vals)
    ax.set_title("Linking and causal-path accuracy")
    ax.tick_params(axis="x", rotation=25)
    # 4: active learning
    ax = axes[1, 1]
    budgets = [0, 25, 50, 100, 200]
    unc = [rg["budget_0"]] + [rg[f"unc_{b}"] for b in budgets[1:]]
    rnd = [rg["budget_0"]] + [rg[f"rnd_{b}"] for b in budgets[1:]]
    ax.plot(budgets, unc, "o-", label="uncertainty sampling")
    ax.plot(budgets, rnd, "s--", label="random sampling")
    ax.set_title("Active learning: pair accuracy vs labeling budget")
    ax.set_xlabel("labeled pairs")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(RESULTS, "charts.png"), dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    main()
