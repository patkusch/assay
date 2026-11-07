"""Hand-over: a small model answers when it is sure, and a bigger model takes the rest.

The small model is asked first. If its answer is marked "not sure" (abstain) or its confidence is below `below`,
the same question goes to the big model and that answer is returned instead. Each answer says which model gave it.

Measured on our four tasks (bench/receipts/handover-4b-12b.md): gemma3 4B handing up below 70% confidence sent
49% of items to gemma3 12B and got 89.4% right, against 90.0% for the 12B alone, in 38% less time. Handing up the
same share of items at random got 81.9%, so the small model's calibrated confidence is what makes this work.
"""
from __future__ import annotations

import time
from dataclasses import replace

from .engine import decide_one
from .types import Backend, BackendError, Calibrator, Request, Response


def decide_with_handover(
    small: Backend,
    big: Backend,
    request: Request,
    *,
    below: float = 0.8,
    n_orders: int = 3,
    calibrators: dict[str, Calibrator] | None = None,
    big_calibrators: dict[str, Calibrator] | None = None,
    confidence_floor: float = 0.0,
) -> Response:
    """Answer every question with `small`, re-asking `big` where `small` is not sure or under `below`.

    `calibrators` belong to the small model and `big_calibrators` to the big one: a calibration fitted on one model
    is wrong for another, so they are never shared.
    """
    if not 0.0 <= below <= 1.0:
        raise ValueError("below must be between 0 and 1")
    t0 = time.perf_counter()
    small_name, big_name = getattr(small, "name", "small"), getattr(big, "name", "big")
    answers = {}
    for qid, q in request.questions.items():
        a = decide_one(small, request.state, q, n_orders=n_orders, calibrator=(calibrators or {}).get(qid),
                       confidence_floor=confidence_floor)
        if a.abstain or a.confidence < below:
            try:
                a = decide_one(big, request.state, q, n_orders=n_orders, calibrator=(big_calibrators or {}).get(qid),
                               confidence_floor=confidence_floor)
            except BackendError as e:
                raise BackendError(f"{small_name} was not sure about {qid!r} and the hand-over model {big_name} failed: {e}") from e
            a = replace(a, answered_by=big_name)
        else:
            a = replace(a, answered_by=small_name)
        answers[qid] = a
    return Response(answers, (time.perf_counter() - t0) * 1000, f"{small_name}, then {big_name} when unsure")
