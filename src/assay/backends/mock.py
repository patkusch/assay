"""Deterministic backends for tests. No model, no network."""
from __future__ import annotations

from ..types import Question


class KeywordBackend:
    """Scores a label by how often its words appear in the state. Crude, but real enough to test plumbing."""
    name = "keyword"

    def logprobs(self, state: str, question: Question, labels: list[str]) -> list[float]:
        s = state.lower()
        return [float(s.count(l.lower())) * 2.0 for l in labels]


class PositionBiasedBackend:
    """Prefers whichever label is shown first, plus a small true signal. Used to prove the engine cancels position bias."""
    name = "position-biased"

    def __init__(self, truth: str, bias: float = 3.0, signal: float = 1.0):
        self.truth, self.bias, self.signal = truth, bias, signal

    def logprobs(self, state: str, question: Question, labels: list[str]) -> list[float]:
        return [(self.bias if i == 0 else 0.0) + (self.signal if l == self.truth else 0.0) for i, l in enumerate(labels)]
