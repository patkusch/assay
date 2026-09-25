"""Turns a benchmark receipts file into a plain-English markdown scoreboard.

The scoreboard leads with the pass/fail verdict against the bar that was written down in docs/PLAN.md
BEFORE anything was measured:

  1. shuffling the option order must cut the order-flip rate versus a single ordering, and
  2. calibration must cut the expected calibration error versus the uncalibrated probabilities.

Failures are reported as plainly as passes. Nothing is left out because it looks bad.

    python bench/report.py bench/receipts/gemma3.json          # writes bench/receipts/gemma3.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

COND_NAMES = {
    "single": "Single order",
    "shuffled": "Shuffled",
    "calibrated": "Shuffled + calibrated",
    "llm_baseline": "Ordinary LLM answer",
}


def _pct(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x * 100:.1f}%"


def _num(x, d: int = 3) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.{d}f}"


def _ms(x) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.0f} ms"


def _get(receipts: dict, cond: str, task: str | None = None) -> dict | None:
    """The test-split metrics for a condition, pooled (task=None) or for one task; None if not run."""
    node = receipts["pooled"].get(cond) if task is None else receipts["tasks"][task]["conditions"].get(cond)
    return node.get("test") if node else None


def verdicts(receipts: dict) -> list[dict]:
    """The two pre-set bar checks: pooled over all tasks, plus how many individual tasks agree."""
    out = []
    tasks = list(receipts["tasks"])

    single, shuf = _get(receipts, "single"), _get(receipts, "shuffled")
    per = [(t, _get(receipts, "single", t)["flip_rate"], _get(receipts, "shuffled", t)["flip_rate"]) for t in tasks]
    improved = sum(1 for _, a, b in per if b < a)
    worse = sum(1 for _, a, b in per if b > a)
    ok = shuf["flip_rate"] < single["flip_rate"]
    if single["flip_rate"] == 0:
        ok = None  # a model that never flips on reversal is already order-proof: there is nothing for shuffling to cut
    out.append({
        "bar": "Shuffling the option order must cut the order-flip rate versus a single ordering.",
        "passed": ok, "before": single["flip_rate"], "after": shuf["flip_rate"],
        "detail": f"Order-flip rate went from {_pct(single['flip_rate'])} to {_pct(shuf['flip_rate'])} over {single['n']} test items. "
                  f"By task: lower in {improved}, higher in {worse}, unchanged in {len(per) - improved - worse}."
                  + ("" if single["flip_rate"] > 0 else " The single ordering never flipped, so there was nothing to cut: not applicable."),
    })

    cal = _get(receipts, "calibrated")
    if cal is None:
        out.append({"bar": "Calibration must cut expected calibration error versus the uncalibrated probabilities.", "passed": None,
                    "before": None, "after": None, "detail": "Not evaluated: the calibrator could not be fitted (too few dev items)."})
    else:
        per = [(t, _get(receipts, "shuffled", t)["ece"], _get(receipts, "calibrated", t)["ece"]) for t in tasks]
        improved = sum(1 for _, a, b in per if b < a)
        worse = sum(1 for _, a, b in per if b > a)
        ok = cal["ece"] < shuf["ece"]
        out.append({
            "bar": "Calibration must cut expected calibration error versus the uncalibrated probabilities.",
            "passed": ok, "before": shuf["ece"], "after": cal["ece"],
            "detail": f"Calibration error went from {_num(shuf['ece'])} to {_num(cal['ece'])} over {cal['n']} test items "
                      f"(against a single ordering it started at {_num(single['ece'])}). "
                      f"By task: lower in {improved}, higher in {worse}, unchanged in {len(per) - improved - worse}.",
        })
    return out


ROWS = [
    ("accuracy", "Accuracy", _pct, "How often the top answer matches the answer written by construction. Higher is better."),
    ("ece", "Calibration error (ECE)", _num, "How far stated confidence is from the actual hit rate, on average. 0.10 means about 10 points off. Lower is better."),
    ("brier", "Brier score", _num, "Punishes confident wrong answers; 0 is perfect; guessing evenly scores 0.5 on a yes/no question and 0.8 on five options. Lower is better."),
    ("flip_rate", "Order-flip rate", _pct, "Share of items whose top answer changes when the options are shown in reverse order. Lower is better."),
    ("latency_p50_ms", "Latency, typical (p50)", _ms, "Half of items were answered faster than this."),
    ("latency_p95_ms", "Latency, slow end (p95)", _ms, "Nineteen in twenty items were answered faster than this."),
]


def build_report(receipts: dict) -> str:
    cfg, ver = receipts["config"], receipts["versions"]
    conds = [c for c in COND_NAMES if _get(receipts, c) is not None]
    L: list[str] = []
    model = cfg.get("model") or ("keyword stand-in (no real model)" if cfg.get("backend") == "keyword" else cfg.get("backend"))
    L += [f"# assay scoreboard: {model}", "",
          f"Run at {receipts['timestamp']}. Backend `{cfg.get('backend')}`, {cfg.get('orders')} option orderings, "
          f"tasks: {', '.join(receipts['tasks'])}. Python {ver.get('python')}, assay {ver.get('assay', '?')}"
          + (f", Ollama {ver['ollama']}" if ver.get("ollama") else "") + ".", "",
          "Every number below is measured on the **test half** of each task only. The calibrator was fitted on the dev half and never "
          "graded on it. The right answers were written by construction, never by a model (see `bench/tasks/README.md`).", ""]

    if cfg.get("limit"):
        L += [f"> **Quick run:** only the first {cfg['limit']} items of each split were used. Do not quote these numbers.", ""]
    if cfg.get("backend") == "keyword":
        L += ["> **This run used the keyword stand-in, not a language model.** It only proves the plumbing works. "
              "Do not read anything about real models from it.", ""]

    L += ["## Did it clear the bar?", "",
          "The bar was set in `docs/PLAN.md` before any measuring.", ""]
    vs = verdicts(receipts)
    for v in vs:
        tag = "NOT APPLICABLE / NOT EVALUATED" if v["passed"] is None else ("PASS" if v["passed"] else "FAIL")
        L += [f"- **{tag}.** {v['bar']}", f"  {v['detail']}"]
    failed = any(v["passed"] is False for v in vs)
    unclear = any(v["passed"] is None for v in vs)
    overall = "FAIL" if failed else ("PASS (part not applicable)" if unclear else "PASS")
    L += ["", f"**Overall: {overall}.** " + ("At least one part of the bar was not met; that is the honest result of this run." if failed else
          "Every part of the bar that applies was met on this run." if unclear else "Both parts of the bar were met on this run."), ""]

    L += ["## Scoreboard (all tasks together, test half)", ""]
    head = "| Measure | " + " | ".join(COND_NAMES[c] for c in conds) + " | What it means |"
    L += [head, "|" + "---|" * (len(conds) + 2)]
    for key, label, fmt, meaning in ROWS:
        cells = []
        for c in conds:
            m = _get(receipts, c)
            cells.append(fmt(m.get(key)))
        L.append(f"| {label} | " + " | ".join(cells) + f" | {meaning} |")
    for cov in ("100", "80", "60", "40"):
        cells = [_pct(_get(receipts, c)["accuracy_at_coverage"][cov]) for c in conds]
        meaning = ("Accuracy if the system only answers its most confident " + cov + "% of items. It should rise as the share falls."
                   if cov != "100" else "Accuracy when answering everything (the same as Accuracy above).")
        L.append(f"| Accuracy at {cov}% coverage | " + " | ".join(cells) + f" | {meaning} |")
    cal = _get(receipts, "calibrated")
    if cal:
        L += ["", f"**Saying \"not sure\" (calibrated condition):** it abstained on {_pct(cal['abstain_rate'])} of items "
              f"(more than one answer could not be ruled out). On the items it did answer, it was right {_pct(cal['accuracy_when_answered'])} of the time. "
              f"The true answer was inside its answer set {_pct(cal.get('set_coverage'))} of the time; the target was {_pct(1 - cfg.get('alpha', 0.1))}. "
              f"Average set size: {_num(cal.get('avg_set_size'), 2)} answers."]
    L += [""]

    L += ["## By task (test half)", "",
          "| Task | Items | Flip rate: single → shuffled | ECE: shuffled → calibrated | Accuracy: single / shuffled / calibrated"
          " / ordinary LLM | Bar |", "|---|---|---|---|---|---|"]
    for t, tv in receipts["tasks"].items():
        s, sh, ca, bl = (_get(receipts, c, t) for c in ("single", "shuffled", "calibrated", "llm_baseline"))
        f_ok = sh["flip_rate"] < s["flip_rate"]
        e_ok = ca is not None and ca["ece"] < sh["ece"]
        accs = " / ".join(_pct(m["accuracy"]) if m else "n/a" for m in (s, sh, ca, bl))
        L.append(f"| {t} | {tv['n_test']} | {_pct(s['flip_rate'])} → {_pct(sh['flip_rate'])} | "
                 f"{_num(sh['ece'])} → {_num(ca['ece']) if ca else 'n/a'} | {accs} | "
                 f"flip {'n/a' if s['flip_rate'] == 0 else ('PASS' if f_ok else 'FAIL')}, ECE {'PASS' if e_ok else 'FAIL'} |")
    L += [""]

    bl = _get(receipts, "llm_baseline")
    if bl is not None and cal is not None:
        fails = sum(1 for t in receipts["tasks"].values() for r in t["items"] if "llm_baseline" in r and r["llm_baseline"]["failed"])
        L += ["## Against an ordinary LLM answer", "",
              "The ordinary answer asks the same model to write JSON with a stated confidence, and that confidence is graded as its probability.", ""]
        cmp_rows = [("Accuracy", "accuracy", "higher", cal["accuracy"], bl["accuracy"], _pct),
                    ("Calibration error", "ece", "lower", cal["ece"], bl["ece"], _num),
                    ("Brier score", "brier", "lower", cal["brier"], bl["brier"], _num),
                    ("Typical latency (p50)", "latency_p50_ms", "lower", cal["latency_p50_ms"], bl["latency_p50_ms"], _ms),
                    ("Slow-end latency (p95)", "latency_p95_ms", "lower", cal["latency_p95_ms"], bl["latency_p95_ms"], _ms)]
        L += ["| Measure | assay (shuffled + calibrated) | Ordinary LLM answer | Better |", "|---|---|---|---|"]
        for label, _k, better, a, b, fmt in cmp_rows:
            win = "tie" if a == b else ("assay" if (a > b) == (better == "higher") else "ordinary LLM")
            L.append(f"| {label} | {fmt(a)} | {fmt(b)} | {win} |")
        L += ["", f"The ordinary answer failed to produce a usable reply on {fails} items (counted as wrong). "
              "Note that assay's latency here includes several model calls per item (one per option ordering), so it can be slower than one "
              "ordinary call; the order-proofing is what that time buys.", ""]
    elif bl is None:
        L += ["## Against an ordinary LLM answer", "", "Not run in this receipts file (it needs a live Ollama model).", ""]

    L += ["## Read this before quoting any number", "",
          "- The tasks are synthetic, small (about 30 test items each) and labelled by the person who built the engine. Gaps of a few points can be noise.",
          "- Calibration was fitted on about 30 dev items per task. That is enough to run, not enough to be precise.",
          "- Accuracy at coverage on small sets moves in big steps: each item is worth several points at 40% coverage.",
          "- The order-flip check compares the top answer with the options shown in forward versus reversed order. It does not test rewording.",
          "- Full per-item predictions are in the receipts JSON next to this file, so every number can be recomputed.", ""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Write a plain-English scoreboard from a benchmark receipts file.")
    ap.add_argument("receipts")
    ap.add_argument("--out", default=None, help="markdown path; default is the receipts path with .md")
    args = ap.parse_args(argv)
    path = Path(args.receipts)
    md = build_report(json.loads(path.read_text()))
    out = Path(args.out) if args.out else path.with_suffix(".md")
    out.write_text(md)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
