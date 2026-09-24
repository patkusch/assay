"""Scores that answer one question: when the model says it is X% sure, is it right X% of the time?

A sample is a dict like ``{"probs": {"yes": 0.8, "no": 0.2}, "truth": "yes"}``. The model's guess is
the label with the highest probability, and its confidence is that probability.
"""
from __future__ import annotations

import math

_EPS = 1e-12


def _top(probs: dict[str, float]) -> tuple[str, float]:
    label = max(probs, key=probs.get)
    return label, probs[label]


def _need(samples: list[dict]) -> None:
    if not samples:
        raise ValueError("need at least one sample")


def accuracy(samples: list[dict]) -> float:
    """Share of samples where the model's top pick was the true answer."""
    _need(samples)
    return sum(1 for s in samples if _top(s["probs"])[0] == s["truth"]) / len(samples)


def brier(samples: list[dict]) -> float:
    """Average squared distance between the model's probabilities and the truth (0 is perfect, lower is better).

    For each sample the truth counts as 1 for the right label and 0 for the others, so a confident
    wrong answer is punished much harder than a hesitant one.
    """
    _need(samples)
    total = 0.0
    for s in samples:
        probs, truth = s["probs"], s["truth"]
        row = sum((p - (1.0 if label == truth else 0.0)) ** 2 for label, p in probs.items())
        if truth not in probs:  # the model gave the true answer no probability at all
            row += 1.0
        total += row
    return total / len(samples)


def nll(samples: list[dict]) -> float:
    """Average surprise at the true answer: minus the log of the probability given to it (lower is better)."""
    _need(samples)
    return sum(-math.log(max(s["probs"].get(s["truth"], 0.0), _EPS)) for s in samples) / len(samples)


def reliability_bins(samples: list[dict], bins: int = 10) -> list[dict]:
    """Group samples by how confident the model was and compare that confidence with how often it was right.

    Returns one dict per equal-width confidence band: ``lo``, ``hi``, ``n``, ``mean_confidence`` and
    ``accuracy``. Empty bands are kept (n=0, both means 0.0) so the list always has ``bins`` entries.
    A perfectly calibrated model has mean_confidence equal to accuracy in every band.
    """
    if bins < 1:
        raise ValueError("bins must be at least 1")
    conf_sum = [0.0] * bins
    hits = [0] * bins
    counts = [0] * bins
    for s in samples:
        label, conf = _top(s["probs"])
        i = min(int(conf * bins), bins - 1)  # a confidence of exactly 1.0 belongs to the top band
        counts[i] += 1
        conf_sum[i] += conf
        hits[i] += 1 if label == s["truth"] else 0
    return [
        {
            "lo": i / bins,
            "hi": (i + 1) / bins,
            "n": counts[i],
            "mean_confidence": conf_sum[i] / counts[i] if counts[i] else 0.0,
            "accuracy": hits[i] / counts[i] if counts[i] else 0.0,
        }
        for i in range(bins)
    ]


def ece(samples: list[dict], bins: int = 10) -> float:
    """Expected calibration error: the average gap between stated confidence and actual accuracy.

    0 means "80% sure" really is right 80% of the time. 0.2 means the model is off by 20 points on average.
    """
    _need(samples)
    n = len(samples)
    return sum(b["n"] / n * abs(b["mean_confidence"] - b["accuracy"]) for b in reliability_bins(samples, bins))


def accuracy_at_coverage(samples: list[dict], coverages: tuple[float, ...] = (1.0, 0.8, 0.6, 0.4)) -> dict[float, float]:
    """Accuracy if the model only answers the questions it is most sure about.

    For each coverage (e.g. 0.8) keep that share of samples, most confident first, and report accuracy
    on them. If confidence means anything, accuracy rises as coverage falls: that is the payoff of "not sure".
    """
    _need(samples)
    ranked = sorted(samples, key=lambda s: -_top(s["probs"])[1])
    hit = [1 if _top(s["probs"])[0] == s["truth"] else 0 for s in ranked]
    out: dict[float, float] = {}
    for c in coverages:
        if not 0 < c <= 1:
            raise ValueError("coverage must be in (0, 1]")
        k = max(1, math.ceil(c * len(ranked) - 1e-9))
        out[c] = sum(hit[:k]) / k
    return out
