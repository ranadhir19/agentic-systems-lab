"""Head-to-head experiments: intent classification vs intent inference.

Seeded and deterministic.  Regenerates:
    07-intent-inference/results/results.md
    07-intent-inference/results/charts.png

Run:  cd 07-intent-inference && python3 experiments/run_experiments.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from agentic_systems.intent_inference import (
    InferencePipeline,
    aggregate,
    evaluate_classifier,
    evaluate_pipeline,
)
from agentic_systems.intent_inference.catalog import (
    EXPECTED_MISSING_INFO,
    TEST_SUITE,
)

SEED = 7
HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "..", "results")


def check_o2_missing_info() -> dict:
    """Does the pipeline ask the expected diagnostic questions on o2?"""
    pipe = InferencePipeline(seed=SEED)
    res = pipe.run_conversation(
        ["My Apple laptop screen becomes dark after login"])[0]
    asked = " ".join(res.questions_asked).lower()
    want = EXPECTED_MISSING_INFO["o2"]
    hits = {k: (k in asked) for k in want}
    goals = [(g.id, g.confidence, g.constraints, g.missing_info)
             for g in res.goals]
    return {"questions": res.questions_asked, "hits": hits,
            "goals": goals, "response": res.response}


def main() -> None:
    clf_scores = evaluate_classifier(seed=SEED)
    pipe_scores = evaluate_pipeline(seed=SEED)
    clf = aggregate(clf_scores)
    pipe = aggregate(pipe_scores)
    o2 = check_o2_missing_info()
    pipe["o2_missing_info_ok"] = all(o2["hits"].values())

    # ---- results.md ----------------------------------------------------
    lines = ["# Intent inference vs intent classification — results", "",
             f"Seed {SEED}; {len(TEST_SUITE)} frozen test cases; "
             "both systems graded identically.", "",
             "## Aggregate metrics",
             "",
             "| Metric | Classifier (TF-IDF + softmax) | Inference pipeline |",
             "|---|---|---|"]
    for key in ["mean_recall", "mean_precision", "task_success",
                "paraphrase_consistency", "context_accuracy"]:
        lines.append(f"| {key} | {clf[key]} | {pipe[key]} |")
    lines += [
        f"| clarification turns (useless rephrase / targeted) "
        f"| {clf['total_clarifications']} / 0 "
        f"| 0 / {pipe['total_clarifications']} |",
        "",
        "## Success rate by phenomenon",
        "",
        "| Phenomenon | n | Classifier | Pipeline |",
        "|---|---|---|---|",
    ]
    for tag in ["paraphrase", "multi_intent", "latent", "dynamic",
                "context", "out_of_catalog", "standard"]:
        lines.append(
            f"| {tag} | {clf[f'{tag}_n']} "
            f"| {clf[f'{tag}_success']} | {pipe[f'{tag}_success']} |")
    lines += ["", "## Per-case detail (classifier)", "",
              "| Case | Utterance | Produced | Expected | Success | Clarify |",
              "|---|---|---|---|---|---|"]
    for s, case in zip(clf_scores, TEST_SUITE):
        lines.append(
            f"| {s.case_id} | {case['turns'][-1][:52]} "
            f"| {s.produced} | {s.expected} | {s.success} | {s.clarifications} |")
    lines += ["", "## Per-case detail (pipeline)", "",
              "| Case | Produced | Expected | Success | Targeted Qs | Used ctx |",
              "|---|---|---|---|---|---|"]
    for s, case in zip(pipe_scores, TEST_SUITE):
        lines.append(
            f"| {s.case_id} | {s.produced} | {s.expected} | {s.success} "
            f"| {s.clarifications} | {s.used_context} |")
    lines += ["",
              "## o2 walkthrough: laptop display (structured goal)",
              "",
              "Utterance: `My Apple laptop screen becomes dark after login`",
              ""]
    for gid, conf, cons, mi in o2["goals"]:
        lines.append(f"- goal `{gid}` (confidence {conf})")
        for c in cons:
            lines.append(f"  - constraint: {c}")
        for q in mi:
            lines.append(f"  - missing info: {q}")
    lines += ["",
              f"Questions asked: {o2['questions']}",
              f"Expected missing-info covered: {o2['hits']}",
              "",
              f"Pipeline response: {o2['response']}",
              "",
              "## Reading the numbers",
              "",
              "- The classifier is perfect on canonical phrasings (5/5 "
              "standard cases) and collapses everywhere else: 0% on "
              "multi-intent (one label cannot hold three goals), 0% on "
              "out-of-catalog, 40% on paraphrases.",
              "- Its 7 'clarifications' are all the same useless fallback "
              "('Sorry, I didn't understand. Please rephrase.').",
              "- The pipeline's 6 clarifications are targeted missing-info "
              "questions (diagnostic questions, dates, dress code) — asked "
              "only when the evidence check shows the info is absent.",
              "- No utterance ever yields 'unknown': the worst case is a "
              "best-effort `general_assist` goal with a clarification "
              "question (graceful degradation).",
              ""]
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "results.md"), "w") as f:
        f.write("\n".join(lines) + "\n")

    # ---- charts.png ----------------------------------------------------
    phenomena = ["paraphrase", "multi_intent", "latent", "dynamic",
                 "context", "out_of_catalog", "standard"]
    clf_vals = [clf[f"{t}_success"] for t in phenomena]
    pipe_vals = [pipe[f"{t}_success"] for t in phenomena]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle("Intent classification vs intent inference (seed 7, n=20)",
                 fontsize=14, fontweight="bold")

    ax = axes[0, 0]
    x = np.arange(len(phenomena))
    ax.bar(x - 0.2, clf_vals, 0.4, label="classifier", color="#f08787")
    ax.bar(x + 0.2, pipe_vals, 0.4, label="inference pipeline", color="#7ee2a8")
    ax.set_xticks(x)
    ax.set_xticklabels([p.replace("_", "\n") for p in phenomena], fontsize=9)
    ax.set_ylabel("task success rate")
    ax.set_ylim(0, 1.08)
    ax.legend(fontsize=9)
    ax.set_title("Success rate by phenomenon")

    ax = axes[0, 1]
    metrics = ["mean_recall", "mean_precision", "task_success",
               "paraphrase_consistency", "context_accuracy"]
    cv = [clf[m] for m in metrics]
    pv = [pipe[m] for m in metrics]
    x = np.arange(len(metrics))
    ax.bar(x - 0.2, cv, 0.4, label="classifier", color="#f08787")
    ax.bar(x + 0.2, pv, 0.4, label="inference pipeline", color="#7ee2a8")
    ax.set_xticks(x)
    ax.set_xticklabels([m.replace("_", "\n") for m in metrics], fontsize=8)
    ax.set_ylim(0, 1.08)
    ax.legend(fontsize=9)
    ax.set_title("Aggregate metrics")

    ax = axes[1, 0]
    ax.bar(["classifier\n'useless rephrase'", "pipeline\ntargeted questions"],
           [clf["total_clarifications"], pipe["total_clarifications"]],
           color=["#f08787", "#7ee2a8"])
    ax.set_ylabel("clarification turns")
    ax.set_title("Clarifications: fallback vs targeted")

    ax = axes[1, 1]
    ax.axis("off")
    txt = (
        "Headline deltas (pipeline − classifier)\n\n"
        f"task success:        {pipe['task_success']:.0%}  vs  {clf['task_success']:.0%}\n"
        f"multi-intent:        {pipe['multi_intent_success']:.0%}  vs  {clf['multi_intent_success']:.0%}\n"
        f"out-of-catalog:      {pipe['out_of_catalog_success']:.0%}  vs  {clf['out_of_catalog_success']:.0%}\n"
        f"paraphrase:          {pipe['paraphrase_success']:.0%}  vs  {clf['paraphrase_success']:.0%}\n"
        f"context accuracy:    {pipe['context_accuracy']:.0%}  vs  {clf['context_accuracy']:.0%}\n\n"
        "o2 missing-info questions asked: "
        f"{sum(o2['hits'].values())}/{len(o2['hits'])} expected\n"
        "Every number above is measured on the frozen suite."
    )
    ax.text(0.05, 0.95, txt, transform=ax.transAxes, fontsize=11,
            verticalalignment="top", fontfamily="monospace",
            bbox=dict(boxstyle="round", facecolor="#111724", edgecolor="#22304a"))

    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(os.path.join(RESULTS, "charts.png"), dpi=110,
                facecolor="#0b0e14")
    plt.close(fig)

    print("wrote results.md + charts.png")
    print(f"classifier success={clf['task_success']}  "
          f"pipeline success={pipe['task_success']}")
    print(f"o2 missing-info ok: {pipe['o2_missing_info_ok']}")


if __name__ == "__main__":
    main()
