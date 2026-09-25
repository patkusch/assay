"""Are the gaps between conditions bigger than noise? Bootstrap 95% intervals from a receipts file.

Resamples the test items with replacement 2,000 times and recomputes each gap, so the interval says how far
the gap could move if a different sample of similar items had been drawn. If the interval includes zero, the
gap may be noise.

    python bench/significance.py bench/receipts/v2-gemma3-4b.json
"""
from __future__ import annotations

import argparse
import json
import random


def ece(rows, bins=10):
    n = len(rows)
    tot = 0.0
    for b in range(bins):
        r = [x for x in rows if min(bins - 1, int(x[0] * bins)) == b]
        if r:
            tot += len(r) / n * abs(sum(x[0] for x in r) / len(r) - sum(x[1] for x in r) / len(r))
    return tot


def top(probs):
    k = max(probs, key=probs.get)
    return k, probs[k]


def collect(rec):
    items = []
    for t in rec["tasks"].values():
        for it in t["items"]:
            if it["split"] != "test":
                continue
            row = {"truth": str(it["truth"])}
            for cond in ("single", "shuffled", "calibrated"):
                if cond in it:
                    k, p = top(it[cond]["probs"])
                    row[cond] = (p, int(k == row["truth"]))
                    if cond != "calibrated":
                        row[cond + "_flip"] = int(it[cond]["top"] != it[cond]["top_reversed"])
            b = it.get("llm_baseline")
            if b and not b.get("failed") and b.get("probs"):
                k, p = top(b["probs"])
                row["plain"] = (p, int(k == row["truth"]))
            items.append(row)
    return items


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("receipts")
    ap.add_argument("--draws", type=int, default=2000)
    args = ap.parse_args()
    items = collect(json.load(open(args.receipts)))
    rng = random.Random(0)
    n = len(items)
    gaps = {
        "Order-flip rate: shuffled minus one order": lambda s: sum(i["shuffled_flip"] - i["single_flip"] for i in s) / len(s),
        "Confidence error: calibrated minus shuffled": lambda s: ece([i["calibrated"] for i in s]) - ece([i["shuffled"] for i in s]),
        "Confidence error: shuffled minus one order": lambda s: ece([i["shuffled"] for i in s]) - ece([i["single"] for i in s]),
        "Accuracy: shuffled minus one order": lambda s: sum(i["shuffled"][1] - i["single"][1] for i in s) / len(s),
    }
    if all("plain" in i for i in items):
        gaps["Accuracy: assay (shuffled) minus plain answer"] = lambda s: sum(i["shuffled"][1] - i["plain"][1] for i in s) / len(s)
        gaps["Confidence error: assay calibrated minus plain answer"] = lambda s: ece([i["calibrated"] for i in s]) - ece([i["plain"] for i in s])
    print(f"{n} test items, {args.draws} resamples\n")
    print("| Gap | Observed | 95% interval | Clear of noise? |\n|---|---|---|---|")
    for name, fn in gaps.items():
        obs = fn(items)
        draws = sorted(fn([items[rng.randrange(n)] for _ in range(n)]) for _ in range(args.draws))
        lo, hi = draws[int(.025 * args.draws)], draws[int(.975 * args.draws) - 1]
        clear = "yes" if (lo > 0 or hi < 0) else "no"
        print(f"| {name} | {obs:+.3f} | {lo:+.3f} to {hi:+.3f} | {clear} |")


if __name__ == "__main__":
    main()
