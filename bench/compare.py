"""Paired comparison of two receipts on the test items they share, with bootstrap intervals.

Use it to ask "is B really better than A?" for word against letter scoring, 12B against 4B, or assay against the
plain answer. Only items present in both files are used, so the two sides are graded on identical questions.
The interval comes from resampling those shared items 2,000 times: if it excludes zero, the gap is outside noise.

    python bench/compare.py A.json B.json                       # shuffled odds on both sides
    python bench/compare.py A.json B.json --cond-a plain        # A's plain generate-and-parse answer against B's shuffled odds
    python bench/compare.py A.json B.json --cond calibrated
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from significance import ece, top  # noqa: E402

CONDS = ("single", "shuffled", "calibrated", "plain")


def load(path: str) -> dict:
    """{item id: {"task", cond: (confidence, correct), cond+"_flip": 0/1}} for the test split."""
    rec = json.load(open(path))
    out: dict = {}
    for task, t in rec["tasks"].items():
        for it in t["items"]:
            if it["split"] != "test":
                continue
            row = {"task": task}
            truth = str(it["truth"])
            for cond in ("single", "shuffled", "calibrated"):
                if cond in it:
                    k, p = top(it[cond]["probs"])
                    row[cond] = (p, int(k == truth))
                    if cond != "calibrated":
                        row[cond + "_flip"] = int(it[cond]["top"] != it[cond]["top_reversed"])
            b = it.get("llm_baseline")
            if b and not b.get("failed") and b.get("probs"):
                k, p = top(b["probs"])
                row["plain"] = (p, int(k == truth))
            out[it["id"]] = row
    return out


def metrics(rows: list[dict], cond: str) -> dict:
    conf = [r[cond] for r in rows]
    flips = [r[cond + "_flip"] for r in rows if cond + "_flip" in r]
    return {"n": len(rows), "acc": sum(c for _, c in conf) / len(conf), "ece": ece(conf),
            "flip": (sum(flips) / len(flips)) if flips else None}


def boot(a_rows, b_rows, ca, cb, fn, draws, rng):
    n = len(a_rows)
    obs = fn(a_rows, b_rows, ca, cb)
    ds = sorted(fn([a_rows[i] for i in idx], [b_rows[i] for i in idx], ca, cb)
                for idx in ([rng.randrange(n) for _ in range(n)] for _ in range(draws)))
    return obs, ds[int(.025 * draws)], ds[int(.975 * draws) - 1]


def d_acc(a, b, ca, cb):
    return sum(r[cb][1] for r in b) / len(b) - sum(r[ca][1] for r in a) / len(a)


def d_ece(a, b, ca, cb):
    return ece([r[cb] for r in b]) - ece([r[ca] for r in a])


def d_flip(a, b, ca, cb):
    fa = [r[ca + "_flip"] for r in a]
    fb = [r[cb + "_flip"] for r in b]
    return sum(fb) / len(fb) - sum(fa) / len(fa)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--cond", choices=CONDS, default="shuffled", help="which numbers to compare on both sides")
    ap.add_argument("--cond-a", choices=CONDS, help="override the condition on side A")
    ap.add_argument("--cond-b", choices=CONDS, help="override the condition on side B")
    ap.add_argument("--draws", type=int, default=2000)
    args = ap.parse_args()
    ca, cb = args.cond_a or args.cond, args.cond_b or args.cond
    A, B = load(args.a), load(args.b)
    ids = sorted(i for i in A if i in B and ca in A[i] and cb in B[i])
    if not ids:
        raise SystemExit("no shared test items with those conditions")
    rng = random.Random(0)
    name = lambda p: Path(p).stem
    print(f"A = {name(args.a)} ({ca}), B = {name(args.b)} ({cb}); {len(ids)} shared test items, {args.draws} resamples.")
    print("Gaps are B minus A. A negative confidence-error or flip gap means B is better.\n")
    print("| Slice | Items | Right answers A → B | Gap | 95% interval | Outside noise? | Confidence error A → B | Gap | 95% interval | Outside noise? |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    slices = [("all tasks", ids)] + [(t, [i for i in ids if A[i]["task"] == t]) for t in sorted({A[i]["task"] for i in ids})]
    for label, sl in slices:
        if len(sl) < 20:
            continue
        a_rows, b_rows = [A[i] for i in sl], [B[i] for i in sl]
        ma, mb = metrics(a_rows, ca), metrics(b_rows, cb)
        o1, l1, h1 = boot(a_rows, b_rows, ca, cb, d_acc, args.draws, rng)
        o2, l2, h2 = boot(a_rows, b_rows, ca, cb, d_ece, args.draws, rng)
        f = lambda lo, hi: "yes" if (lo > 0 or hi < 0) else "no"
        print(f"| {label} | {len(sl)} | {ma['acc']:.1%} → {mb['acc']:.1%} | {o1:+.3f} | {l1:+.3f} to {h1:+.3f} | {f(l1, h1)} | "
              f"{ma['ece']:.3f} → {mb['ece']:.3f} | {o2:+.3f} | {l2:+.3f} to {h2:+.3f} | {f(l2, h2)} |")
    if ca in ("single", "shuffled") and cb in ("single", "shuffled"):
        a_rows, b_rows = [A[i] for i in ids], [B[i] for i in ids]
        o, lo, hi = boot(a_rows, b_rows, ca, cb, d_flip, args.draws, rng)
        ma, mb = metrics(a_rows, ca), metrics(b_rows, cb)
        print(f"\nAnswers that changed when the options were reversed: {ma['flip']:.1%} → {mb['flip']:.1%} "
              f"(gap {o:+.3f}, 95% interval {lo:+.3f} to {hi:+.3f}, {'outside' if (lo > 0 or hi < 0) else 'within'} noise).")


if __name__ == "__main__":
    main()
