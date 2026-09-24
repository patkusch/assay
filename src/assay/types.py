"""Shared types. Zero dependencies: everything is a dataclass that round-trips through JSON."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Protocol

QUESTION_TYPES = ("choice", "score", "noul")


class BackendError(RuntimeError):
    """A backend could not produce scores (model down, bad output). Never swallowed silently."""


@dataclass
class Question:
    """One decision. Same three kinds as the Jev API so requests are portable.

    choice: pick one of `options`.  score: place on a 1..`levels` scale.  noul: a yes/no statement.
    """
    type: str
    instructions: str
    options: list[str] = field(default_factory=list)  # choice only
    levels: int = 5                                   # score only, 2..10

    def labels(self) -> list[str]:
        """The candidate answers the backend must score, in canonical order."""
        if self.type == "choice":
            return list(self.options)
        if self.type == "score":
            return [str(i) for i in range(1, self.levels + 1)]
        if self.type == "noul":
            return ["yes", "no"]
        raise ValueError(f"unknown question type {self.type!r}")

    def validate(self) -> None:
        if self.type not in QUESTION_TYPES:
            raise ValueError(f"type must be one of {QUESTION_TYPES}")
        if self.type == "choice" and not (2 <= len(self.options) <= 255):
            raise ValueError("choice needs 2..255 options")
        if self.type == "choice" and len(set(self.options)) != len(self.options):
            raise ValueError("choice options must be unique")
        if self.type == "score" and not (2 <= self.levels <= 10):
            raise ValueError("score levels must be 2..10")


@dataclass
class Request:
    state: str
    questions: dict[str, Question]


@dataclass
class Answer:
    value: object                      # str (choice), float (score), float p(yes) (noul)
    probabilities: dict[str, float]    # over Question.labels(), sums to 1, after calibration
    confidence: float                  # probability of the top label
    stability: float                   # share of option orderings whose top pick matched the final one (1.0 = order-proof)
    prediction_set: list[str]          # labels the calibrator says cannot be ruled out (>=1)
    abstain: bool                      # True when the set has more than one label or confidence is under the floor
    calibrated: bool                   # whether a fitted calibrator was applied

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Response:
    answers: dict[str, Answer]
    latency_ms: float
    model: str

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "latency_ms": round(self.latency_ms, 2),
            "answers": {k: v.to_dict() for k, v in self.answers.items()},
        }


class Backend(Protocol):
    """Anything that can score candidate answers. Must NOT generate free text.

    `logprobs` receives the labels in the order the prompt should present them (the engine
    shuffles this to cancel position bias) and returns one raw log-score per label, aligned
    to that order. Scores need not be normalised; the engine softmaxes them.
    Raise BackendError on failure.
    """
    name: str

    def logprobs(self, state: str, question: Question, labels: list[str]) -> list[float]: ...


class Calibrator(Protocol):
    """Post-hoc fix-up of a probability vector. Implemented in assay.calibrate."""

    def transform(self, probs: dict[str, float]) -> dict[str, float]: ...

    def prediction_set(self, probs: dict[str, float]) -> list[str]: ...
