"""Checks whether a model over- or under-predicts particular labels, regardless of whether it is right.

A model that is simply bad at a task still guesses roughly the true share of each label. A model with a
label bias favours one label far more than its true share: it reaches for a "safe" default when unsure.
That is a different and often bigger problem than raw accuracy, because no amount of reordering the
options or rewording the question fixes a favourite word; the fix has to touch the word itself (a
different prompt, a fine-tune, or a calibrated per-label correction).

    python bench/label_bias.py bench/receipts/v2-gemma3-4b-word.json --task routing
    python bench/label_bias.py bench/receipts/v2-gemma3-4b-word.json --task routing --cond single
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def label_bias(rows: list[dict], cond: str) -> dict:
    """Per label: how often it is the true answer, how often it is predicted, the ratio of the two, and
    what share of the model's WRONG predictions land on it (the "catch-all" share)."""
    n = len(rows)
    truths = [str(r["truth"]) for r in rows]
    preds = [r[cond]["top"] for r in rows]
    labels = sorted(set(truths) | set(preds))
    wrong = [(t, p) for t, p in zip(truths, preds) if t != p]
    out = {}
    for l in labels:
        true_rate = truths.count(l) / n
        pred_rate = preds.count(l) / n
        catchall = sum(1 for t, p in wrong if p == l) / len(wrong) if wrong else 0.0
        out[l] = {"true_rate": true_rate, "predicted_rate": pred_rate,
                  "ratio": (pred_rate / true_rate) if true_rate else float("inf"), "catchall_share": catchall}
    return out


def worst_bias(bias: dict) -> tuple[str, float]:
    """The label whose predicted share is furthest (in ratio) from its true share, excluding a 0-true-rate label."""
    scored = [(l, b["ratio"]) for l, b in bias.items() if b["true_rate"] > 0]
    return max(scored, key=lambda x: x[1]) if scored else (None, 0.0)


def markdown(model: str, task: str, cond: str, n: int, bias: dict) -> str:
    L = [f"# Label bias: {model}, {task} ({cond})", "",
         f"{n} test items. `ratio` is predicted share divided by true share: 1.0 means the model reaches for that "
         "label exactly as often as it should; well above 1.0 is a favourite default. `catchall share` is how "
         "often a WRONG answer lands on that label, out of all wrong answers.", "",
         "| Label | True share | Predicted share | Ratio | Catch-all share of wrong answers |", "|---|---|---|---|---|"]
    for l, b in sorted(bias.items(), key=lambda kv: -kv[1]["ratio"]):
        L.append(f"| {l} | {b['true_rate']:.1%} | {b['predicted_rate']:.1%} | {b['ratio']:.2f}x | {b['catchall_share']:.1%} |")
    worst, ratio = worst_bias(bias)
    if worst and ratio > 1.5:
        L += ["", f"**Biggest bias: `{worst}`, predicted {ratio:.2f}x as often as it is true.**"]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("receipts")
    ap.add_argument("--task", required=True)
    ap.add_argument("--cond", choices=["single", "shuffled", "calibrated"], default="shuffled")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    rec = json.load(open(args.receipts))
    rows = [r for r in rec["tasks"][args.task]["items"] if r["split"] == "test" and args.cond in r]
    if not rows:
        raise SystemExit(f"no test items with condition {args.cond!r} in task {args.task!r}")
    model = rec["config"].get("model") or rec["config"].get("backend")
    if rec["config"].get("scoring") and rec["config"]["scoring"] != "letter":
        model += f" ({rec['config']['scoring']} scoring)"
    bias = label_bias(rows, args.cond)
    md = markdown(model, args.task, args.cond, len(rows), bias)
    print(md)
    if args.out:
        Path(args.out).write_text(md)
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
