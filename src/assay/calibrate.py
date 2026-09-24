"""Per-task calibration: learn from a few dozen labelled examples how much to trust the model.

Two things are learned from the same examples:

* a temperature that softens (or sharpens) the model's probabilities so "80% sure" comes out right
  about 80% of the time, and
* a conformal threshold that decides which answers cannot be ruled out, so that the true answer
  is inside the returned set at least ``1 - alpha`` of the time (on data like the examples).
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

from .metrics import brier, ece, nll

_EPS = 1e-12
MIN_SAMPLES = 20
_GOLD = (math.sqrt(5) - 1) / 2


def _apply_temperature(probs: dict[str, float], t: float) -> dict[str, float]:
    logs = {k: math.log(max(p, _EPS)) / t for k, p in probs.items()}
    m = max(logs.values())
    exps = {k: math.exp(v - m) for k, v in logs.items()}
    z = sum(exps.values())
    return {k: v / z for k, v in exps.items()}


class TemperatureCalibrator:
    """Temperature scaling plus a split-conformal prediction-set threshold.

    Before ``fit`` it does nothing: probabilities pass through and the prediction set is just the top pick.
    """

    def __init__(self) -> None:
        self.temperature: float = 1.0
        self.alpha: float | None = None
        self.qhat: float | None = None
        self.report: dict = {}

    @property
    def fitted(self) -> bool:
        return self.qhat is not None

    # ---- learning ------------------------------------------------------------------------------

    def fit(self, samples: list[dict], alpha: float = 0.1) -> "TemperatureCalibrator":
        """Learn the temperature and the conformal threshold from labelled examples.

        ``alpha`` is the miss rate you accept: 0.1 means the true answer should be inside the
        prediction set about 90% of the time. Needs at least 20 examples, because fewer cannot
        support a trustworthy threshold. Fills in ``report`` with before/after scores on these examples.
        """
        if len(samples) < MIN_SAMPLES:
            raise ValueError(f"need at least {MIN_SAMPLES} labelled examples to calibrate, got {len(samples)}")
        if not 0 < alpha < 1:
            raise ValueError("alpha must be between 0 and 1")

        self.temperature = self._best_temperature(samples)
        scaled = [self._scaled(s) for s in samples]

        # Conformal step: how surprised was the calibrated model by the truth? Take the score that
        # (1 - alpha) of examples stay under, with the small-sample correction of one extra rank.
        scores = sorted(1.0 - s["probs"].get(s["truth"], 0.0) for s in scaled)
        n = len(scores)
        k = math.ceil((n + 1) * (1 - alpha))
        self.qhat = 1.0 if k > n else scores[k - 1]
        self.alpha = alpha

        sizes = [len(self.prediction_set(s["probs"])) for s in scaled]
        self.report = {
            "n": n,
            "T": self.temperature,
            "alpha": alpha,
            "qhat": self.qhat,
            "ece_before": ece(samples),
            "ece_after": ece(scaled),
            "brier_before": brier(samples),
            "brier_after": brier(scaled),
            "nll_before": nll(samples),
            "nll_after": nll(scaled),
            "avg_set_size": sum(sizes) / n,
        }
        return self

    def fit_holdout(self, samples: list[dict], alpha: float = 0.1, seed: int = 0) -> dict:
        """The honest test: learn on a random half, then score on the half it never saw.

        Scores measured on the same examples used for fitting always look good. This reports the
        before/after metrics and how often the prediction set really contained the truth on the
        unseen half. Afterwards the calibrator is fitted on the first half only; call ``fit`` on
        everything to get the version you deploy.
        """
        if len(samples) < 2 * MIN_SAMPLES:
            raise ValueError(f"need at least {2 * MIN_SAMPLES} labelled examples for a holdout check, got {len(samples)}")
        order = list(range(len(samples)))
        random.Random(seed).shuffle(order)
        half = len(samples) // 2
        train = [samples[i] for i in order[:half]]
        test = [samples[i] for i in order[half:]]

        self.fit(train, alpha)
        scaled = [self._scaled(s) for s in test]
        sets = [self.prediction_set(s["probs"]) for s in scaled]
        covered = sum(1 for s, ps in zip(test, sets) if s["truth"] in ps) / len(test)
        return {
            "n_fit": len(train),
            "n_holdout": len(test),
            "T": self.temperature,
            "alpha": alpha,
            "qhat": self.qhat,
            "target_coverage": 1 - alpha,
            "coverage": covered,
            "avg_set_size": sum(len(ps) for ps in sets) / len(sets),
            "ece_before": ece(test),
            "ece_after": ece(scaled),
            "brier_before": brier(test),
            "brier_after": brier(scaled),
            "nll_before": nll(test),
            "nll_after": nll(scaled),
        }

    # ---- using it ------------------------------------------------------------------------------

    def transform(self, probs: dict[str, float]) -> dict[str, float]:
        """Return the probabilities after applying the learned temperature (unchanged before fitting)."""
        if not self.fitted:
            return dict(probs)
        return _apply_temperature(probs, self.temperature)

    def prediction_set(self, probs: dict[str, float]) -> list[str]:
        """The answers that cannot be ruled out, most likely first. Never empty: the top pick is always in.

        ``probs`` should already be calibrated (the output of ``transform``). One label means the
        model is sure enough to commit; more than one means it should say "not sure".
        """
        ranked = sorted(probs, key=lambda k: -probs[k])
        if not ranked:
            return []
        if not self.fitted:
            return ranked[:1]
        cutoff = 1.0 - self.qhat - 1e-12
        chosen = [k for k in ranked if probs[k] >= cutoff]
        return chosen or ranked[:1]

    # ---- saving --------------------------------------------------------------------------------

    def to_json(self) -> str:
        """Serialise what was learned so it can be reloaded without the training examples."""
        return json.dumps(
            {
                "version": 1,
                "temperature": self.temperature,
                "alpha": self.alpha,
                "qhat": self.qhat,
                "report": self.report,
            },
            indent=2,
        )

    @classmethod
    def from_json(cls, text: str | dict) -> "TemperatureCalibrator":
        """Rebuild a calibrator from ``to_json`` output (a string or the parsed dict)."""
        d = json.loads(text) if isinstance(text, str) else text
        cal = cls()
        cal.temperature = float(d["temperature"])
        cal.alpha = d.get("alpha")
        cal.qhat = d.get("qhat")
        cal.report = d.get("report") or {}
        if cal.temperature <= 0:
            raise ValueError("temperature must be positive")
        return cal

    def save(self, path: str | Path) -> None:
        """Write the calibrator to a JSON file."""
        Path(path).write_text(self.to_json() + "\n")

    @classmethod
    def load(cls, path: str | Path) -> "TemperatureCalibrator":
        """Read a calibrator written by ``save``."""
        return cls.from_json(Path(path).read_text())

    # ---- internals -----------------------------------------------------------------------------

    def _scaled(self, sample: dict) -> dict:
        return {"probs": _apply_temperature(sample["probs"], self.temperature), "truth": sample["truth"]}

    @staticmethod
    def _best_temperature(samples: list[dict]) -> float:
        """Find the temperature that makes the true answers least surprising (search over log T in [-3, 3])."""
        def loss(log_t: float) -> float:
            t = math.exp(log_t)
            return nll([{"probs": _apply_temperature(s["probs"], t), "truth": s["truth"]} for s in samples])

        lo, hi = -3.0, 3.0
        c = hi - _GOLD * (hi - lo)
        d = lo + _GOLD * (hi - lo)
        fc, fd = loss(c), loss(d)
        for _ in range(60):
            if fc < fd:
                hi, d, fd = d, c, fc
                c = hi - _GOLD * (hi - lo)
                fc = loss(c)
            else:
                lo, c, fc = c, d, fd
                d = lo + _GOLD * (hi - lo)
                fd = loss(d)
        return math.exp((lo + hi) / 2)
