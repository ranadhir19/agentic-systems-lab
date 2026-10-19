"""Smoke tests for intent_inference."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from agentic_systems.intent_inference import (
    DialogueManager,
    InferencePipeline,
    aggregate,
    evaluate_classifier,
    evaluate_pipeline,
)


def test_classifier_canonical():
    dm = DialogueManager(seed=0)
    c = dm.classifier.classify("What is my account balance?")
    assert c.intent == "check_balance" and c.confidence > 0.35


def test_classifier_fails_paraphrase():
    dm = DialogueManager(seed=0)
    c = dm.classifier.classify("Can you tell me whether I can afford lunch today?")
    assert c.intent == "unknown", c.intent  # the classic failure mode


def test_classifier_single_label_on_multi_intent():
    dm = DialogueManager(seed=0)
    t = dm.handle("I forgot my password, but I also changed my phone number, and I can't receive OTP")
    assert t.classification.intent in ("reset_password", "update_phone")


def test_pipeline_paraphrase_robust():
    pipe = InferencePipeline(seed=0)
    ids = set()
    for u in ["I want to know my balance", "How much money do I have?",
              "Can you tell me whether I can afford lunch today?"]:
        r = pipe.turn(u)
        ids.update(g.id for g in r.goals)
        pipe.reset()
    assert ids == {"check_balance"}, ids


def test_pipeline_multi_intent():
    pipe = InferencePipeline(seed=0)
    r = pipe.turn("My laptop is overheating and I also forgot my Wi-Fi password")
    got = {g.id for g in r.goals}
    assert got == {"laptop_support", "wifi_help"}, got


def test_pipeline_latent_intent():
    pipe = InferencePipeline(seed=0)
    r = pipe.turn("I'm hungry")
    assert {g.id for g in r.goals} == {"food_need"}


def test_pipeline_context():
    pipe = InferencePipeline(seed=0)
    pipe.turn("Book me a hotel in Chicago")
    r = pipe.turn("Make it cheaper")
    got = {g.id for g in r.goals}
    assert "refine_search" in got, got
    assert r.used_context is True


def test_pipeline_missing_info():
    pipe = InferencePipeline(seed=0)
    r = pipe.turn("My Apple laptop screen becomes dark after login")
    asked = " ".join(r.questions_asked).lower()
    assert "external monitor" in asked and "safe mode" in asked, asked


def test_pipeline_never_unknown():
    pipe = InferencePipeline(seed=0)
    r = pipe.turn("Can you write a haiku about my router?")
    assert {g.id for g in r.goals} == {"creative_writing"}


def test_headline_numbers():
    clf = aggregate(evaluate_classifier(seed=7))
    pipe = aggregate(evaluate_pipeline(seed=7))
    assert clf["task_success"] == 0.45, clf["task_success"]
    assert pipe["task_success"] == 1.0, pipe["task_success"]
    assert clf["multi_intent_success"] == 0.0
    assert pipe["multi_intent_success"] == 1.0
