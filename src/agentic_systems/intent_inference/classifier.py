"""Traditional baseline: intent classification pipeline.

Architecture (the decision-tree-with-NLP design from the concept):
    text -> preprocessing -> TF-IDF -> softmax regression -> intent label
    -> dialogue manager -> canned handler.

Implemented from scratch in numpy (no sklearn in this environment).
A low-confidence prediction falls back to "unknown".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np

from .catalog import INTENTS, TRAIN_UTTERANCES


def tokenize(text: str) -> list[str]:
    text = text.lower().replace("wi-fi", "wifi").replace("wi fi", "wifi")
    return re.findall(r"[a-z0-9']+", text)


class TfidfVectorizer:
    """Fit-once TF-IDF with sublinear TF. Deterministic."""

    def __init__(self) -> None:
        self.vocab: dict[str, int] = {}
        self.idf: np.ndarray | None = None

    def fit(self, docs: list[str]) -> "TfidfVectorizer":
        df: dict[str, int] = {}
        for d in docs:
            for t in set(tokenize(d)):
                df[t] = df.get(t, 0) + 1
        self.vocab = {t: i for i, t in enumerate(sorted(df))}
        n = len(docs)
        self.idf = np.array(
            [np.log((1 + n) / (1 + df[t])) + 1.0 for t in sorted(df)]
        )
        return self

    def transform(self, docs: list[str]) -> np.ndarray:
        assert self.idf is not None, "fit first"
        X = np.zeros((len(docs), len(self.vocab)))
        for i, d in enumerate(docs):
            toks = tokenize(d)
            if not toks:
                continue
            counts: dict[str, int] = {}
            for t in toks:
                counts[t] = counts.get(t, 0) + 1
            for t, c in counts.items():
                j = self.vocab.get(t)
                if j is not None:
                    X[i, j] = (1.0 + np.log(c)) * self.idf[j]
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return X / norms


class SoftmaxRegression:
    """Multinomial logistic regression, full-batch GD, seeded init."""

    def __init__(self, n_features: int, n_classes: int, seed: int = 0,
                 lr: float = 0.5, iters: int = 600, l2: float = 1e-3) -> None:
        rng = np.random.default_rng(seed)
        self.W = rng.normal(0, 0.01, (n_features, n_classes))
        self.b = np.zeros(n_classes)
        self.lr, self.iters, self.l2 = lr, iters, l2

    def _softmax(self, Z: np.ndarray) -> np.ndarray:
        Z = Z - Z.max(axis=1, keepdims=True)
        E = np.exp(Z)
        return E / E.sum(axis=1, keepdims=True)

    def fit(self, X: np.ndarray, y: np.ndarray) -> "SoftmaxRegression":
        n = X.shape[0]
        Y = np.zeros((n, self.b.shape[0]))
        Y[np.arange(n), y] = 1.0
        for _ in range(self.iters):
            P = self._softmax(X @ self.W + self.b)
            G = (P - Y) / n
            self.W -= self.lr * (X.T @ G + self.l2 * self.W)
            self.b -= self.lr * G.sum(axis=0)
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self._softmax(X @ self.W + self.b)


@dataclass
class Classification:
    intent: str          # or "unknown"
    confidence: float
    runner_up: str = ""
    runner_up_conf: float = 0.0


class IntentClassifier:
    """The traditional baseline. One utterance -> one label."""

    def __init__(self, seed: int = 0, unknown_threshold: float = 0.35) -> None:
        self.threshold = unknown_threshold
        docs, labels = [], []
        for intent in INTENTS:
            for u in TRAIN_UTTERANCES[intent]:
                docs.append(u)
                labels.append(INTENTS.index(intent))
        self.vec = TfidfVectorizer().fit(docs)
        X = self.vec.transform(docs)
        self.model = SoftmaxRegression(X.shape[1], len(INTENTS), seed=seed).fit(
            X, np.array(labels)
        )

    def classify(self, text: str) -> Classification:
        X = self.vec.transform([text])
        if not np.any(X):
            return Classification("unknown", 0.0)
        p = self.model.predict_proba(X)[0]
        order = np.argsort(-p)
        best, second = order[0], order[1]
        if p[best] < self.threshold:
            return Classification("unknown", float(p[best]),
                                  INTENTS[second], float(p[second]))
        return Classification(INTENTS[best], float(p[best]),
                              INTENTS[second], float(p[second]))


@dataclass
class DialogueTurn:
    user_text: str
    classification: Classification
    handler: str
    response: str
    asked_clarification: bool = False


class DialogueManager:
    """Routes one label -> one canned handler. No memory across turns."""

    HANDLERS = {
        "check_balance": "Your balance is $4,231.09.",
        "transfer_money": "Transfer initiated. Anything else?",
        "reset_password": "A password reset link was sent to your email.",
        "update_phone": "Your phone number has been updated.",
        "book_flight": "Flight booked. Confirmation sent.",
        "cancel_booking": "Your booking has been cancelled.",
        "track_order": "Your package arrives Thursday.",
        "laptop_support": "Please restart your laptop and try again.",
        "wifi_help": "Your Wi-Fi password is on the router sticker.",
        "book_hotel": "Hotel booked for 2 nights.",
        "interview_prep": "Here are generic interview tips: research the company...",
        "restaurant_suggestion": "Try Bella Italia downtown.",
        "unknown": "Sorry, I didn't understand. Please rephrase.",
    }

    def __init__(self, seed: int = 0) -> None:
        self.classifier = IntentClassifier(seed=seed)
        self.turns: list[DialogueTurn] = []

    def handle(self, text: str) -> DialogueTurn:
        c = self.classifier.classify(text)
        # The classic failure mode: low lexical overlap -> "unknown";
        # multi-intent utterances collapse to a single label.
        turn = DialogueTurn(
            user_text=text,
            classification=c,
            handler=c.intent,
            response=self.HANDLERS[c.intent],
            asked_clarification=(c.intent == "unknown"),
        )
        self.turns.append(turn)
        return turn

    def run_conversation(self, turns: list[str]) -> list[DialogueTurn]:
        self.turns = []
        return [self.handle(t) for t in turns]
