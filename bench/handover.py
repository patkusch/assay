"""Measure the hand-over: a small model answers when it is sure and passes the rest to a bigger model.

Works from saved receipts, so no model needs to run. Only test items present in both files are used, so both
models are graded on identical questions. For each cut-off, an item is answered by the small model when its
confidence is at or above the cut-off, and by the big model otherwise. "not sure" hands up the items where the
small model's calibrated prediction set held more than one label (assay's abstain), whatever the confidence.

Time per item is the small model's own latency, plus the big model's when the item was handed up: the two calls
happen one after the other.

The "random hand-up" column answers: does picking WHICH items to hand up matter? It hands up the same share of
items chosen at random (averaged over 200 draws). If the real rule beats it, the small model's confidence is
carrying information; if not, you could save the calibration work and flip a coin.

    python bench/handover.py bench/receipts/v2-gemma3-4b.json bench/receipts/v2-gemma3-12b.json
    python bench/handover.py SMALL.json BIG.json --cond calibrated --out bench/receipts/handover-4b-12b
    python bench/handover.py SMALL.json BIG.json --cutoffs 0.65,0.7,0.75   # look closely around one cut-off
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from significance import top  # noqa: E402

CUTOFFS = (0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99)


def load(path: str, cond: str) -> dict[str, dict]:
    """{item id: {"task", "correct", "confidence", "unsure", "ms"}} for the test split."""
    rec = json.load(open(path))
    out: dict[str, dict] = {}
    for task, t in rec["tasks"].items():
        for it in t["items"]:
            if it["split"] != "test" or cond not in it:
                continue
            label, p = top(it[cond]["probs"])
            pset = it[cond].get("prediction_set") or [label]
            # the calibrated condition reuses the shuffled calls, so its time is the shuffled time
            ms = it[cond].get("latency_ms") or it.get("shuffled", {}).get("latency_ms") or 0.0
            out[it["id"]] = {"task": task, "correct": int(label == str(it["truth"])), "confidence": p,
                             "unsure": len(pset) > 1, "ms": float(ms)}
    return out


def hand_over(small: dict[str, dict], big: dict[str, dict], rule) -> dict:
    """Grade one rule. `rule(small item) -> True` means hand this item up to the big model."""
    ids = sorted(set(small) & set(big))
    handed = [i for i in ids if rule(small[i])]
    right = sum(big[i]["correct"] if i in set(handed) else small[i]["correct"] for i in ids)
    ms = sum(small[i]["ms"] + (big[i]["ms"] if i in set(handed) else 0.0) for i in ids)
    per_task: dict[str, dict] = {}
    for i in ids:
        t = per_task.setdefault(small[i]["task"], {"n": 0, "handed": 0, "right": 0})
        t["n"] += 1
        t["handed"] += int(i in set(handed))
        t["right"] += big[i]["correct"] if i in set(handed) else small[i]["correct"]
    hs = set(handed)
    return {"n": len(ids), "handed": len(handed), "share_handed": len(handed) / len(ids) if ids else 0.0,
            "accuracy": right / len(ids) if ids else 0.0, "ms_per_item": ms / len(ids) if ids else 0.0,
            # how the handed-up items would have fared with the small model, and how they fared with the big one
            "small_right_on_handed": sum(small[i]["correct"] for i in hs) / len(hs) if hs else None,
            "big_right_on_handed": sum(big[i]["correct"] for i in hs) / len(hs) if hs else None,
            "per_task": {k: {"n": v["n"], "share_handed": v["handed"] / v["n"], "accuracy": v["right"] / v["n"]}
                         for k, v in sorted(per_task.items())}}


def random_hand_over(small: dict[str, dict], big: dict[str, dict], share: float, draws: int = 200, seed: int = 0) -> float:
    """Mean accuracy when the same share of items is handed up at random: the yardstick the real rule must beat."""
    ids = sorted(set(small) & set(big))
    k = round(share * len(ids))
    rng = random.Random(seed)
    total = 0.0
    for _ in range(draws):
        chosen = set(rng.sample(ids, k))
        total += sum(big[i]["correct"] if i in chosen else small[i]["correct"] for i in ids) / len(ids)
    return total / draws


def sweep(small: dict[str, dict], big: dict[str, dict], cutoffs=CUTOFFS) -> list[dict]:
    rows = [dict(rule="small model alone", **hand_over(small, big, lambda s: False))]
    rows.append(dict(rule="hand up when not sure", **hand_over(small, big, lambda s: s["unsure"])))
    for c in cutoffs:
        rows.append(dict(rule=f"hand up below {c:.0%}", **hand_over(small, big, lambda s, c=c: s["confidence"] < c)))
    rows.append(dict(rule="big model alone", **hand_over(small, big, lambda s: True)))
    for r in rows:
        r["random_same_share"] = random_hand_over(small, big, r["share_handed"])
    return rows


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def markdown(rows: list[dict], small_name: str, big_name: str, cond: str) -> str:
    n = rows[0]["n"]
    out = [f"# Hand-over: {small_name} first, {big_name} when unsure", "",
           f"Made with `bench/handover.py` from saved receipts, {cond} odds, on the {n} test items both runs share. "
           "An item goes to the big model when the small model's confidence is below the cut-off. "
           "Time is the small model's call plus the big model's when it was handed up. "
           "\"Random, same share\" hands up the same number of items picked at random (mean of 200 draws).", "",
           "The last two columns look only at the handed-up items: how many the small model had right, and how many the big model got right.", "",
           "| Rule | Share handed up | Right answers | Random, same share | Time per item | Small model on handed-up | Big model on handed-up |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        on = lambda k: pct(r[k]) if r[k] is not None else "n/a"  # noqa: E731
        out.append(f"| {r['rule']} | {pct(r['share_handed'])} | {pct(r['accuracy'])} | {pct(r['random_same_share'])} | "
                   f"{r['ms_per_item'] / 1000:.2f} s | {on('small_right_on_handed')} | {on('big_right_on_handed')} |")
    tasks = list(rows[0]["per_task"])
    out += ["", "## Per task: right answers (share handed up)", "", "| Rule | " + " | ".join(tasks) + " |", "|---|" + "---|" * len(tasks)]
    for r in rows:
        out.append(f"| {r['rule']} | " + " | ".join(f"{pct(r['per_task'][t]['accuracy'])} ({pct(r['per_task'][t]['share_handed'])})" for t in tasks) + " |")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("small")
    ap.add_argument("big")
    ap.add_argument("--cond", default="calibrated", choices=["single", "shuffled", "calibrated"],
                    help="which odds to read from the small model's receipts (default calibrated)")
    ap.add_argument("--big-cond", default=None, help="odds to read from the big model (default: same as --cond)")
    ap.add_argument("--cutoffs", default=",".join(str(c) for c in CUTOFFS),
                    help="confidence cut-offs to try, between 0 and 1, comma-separated (default %(default)s)")
    ap.add_argument("--out", help="write OUT.json and OUT.md instead of printing")
    a = ap.parse_args(argv)
    small, big = load(a.small, a.cond), load(a.big, a.big_cond or a.cond)
    if not set(small) & set(big):
        print("the two receipts share no test items", file=sys.stderr)
        return 2
    try:
        cutoffs = tuple(float(c) for c in a.cutoffs.split(","))
        if not cutoffs or any(not 0 < c <= 1 for c in cutoffs):
            raise ValueError
    except ValueError:
        print("--cutoffs wants numbers between 0 and 1, comma-separated, like 0.6,0.7,0.8", file=sys.stderr)
        return 2
    rows = sweep(small, big, cutoffs)
    name = lambda p: json.load(open(p))["config"].get("model", Path(p).stem)  # noqa: E731
    small_name = name(a.small) + (" (word scoring)" if json.load(open(a.small))["config"].get("scoring") == "word" else "")
    md = markdown(rows, small_name, name(a.big), a.cond)
    if a.out:
        Path(a.out + ".json").write_text(json.dumps({"small": a.small, "big": a.big, "cond": a.cond, "rows": rows}, indent=2) + "\n")
        Path(a.out + ".md").write_text(md)
        print(f"wrote {a.out}.json and {a.out}.md")
    else:
        print(md, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
