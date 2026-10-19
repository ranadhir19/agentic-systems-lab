"""Continuity metric suite: goal generation, diversity, communication,
link maintenance, caching, survival, and communication->goal coupling.
"""
from __future__ import annotations

import numpy as np


def episode_metrics(env, window=20):
    agents = env.agents
    alive_steps = sum(a.age for a in agents)
    # self-generated goals
    imagined = [g for a in agents for g in a.goals if g.kind == "imagined"]
    n_imagined = len(imagined)
    adopted = sum(1 for g in imagined if g.adopted)
    targets = list({g.target for g in imagined})
    diversity_cells = len(targets)
    if len(targets) > 1:
        pts = np.array(targets, dtype=float)
        d = np.sqrt(((pts[:, None, :] - pts[None, :, :]) ** 2).sum(-1))
        iu = np.triu_indices(len(pts), 1)
        diversity_dist = float(d[iu].mean())
    else:
        diversity_dist = 0.0
    # communication
    emitted = sum(a.tokens_emitted for a in agents)
    heard = sum(a.tokens_heard for a in agents)
    comm_rate = 100.0 * emitted / max(1, alive_steps)
    # link maintenance: mean neighbours within comm radius
    neigh = [n for a in agents for n in a.neighbor_counts]
    link = float(np.mean(neigh)) if neigh else 0.0
    # affiliation away from resources: neighbours when >6 cells from any
    # source (not explainable by shared foraging attraction)
    away = [n for a in agents for n in a.neighbor_counts_away]
    link_away = float(np.mean(away)) if away else 0.0
    # caching: fraction of collected resources withheld from both deposit
    # and eating (held as buffer) by episode end
    caches = []
    for a in agents:
        withheld = a.collected_total - a.deposits - a.eaten_total
        if a.collected_total > 0:
            caches.append(withheld / a.collected_total)
    cache = float(np.mean(caches)) if caches else 0.0
    # survival
    lifetime = float(np.mean([a.age for a in agents]))
    deposits = sum(a.deposits for a in agents)
    # comm -> goal coupling: P(imagine within `window` steps after a hear)
    # vs base rate of imagining in a random window
    lifts = []
    for a in agents:
        if not a.hear_times or not a.gen_times:
            continue
        gen = np.array(a.gen_times)
        hits = 0
        for ht in a.hear_times:
            if ((gen > ht) & (gen <= ht + window)).any():
                hits += 1
        p_after = hits / len(a.hear_times)
        base = len(a.gen_times) * window / max(1, a.age)
        base = min(base, 1.0)
        if base > 1e-9:
            lifts.append(p_after / base)
    lift = float(np.mean(lifts)) if lifts else float("nan")
    # social goal fraction: imagined goals whose target lies near a
    # location heard about shortly before generation (content coupling)
    sg, sg_tot = 0, 0
    for a in agents:
        heard = [(t, xy) for (t, tok, xy) in a.heard_log]
        for g in a.goals:
            if g.kind != "imagined":
                continue
            sg_tot += 1
            for (t, xy) in heard:
                if 0 < g.created_at - t <= 60 and \
                   abs(g.target[0] - xy[0]) + abs(g.target[1] - xy[1]) <= 8:
                    sg += 1
                    break
    social_frac = sg / max(1, sg_tot)
    # token specialization: mean entropy of context distribution per token
    # (low entropy => tokens specialized to situations)
    ents = []
    for a in agents:
        if a.tokens_emitted == 0:
            continue
        p = a.tok_ctx / a.tok_ctx.sum(axis=1, keepdims=True).clip(min=1e-9)
        ent = -(p * np.log(p.clip(min=1e-9))).sum(axis=1)
        used = a.tok_ctx.sum(axis=1) > 0
        if used.any():
            ents.append(float(ent[used].mean()))
    tok_entropy = float(np.mean(ents)) if ents else float("nan")
    # time series: cumulative imagined goals and distinct goal cells at
    # checkpoints (tests H5: does diversity keep growing or saturate?)
    checkpoints = list(range(150, 1501, 150))
    cum_goals, cum_cells = [], []
    for c in checkpoints:
        gs = [g for g in imagined if g.created_at <= c]
        cum_goals.append(len(gs))
        cum_cells.append(len({g.target for g in gs}))
    return {
        "n_imagined": n_imagined,
        "adoption_rate": adopted / max(1, n_imagined),
        "diversity_cells": diversity_cells,
        "diversity_dist": diversity_dist,
        "comm_rate": comm_rate,
        "tokens_heard": heard,
        "link_neighbors": link,
        "link_away": link_away,
        "cache_ratio": cache,
        "lifetime": lifetime,
        "deposits": deposits,
        "comm_goal_lift": lift,
        "social_goal_frac": social_frac,
        "token_entropy": tok_entropy,
        "alive_steps": alive_steps,
        "checkpoints": checkpoints,
        "cum_goals": cum_goals,
        "cum_cells": cum_cells,
    }


def cohens_d(x, y):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    nx, ny = len(x), len(y)
    pooled = np.sqrt(((nx - 1) * x.var() + (ny - 1) * y.var())
                          / max(1, nx + ny - 2))
    if pooled < 1e-12:
        return 0.0
    return float((x.mean() - y.mean()) / pooled)
