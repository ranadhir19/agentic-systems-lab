"""Intent inference quickstart: the same utterance, two architectures.

Shows the core contrast from the concept: a traditional intent classifier
(one label per utterance, no memory) versus the inference pipeline
(semantic understanding -> structured goals -> plan -> specialist agents).

Run:  python3 examples/07_intent_inference_quickstart.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agentic_systems.intent_inference import DialogueManager, InferencePipeline


def show_classifier(dm: DialogueManager, text: str) -> None:
    t = dm.handle(text)
    print(f"  classifier -> intent={t.classification.intent} "
          f"(conf={t.classification.confidence:.2f})")
    print(f"                response: {t.response}")


def show_pipeline(pipe: InferencePipeline, text: str) -> None:
    r = pipe.turn(text)
    goals = ", ".join(f"{g.id}({g.confidence:.2f})" for g in r.goals)
    print(f"  pipeline   -> goals=[{goals}]")
    for q in r.questions_asked:
        print(f"                asks: {q}")
    print(f"                response: {r.response}")


def main() -> None:
    dm = DialogueManager(seed=7)
    pipe = InferencePipeline(seed=7)

    print("1. Paraphrase the classifier never saw in training:")
    u = "Can you tell me whether I can afford lunch today?"
    print(f"  user: {u}")
    show_classifier(dm, u)
    show_pipeline(pipe, u)
    pipe.reset()

    print("\n2. Three intents in one utterance:")
    u = "I forgot my password, but I also changed my phone number, and I can't receive OTP"
    print(f"  user: {u}")
    show_classifier(dm, u)
    show_pipeline(pipe, u)
    pipe.reset()

    print("\n3. Meaning that depends on conversation history:")
    for u in ["Book me a hotel in Chicago", "Make it cheaper"]:
        print(f"  user: {u}")
        show_pipeline(pipe, u)

    print("\nDone: one label vs structured, contextual goal inference.")


if __name__ == "__main__":
    main()
