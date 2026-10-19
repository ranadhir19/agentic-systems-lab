"""Head-to-head evaluation on the frozen test suite.

Metrics (all deterministic, seeded):
  goal_recall        fraction of expected goals produced per case
  goal_precision     fraction of produced goals that were expected
  paraphrase_consistency  within a paraphrase group, same primary goal?
  multi_intent_f1    precision/recall over decomposed goal sets
  context_accuracy   context-dependent turns resolved via memory?
  clarification_precision  asked only when info genuinely missing?
  ooc_graceful       out-of-catalog -> goal produced (not "unknown"/crash)
  task_success       overall: recall==1.0 and no spurious goals

The traditional baseline can output exactly one label per turn, so it is
structurally capped on multi-intent cases — that is the point being
measured, not a trick of the grader.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import EXPECTED_MISSING_INFO, TEST_SUITE
from .classifier import DialogueManager
from .pipeline import InferencePipeline


@dataclass
class CaseScore:
    case_id: str
    system: str
    recall: float
    precision: float
    success: bool
    produced: list[str]
    expected: list[str]
    clarifications: int
    used_context: bool = False
    graceful_ooc: bool = True


def _score_case(case: dict, produced: list[str], clarifications: int,
                used_context: bool, system: str) -> CaseScore:
    expected = set(case["expect"])
    prod = set(produced)
    tp = len(expected & prod)
    recall = tp / len(expected) if expected else 1.0
    precision = tp / len(prod) if prod else 0.0
    spurious = prod - expected
    success = (recall == 1.0 and not spurious)
    graceful = True
    if "out_of_catalog" in case["tags"]:
        graceful = len(prod) > 0 and "unknown" not in prod
        if not graceful:
            success = False
    return CaseScore(case["id"], system, round(recall, 3),
                     round(precision, 3), success, sorted(prod),
                     sorted(expected), clarifications, used_context,
                     graceful)


def evaluate_classifier(seed: int = 0) -> list[CaseScore]:
    dm = DialogueManager(seed=seed)
    out: list[CaseScore] = []
    for case in TEST_SUITE:
        turns = dm.run_conversation(case["turns"])
        produced = [t.classification.intent for t in turns]
        clars = sum(1 for t in turns if t.asked_clarification)
        out.append(_score_case(case, produced, clars, False, "classifier"))
    return out


def evaluate_pipeline(seed: int = 0) -> list[CaseScore]:
    pipe = InferencePipeline(seed=seed)
    out: list[CaseScore] = []
    for case in TEST_SUITE:
        results = pipe.run_conversation(case["turns"])
        produced: list[str] = []
        for r in results:
            produced.extend(g.id for g in r.goals)
        clars = sum(len(r.questions_asked) for r in results)
        used_ctx = any(r.used_context for r in results)
        out.append(_score_case(case, produced, clars, used_ctx, "pipeline"))
    return out


def aggregate(scores: list[CaseScore]) -> dict:
    by_id = {s.case_id: s for s in scores}
    n = len(scores)
    agg: dict = {
        "n": n,
        "mean_recall": round(sum(s.recall for s in scores) / n, 3),
        "mean_precision": round(sum(s.precision for s in scores) / n, 3),
        "task_success": round(sum(s.success for s in scores) / n, 3),
        "total_clarifications": sum(s.clarifications for s in scores),
    }
    # phenomenon slices
    for tag in ["paraphrase", "multi_intent", "latent", "dynamic",
                "context", "out_of_catalog", "standard"]:
        sub = [s for s in scores
               if tag in next(c["tags"] for c in TEST_SUITE
                              if c["id"] == s.case_id)]
        if sub:
            agg[f"{tag}_success"] = round(
                sum(s.success for s in sub) / len(sub), 3)
            agg[f"{tag}_n"] = len(sub)
    # paraphrase consistency: within each paraphrase group, same primary goal?
    # groups: {p1,p2,p3} balance, {p4,p5} transfer
    group_cons = []
    for grp in (["p1", "p2", "p3"], ["p4", "p5"]):
        primaries = [tuple(by_id[i].produced[:1]) for i in grp
                     if by_id[i].produced]
        if primaries:
            group_cons.append(
                sum(1 for p in primaries if p == primaries[0]) / len(primaries))
    agg["paraphrase_consistency"] = round(
        sum(group_cons) / len(group_cons), 3) if group_cons else 0.0
    # context accuracy: d1, c1, c2 must succeed
    ctx = [by_id[i].success for i in ["d1", "c1", "c2"]]
    agg["context_accuracy"] = round(sum(ctx) / len(ctx), 3)
    # missing-info quality on o2 (laptop display)
    o2 = by_id["o2"]
    agg["o2_missing_info_ok"] = None  # filled by experiment via pipeline
    return agg
