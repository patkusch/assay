"""The decision engine: order-shuffled scoring, calibration, typed answers."""
from __future__ import annotations

import math
import time

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
    labels = q.labels()
    per_order: list[dict[str, float]] = []
    for order in orderings(labels, n_orders):
        raw = backend.logprobs(state, q, order)
        if len(raw) != len(order):
            raise ValueError(f"backend returned {len(raw)} scores for {len(order)} labels")
        per_order.append(dict(zip(order, softmax(raw))))

    # average the per-order distributions; position bias cancels because every label rotates through every slot
    probs = {l: sum(p[l] for p in per_order) / len(per_order) for l in labels}
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
