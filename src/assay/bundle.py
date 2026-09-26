"""A calibration bundle: one file holding the fitted calibrator for each question, plus who made it.

Why: a calibration only makes sense for the model it was measured on. The bundle remembers which
backend and model it was fitted with, so a mismatch can be flagged instead of silently applied.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .calibrate import MIN_SAMPLES, TemperatureCalibrator
from .engine import average_probs
from .types import Backend, Question

FORMAT_VERSION = 1


def score_probs(backend: Backend, state: str, q: Question, n_orders: int = 3) -> dict[str, float]:
    """The model's probabilities before calibration: the same path `engine.decide_one` takes."""
    q.validate()
    return average_probs(backend, state, q, n_orders)[0]


def _truth_label(q: Question, truth: object) -> str:
    """Write a truth the way the question spells its labels (True -> yes, 3 -> '3')."""
    if q.type == "noul" and isinstance(truth, bool):
        return "yes" if truth else "no"
    if isinstance(truth, float) and truth.is_integer():
        truth = int(truth)
    return str(truth)


def questions_from_body(body: object) -> dict[str, Question]:
    """Read the `questions` out of a request-shaped JSON object. A `state` is not needed."""
    from .server import parse_request
    if isinstance(body, dict):
        body = {**body, "state": body.get("state", "")}
    return parse_request(body)[0].questions


class CalibrationBundle:
    """{question id -> TemperatureCalibrator}, plus where it came from and how well it held up."""

    def __init__(self, calibrators: dict[str, TemperatureCalibrator], *, backend_name: str = "unknown",
                 model: str | None = None, fitted_at: str | None = None, n_examples: dict[str, int] | None = None,
                 held_out: dict[str, dict | None] | None = None, notes: dict[str, str] | None = None) -> None:
        self.calibrators = calibrators
        self.backend_name = backend_name
        self.model = model
        self.fitted_at = fitted_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.n_examples = n_examples or {qid: int(c.report.get("n", 0)) for qid, c in calibrators.items()}
        self.held_out = held_out or {}
        self.notes = notes or {}

    # ---- checking ------------------------------------------------------------------------------

    def check(self, backend_name: str) -> str | None:
        """A warning in plain words if this bundle was fitted with a different backend, otherwise None."""
        if backend_name == self.backend_name:
            return None
        return (f"warning: this calibration was fitted with {self.backend_name!r} but you are using "
                f"{backend_name!r}. The numbers may be wrong for this model. Fit a new one with `assay calibrate`.")

    # ---- summary -------------------------------------------------------------------------------

    def summary(self) -> dict:
        """What is loaded, in a form fit for JSON: per question the sample count, T, alpha and held-out numbers."""
        questions = {}
        for qid, cal in self.calibrators.items():
            questions[qid] = {
                "n": self.n_examples.get(qid, 0),
                "T": cal.temperature,
                "alpha": cal.alpha,
                "held_out": self.held_out.get(qid),
                "note": self.notes.get(qid),
            }
        return {
            "format_version": FORMAT_VERSION,
            "backend": self.backend_name,
            "model": self.model,
            "fitted_at": self.fitted_at,
            "n_examples": sum(self.n_examples.values()),
            "question_ids": sorted(self.calibrators),
            "questions": questions,
        }

    # ---- saving --------------------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "format_version": FORMAT_VERSION,
            "backend": {"name": self.backend_name, "model": self.model},
            "fitted_at": self.fitted_at,
            "n_examples": sum(self.n_examples.values()),
            "questions": {
                qid: {
                    "n": self.n_examples.get(qid, 0),
                    "calibrator": json.loads(cal.to_json()),
                    "held_out": self.held_out.get(qid),
                    "note": self.notes.get(qid),
                }
                for qid, cal in self.calibrators.items()
            },
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def from_dict(cls, d: object) -> "CalibrationBundle":
        if not isinstance(d, dict) or "questions" not in d:
            raise ValueError("this is not a calibration file")
        if d.get("format_version") != FORMAT_VERSION:
            raise ValueError(f"unsupported calibration format {d.get('format_version')!r}; this assay reads {FORMAT_VERSION}")
        who = d.get("backend") or {}
        qs = d["questions"]
        return cls(
            {qid: TemperatureCalibrator.from_json(e["calibrator"]) for qid, e in qs.items()},
            backend_name=who.get("name", "unknown"),
            model=who.get("model"),
            fitted_at=d.get("fitted_at"),
            n_examples={qid: int(e.get("n", 0)) for qid, e in qs.items()},
            held_out={qid: e.get("held_out") for qid, e in qs.items()},
            notes={qid: e["note"] for qid, e in qs.items() if e.get("note")},
        )

    @classmethod
    def load(cls, path: str | Path) -> "CalibrationBundle":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


