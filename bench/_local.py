"""Small, self-contained scoring helpers used by the benchmark.

Why these exist: the benchmark must be able to run (and be tested) on its own, before or without the
`assay.metrics` and `assay.calibrate` modules. Every function here takes "samples", a list of
`{"probs": {label: probability}, "truth": label}` (an optional `"pred"` overrides the top pick, and
`"pred": None` means "gave no usable answer", which counts as wrong).

Nothing here talks to a model.
"""
from __future__ import annotations

import math


def top_label(probs: dict[str, float]) -> str:
    """The most likely label. Ties go to whichever label comes first in the dict."""
    return max(probs, key=probs.get)


def _pred(s: dict) -> str | None:
    return s["pred"] if "pred" in s else top_label(s["probs"])


def _conf(s: dict) -> float:
    p = _pred(s)
    return s["probs"].get(p, 0.0) if p is not None else max(s["probs"].values())


def accuracy(samples: list[dict]) -> float:
    """Share of items where the top pick equals the truth."""
    return sum(1 for s in samples if _pred(s) == s["truth"]) / len(samples) if samples else float("nan")


def brier(samples: list[dict]) -> float:
    """Average squared distance between the probabilities and the truth (0 is perfect, 2 is worst)."""
    if not samples:
        return float("nan")
    tot = 0.0
    for s in samples:
        tot += sum((p - (1.0 if l == s["truth"] else 0.0)) ** 2 for l, p in s["probs"].items())
    return tot / len(samples)


def nll(samples: list[dict]) -> float:
    """Average surprise at the true answer, in nats (lower is better)."""
    if not samples:
        return float("nan")
    return sum(-math.log(max(s["probs"].get(s["truth"], 0.0), 1e-12)) for s in samples) / len(samples)


def ece(samples: list[dict], n_bins: int = 10) -> float:
    """Expected calibration error: how far stated confidence is from actual hit rate, averaged over confidence bins."""
    if not samples:
        return float("nan")
    bins: list[list[tuple[float, bool]]] = [[] for _ in range(n_bins)]
    for s in samples:
        c = _conf(s)
        b = min(int(c * n_bins), n_bins - 1)
        bins[b].append((c, _pred(s) == s["truth"]))
    n = len(samples)
    return sum(len(b) / n * abs(sum(c for c, _ in b) / len(b) - sum(1 for _, ok in b if ok) / len(b)) for b in bins if b)


def accuracy_at_coverage(samples: list[dict], coverage: float) -> float:
    """Accuracy on the most confident `coverage` share of items (ties keep input order)."""
    if not samples:
        return float("nan")
    k = max(1, math.ceil(coverage * len(samples) - 1e-9))
    ranked = sorted(samples, key=_conf, reverse=True)[:k]
    return accuracy(ranked)


def percentile(values: list[float], q: float) -> float:
    """The q-th percentile (0..100) with linear interpolation."""
    if not values:
        return float("nan")
    xs = sorted(values)
    pos = (len(xs) - 1) * q / 100.0
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


class LocalCalibrator:
    """Temperature scaling plus a split-conformal threshold, used only if `assay.calibrate` is not importable.

    Mirrors the shape of `assay.calibrate.TemperatureCalibrator`: `fit(samples, alpha)`, `transform`,
    `prediction_set`, and a `report` dict. Needs at least 20 labelled examples.
    """

    MIN_SAMPLES = 20

    def __init__(self) -> None:
        self.temperature = 1.0
        self.qhat: float | None = None
        self.alpha: float | None = None
        self.report: dict = {}

    @staticmethod
    def _scale(probs: dict[str, float], t: float) -> dict[str, float]:
        logs = {l: math.log(max(p, 1e-12)) / t for l, p in probs.items()}
        m = max(logs.values())
        es = {l: math.exp(v - m) for l, v in logs.items()}
        z = sum(es.values())
        return {l: e / z for l, e in es.items()}

    def fit(self, samples: list[dict], alpha: float = 0.1) -> "LocalCalibrator":
        if len(samples) < self.MIN_SAMPLES:
            raise ValueError(f"need at least {self.MIN_SAMPLES} labelled examples to calibrate, got {len(samples)}")
        grid = [math.exp(-3.0 + 6.0 * i / 200) for i in range(201)]
        self.temperature = min(grid, key=lambda t: nll([{"probs": self._scale(s["probs"], t), "truth": s["truth"]} for s in samples]))
        scores = sorted(1.0 - self.transform(s["probs"]).get(s["truth"], 0.0) for s in samples)
        k = math.ceil((len(scores) + 1) * (1 - alpha))
        self.qhat = 1.0 if k > len(scores) else scores[k - 1]
        self.alpha = alpha
        self.report = {"T": self.temperature, "qhat": self.qhat, "alpha": alpha, "n": len(samples), "source": "bench/_local.py"}
        return self

    def transform(self, probs: dict[str, float]) -> dict[str, float]:
        return self._scale(probs, self.temperature)

    def prediction_set(self, probs: dict[str, float]) -> list[str]:
        ranked = sorted(probs, key=lambda k: -probs[k])
        if self.qhat is None:
            return ranked[:1]
        chosen = [k for k in ranked if probs[k] >= 1.0 - self.qhat - 1e-12]
        return chosen or ranked[:1]
