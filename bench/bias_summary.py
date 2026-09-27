"""Runs label_bias.py over every system's receipts and every task, and writes one consolidated report.

Reproducible: rerun any time new or updated receipts land (a new model, a new clone, a rerun of an
existing one) and the report picks them up.

    python bench/bias_summary.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
from label_bias import label_bias, worst_bias  # noqa: E402

SYSTEMS = [
    ("assay + gemma3 4B (letter)", "v2-gemma3-4b.json"),
    ("assay + gemma3 4B (word)", "v2-gemma3-4b-word.json"),
    ("von 1.2", "v2-von.json"),
    ("openJev-verdict-2.0", "v2-verdict.json"),
]
TASKS = ["phishing", "command_safety", "routing", "urgency"]


def load(name: str) -> dict | None:
    p = BENCH / "receipts" / name
    return json.loads(p.read_text()) if p.exists() else None


def main() -> None:
    L = ["# Label bias summary", "",
         "Built by `bench/bias_summary.py` from the receipts in `bench/receipts/`. For each system and task, the "
         "biggest bias: the label predicted far more often than it is true, whether shuffling the option order made "
         "it better or worse, and (for routing and urgency, where every system showed a real bias) the full table.",
         "", "## Biggest bias per system and task, shuffled condition", "",
         "| System | Task | Label | Predicted ÷ true | Single order | Shuffled |", "|---|---|---|---|---|---|"]
    detail: dict[str, dict[str, dict]] = {t: {} for t in TASKS}
    for label, fname in SYSTEMS:
        rec = load(fname)
        if rec is None:
            continue
        for task in TASKS:
            rows_all = rec["tasks"].get(task, {}).get("items", [])
            rows_s = [r for r in rows_all if r["split"] == "test" and "single" in r]
            rows_h = [r for r in rows_all if r["split"] == "test" and "shuffled" in r]
            if not rows_s or not rows_h:
                continue
            bias_single = label_bias(rows_s, "single")
            bias_shuf = label_bias(rows_h, "shuffled")
            worst, ratio_s = worst_bias(bias_single)
            _, ratio_h = worst_bias(bias_shuf) if worst is None else (worst, bias_shuf.get(worst, {}).get("ratio", 0.0))
            if worst is None or max(ratio_s, ratio_h) <= 1.5:
                continue
            arrow = "worse" if ratio_h > ratio_s + 0.05 else ("better" if ratio_h < ratio_s - 0.05 else "about the same")
            L.append(f"| {label} | {task} | `{worst}` | {ratio_h:.2f}x | {ratio_s:.2f}x | {ratio_h:.2f}x ({arrow} after shuffling) |")
            detail[task][label] = bias_shuf
    for task in ("routing", "urgency"):
        if not detail[task]:
            continue
        labels = sorted({l for b in detail[task].values() for l in b})
        L += ["", f"## Full label bias, {task}, shuffled condition", "",
              "| System | " + " | ".join(labels) + " |", "|---|" + "---|" * len(labels)]
        for label, fname in SYSTEMS:
            if label not in detail[task]:
                continue
            b = detail[task][label]
            L.append(f"| {label} | " + " | ".join(f"{b[l]['ratio']:.2f}x" if l in b else "n/a" for l in labels) + " |")
    L += ["", "`ratio` is predicted share ÷ true share. 1.0x is unbiased; every system above 1.5x on a task is shown. "
              "A ratio could not be computed where a system has no receipts for that task.", ""]
    out = BENCH / "receipts" / "bias-summary.md"
    out.write_text("\n".join(L) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
