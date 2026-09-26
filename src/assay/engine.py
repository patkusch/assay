"""The decision engine: order-shuffled scoring, calibration, typed answers."""
from __future__ import annotations

import math
import time
from dataclasses import replace

from .types import Answer, Backend, Calibrator, Question, Request, Response


def softmax(xs: list[float]) -> list[float]:
    m = max(xs)
    es = [math.exp(x - m) for x in xs]
    z = sum(es)
    return [e / z for e in es]


def orderings(labels: list[str], n: int) -> list[list[str]]:
    """Up to n rotations of the labels, evenly spaced, so each label leads (and trails) about equally often."""
    k = len(labels)
    n = max(1, min(n, k))
    shifts = sorted({round(i * k / n) % k for i in range(n)})
    return [labels[s:] + labels[:s] for s in shifts]


def average_probs(backend: Backend, state: str, q: Question, n_orders: int = 3) -> tuple[dict[str, float], list[dict[str, float]]]:
    """The model's odds for each label before calibration, averaged over rotated option orders and, if the question has
    `alternates`, over its other wordings too.

    Each wording is paired with a different option rotation, and the number of calls is whichever is larger: the
    number of wordings or the number of rotations. With no alternates this is exactly the plain rotation average.
    Returns the averaged odds and the per-call distributions (used to report how stable the answer was).
    """
    labels = q.labels()
    orders = orderings(labels, n_orders)
    wordings = [q.instructions] + list(q.alternates)
    per_call: list[dict[str, float]] = []
    for i in range(max(len(orders), len(wordings))):
        order = orders[i % len(orders)]
        wq = q if len(wordings) == 1 else replace(q, instructions=wordings[i % len(wordings)], alternates=[])
        raw = backend.logprobs(state, wq, order)
        if len(raw) != len(order):
            raise ValueError(f"backend returned {len(raw)} scores for {len(order)} labels")
        per_call.append(dict(zip(order, softmax(raw))))
    # position bias cancels because every label rotates through every slot
    return {l: sum(p[l] for p in per_call) / len(per_call) for l in labels}, per_call


def decide_one(
    backend: Backend,
    state: str,
    q: Question,
    *,
    n_orders: int = 3,
    calibrator: Calibrator | None = None,
    confidence_floor: float = 0.0,
) -> Answer:
    q.validate()
    probs, per_order = average_probs(backend, state, q, n_orders)
    top = max(probs, key=probs.get)
    stability = sum(1 for p in per_order if max(p, key=p.get) == top) / len(per_order)

    if calibrator is not None:
        probs = calibrator.transform(probs)
        top = max(probs, key=probs.get)
        pset = calibrator.prediction_set(probs)
    else:
        pset = [top]

    conf = probs[top]
    abstain = len(pset) > 1 or conf < confidence_floor

    if q.type == "choice":
        value: object = top
    elif q.type == "score":
        value = sum(int(l) * p for l, p in probs.items())
    else:
        value = probs["yes"]
    return Answer(value, probs, conf, stability, pset, abstain, calibrator is not None)


def decide(
    backend: Backend,
    request: Request,
    *,
    n_orders: int = 3,
    calibrators: dict[str, Calibrator] | None = None,
    confidence_floor: float = 0.0,
) -> Response:
    """Answer every question independently (questions never see each other, like Jev)."""
    t0 = time.perf_counter()
    answers = {
        qid: decide_one(
            backend, request.state, q,
            n_orders=n_orders,
            calibrator=(calibrators or {}).get(qid),
            confidence_floor=confidence_floor,
        )
        for qid, q in request.questions.items()
    }
    return Response(answers, (time.perf_counter() - t0) * 1000, getattr(backend, "name", "unknown"))
