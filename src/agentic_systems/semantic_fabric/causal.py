"""L5 — causal semantics.

Constraint-based DAG discovery (PC-style skeleton with Fisher-z partial
correlation tests, orientation by temporal order), linear-Gaussian SCM
fit, do-interventions, and counterfactual queries. The discovered DAG is
a persistent semantic artifact: reasoning (root cause, simulation) runs
against it, never against raw data.
"""
from __future__ import annotations

import itertools

import numpy as np

from .common import partial_corr, fisher_z_test


def pc_skeleton(X, names, alpha=0.01, max_cond=2):
    """PC skeleton: start complete, remove edge i-j if conditionally
    independent given some subset of others. Returns adjacency as set of
    frozenset({i, j}) with sepsets recorded."""
    n, d = X.shape
    C = np.corrcoef(X, rowvar=False)
    C = np.nan_to_num(C)
    adj = {frozenset({i, j}) for i in range(d) for j in range(i + 1, d)}
    sepset = {}
    for size in range(0, max_cond + 1):
        removed = True
        while removed:
            removed = False
            for e in sorted(adj, key=lambda s: sorted(s)):
                i, j = sorted(e)
                others = [k for k in range(d) if k not in (i, j)]
                for cond in itertools.combinations(others, size):
                    p = fisher_z_test(partial_corr(C, i, j, cond), n,
                                      len(cond))
                    if p > alpha:
                        adj.discard(e)
                        sepset[e] = set(cond)
                        removed = True
                        break
                if removed:
                    break
    return adj, sepset


def orient_temporal(adj, names, order):
    """Orient edges by temporal/causal order (causes precede effects).

    `order` maps variable name -> rank. Returns directed edge list.
    """
    edges = []
    for e in adj:
        i, j = sorted(e)
        a, b = order[names[i]], order[names[j]]
        if a == b:
            continue
        edges.append((i, j) if a < b else (j, i))
    return edges


def fit_linear_scm(X, names, edges):
    """Least-squares coefficients of each node on its parents."""
    coefs, intercepts, parents = {}, {}, {}
    for j, name in enumerate(names):
        ps = sorted({i for i, jj in edges if jj == j})
        parents[name] = [names[i] for i in ps]
        if ps:
            A = np.column_stack([X[:, i] for i in ps] + [np.ones(len(X))])
            beta, *_ = np.linalg.lstsq(A, X[:, j], rcond=None)
            coefs[name] = {names[ps[k]]: float(beta[k])
                           for k in range(len(ps))}
            intercepts[name] = float(beta[-1])
        else:
            coefs[name] = {}
            intercepts[name] = float(X[:, j].mean())
    resid_std = {}
    for j, name in enumerate(names):
        pred = intercepts[name] + sum(coefs[name][p] * X[:, names.index(p)]
                                      for p in parents[name])
        resid_std[name] = float((X[:, j] - pred).std())
    return {"parents": parents, "coefs": coefs, "intercepts": intercepts,
            "resid_std": resid_std}


def extract_l5(X, names, order, alpha=0.01):
    """Full L5 artifact: skeleton -> oriented DAG -> linear SCM."""
    adj, sepset = pc_skeleton(X, names, alpha=alpha)
    edges = orient_temporal(adj, names, order)
    scm = fit_linear_scm(X, names, edges)
    return {
        "names": names,
        "edges": [(names[i], names[j]) for i, j in edges],
        "scm": scm,
        "n_edges": len(edges),
    }


def do_intervention(artifact, target, value, baseline):
    """do(target=value): propagate through the linear SCM in topological
    order. `baseline` maps name -> observed value (for root nodes)."""
    scm = artifact["scm"]
    names = artifact["names"]
    # topological order via parents
    order, done = [], set()
    while len(order) < len(names):
        for nm in names:
            if nm in done:
                continue
            if all(p in done for p in scm["parents"][nm]):
                order.append(nm)
                done.add(nm)
    vals = dict(baseline)
    vals[target] = value
    for nm in order:
        if nm == target:
            continue
        vals[nm] = scm["intercepts"][nm] + sum(
            scm["coefs"][nm][p] * vals[p] for p in scm["parents"][nm])
    return vals


def counterfactual(artifact, observed, target, value):
    """Counterfactual: abduction (recover noise) then do(target=value)."""
    scm = artifact["scm"]
    noise = {}
    for nm in artifact["names"]:
        pred = scm["intercepts"][nm] + sum(
            scm["coefs"][nm][p] * observed[p] for p in scm["parents"][nm])
        noise[nm] = observed[nm] - pred
    vals = do_intervention(artifact, target, value, observed)
    # add back abducted noise for non-intervened nodes
    return {nm: vals[nm] + (0.0 if nm == target else noise[nm])
            for nm in artifact["names"]}


def root_cause(artifact, symptom, top_k=3):
    """Walk the DAG upstream from `symptom`, ranking ancestors by the
    absolute product of path coefficients (linear effect strength)."""
    names = artifact["names"]
    children = {}
    for s, d in artifact["edges"]:
        children.setdefault(s, []).append(d)
    # all ancestors with path strengths
    strengths = {}

    def walk(node, prod, seen):
        for s, d in artifact["edges"]:
            if d == node and s not in seen:
                w = abs(artifact["scm"]["coefs"][d].get(s, 0.0)) * prod
                strengths[s] = max(strengths.get(s, 0.0), w)
                walk(s, w, seen | {s})

    walk(symptom, 1.0, {symptom})
    ranked = sorted(strengths.items(), key=lambda kv: -kv[1])[:top_k]
    return [{"cause": c, "effect_strength": round(float(s), 4)}
            for c, s in ranked]