def fit_bundle(backend: Backend, questions: dict[str, Question], labelled: list[dict], n_orders: int = 3,
               alpha: float = 0.1, seed: int = 0) -> CalibrationBundle:
    """Score every labelled example with the backend and fit one calibrator per question.

    `labelled` rows look like {"question": id, "state": text, "truth": label}. A question that appears
    with fewer than 20 rows is refused. A question with no rows is left out of the bundle.
    With 40 or more rows the report is a held-out check (fit on half, test on the rest); with fewer it
    can only be measured on the same rows it was fitted on, and the note says so.
    """
    rows: dict[str, list[dict]] = {}
    for i, row in enumerate(labelled, 1):
        if not isinstance(row, dict) or not {"question", "state", "truth"} <= set(row):
            raise ValueError(f"labelled row {i} must have 'question', 'state' and 'truth'")
        if row["question"] not in questions:
            raise ValueError(f"labelled row {i} is about question {row['question']!r}, which is not in the questions")
        rows.setdefault(row["question"], []).append(row)
    for qid, rs in rows.items():
        if len(rs) < MIN_SAMPLES:
            raise ValueError(f"question {qid!r} has {len(rs)} labelled examples; need at least {MIN_SAMPLES}")
    if not rows:
        raise ValueError("no labelled examples given")

    calibrators: dict[str, TemperatureCalibrator] = {}
    held_out: dict[str, dict | None] = {}
    notes: dict[str, str] = {}
    counts: dict[str, int] = {}
    for qid, rs in rows.items():
        q = questions[qid]
        labels = q.labels()
        samples = []
        for i, r in enumerate(rs, 1):
            truth = _truth_label(q, r["truth"])
            if truth not in labels:
                raise ValueError(f"question {qid!r}, example {i}: truth {truth!r} is not one of {labels}")
            samples.append({"probs": score_probs(backend, str(r["state"]), q, n_orders), "truth": truth})
        cal = TemperatureCalibrator().fit(samples, alpha)  # the one that gets used: fitted on everything
        if len(samples) >= 2 * MIN_SAMPLES:
            held_out[qid] = TemperatureCalibrator().fit_holdout(samples, alpha, seed)
        else:
            held_out[qid] = None
            notes[qid] = (f"only {len(samples)} examples: scores were measured on the same examples used to fit, "
                          f"so they look better than they will in use. {2 * MIN_SAMPLES} or more allows a held-out check.")
        calibrators[qid] = cal
        counts[qid] = len(samples)
    return CalibrationBundle(calibrators, backend_name=getattr(backend, "name", "unknown"),
                             model=getattr(backend, "model", None), n_examples=counts,
                             held_out=held_out, notes=notes)


def load_labelled(path: str | Path) -> list[dict]:
    """Read a JSONL file of {"question", "state", "truth"} rows (blank lines are skipped)."""
    out = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            try:
                out.append(json.loads(line))
            except ValueError as e:
                raise ValueError(f"{path} line {n} is not valid JSON: {e}") from e
    return out


def describe(bundle: CalibrationBundle) -> str:
    """The bundle's results in plain English, one block per question."""
    lines = [f"Calibration fitted with {bundle.backend_name} on {bundle.fitted_at[:10]}."]
    for qid, cal in bundle.calibrators.items():
        n = bundle.n_examples.get(qid, 0)
        ho = bundle.held_out.get(qid)
        lines.append(f"\nQuestion {qid!r}: {n} labelled examples.")
        if ho:
            lines.append(f"  Checked on {ho['n_holdout']} examples the fit never saw.")
            lines.append(f"  Calibration error: {ho['ece_before']:.3f} before, {ho['ece_after']:.3f} after (lower is better).")
            lines.append(f"  The true answer was inside the not-sure set {ho['coverage'] * 100:.0f}% of the time "
                         f"(aimed for {ho['target_coverage'] * 100:.0f}%).")
        else:
            r = cal.report
            lines.append(f"  Not enough examples for a fair check, so these numbers use the same examples as the fit.")
            lines.append(f"  Calibration error: {r['ece_before']:.3f} before, {r['ece_after']:.3f} after (lower is better).")
            lines.append(f"  Aimed for the true answer being in the not-sure set {(1 - cal.alpha) * 100:.0f}% of the time.")
    return "\n".join(lines)
