"""Does the long-input wrapper help when the deciding text is buried in filler? (the long-input test)

Each test item is padded with filler that has nothing to do with any label, in three positions: filler before the
item, after it, or on both sides. Padding never changes the right answer, so the labels stay valid. Each padded item is
answered two ways: by the plain backend, and by `ChunkedBackend`, which splits long text into overlapping pieces and
combines the scores. The original short item is answered too, as the ceiling.

    python bench/longinput_eval.py --backend ollama --model gemma3 --scoring word --per-task 25 --pad-chars 12000 \\
        --out bench/receipts/longinput-gemma3-4b-word.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH.parent / "src"))

from assay import Question, decide_one  # noqa: E402
from assay.longinput import ChunkedBackend  # noqa: E402
import run as bench_run  # noqa: E402

# Filler sentences about nothing the tasks care about. A test checks none of the task's own words appear in them.
FILLER = [
    "The weather turned cold on Tuesday and the walk in was slower than usual.",
    "We moved to the second floor last month and the new desks still have their stickers on.",
    "The coffee machine by the lifts has been out of order since the spring.",
    "My colleague is away until the fourteenth, so the rota looks a bit thin for now.",
    "The train was late twice this week, which made the mornings feel longer.",
    "There was a long meeting about the seating plan, and nothing much was decided.",
    "The garden outside the window has finally started to flower after all the rain.",
    "Somebody left an umbrella by the front door and nobody has claimed it yet.",
    "The lunch order arrived twenty minutes late, though everyone was in good spirits.",
    "A cyclist stopped to ask for directions to the market, and we pointed him the right way.",
    "The printer on the third floor makes a strange noise when it warms up.",
    "It has been a busy season, and the calendar is filling up with small appointments.",
    "We repainted the meeting room in a pale green that nobody had asked for.",
    "The neighbours downstairs are learning the trumpet, which has become part of the background.",
    "After the storm the car park was covered in leaves and a few small branches.",
    "The new plants in the lobby seem to be thriving despite the low light.",
    "Everyone agreed the summer went by far too quickly this year.",
    "The bakery on the corner has started selling cinnamon buns on Fridays.",
    "There is a book club on Thursday evenings, though attendance has been patchy.",
    "The lift was serviced yesterday and now announces each floor in a cheerful voice.",
]
POSITIONS = ("before", "after", "both")


def filler(n_chars: int, rng: random.Random) -> str:
    """About `n_chars` of filler, in paragraphs, built from the fixed sentence bank."""
    out, total = [], 0
    while total < n_chars:
        para = " ".join(rng.choice(FILLER) for _ in range(rng.randint(3, 6)))
        out.append(para)
        total += len(para) + 2
    return "\n\n".join(out)


def pad(state: str, position: str, n_chars: int, rng: random.Random) -> str:
    if position == "before":
        return filler(n_chars, rng) + "\n\n" + state
    if position == "after":
        return state + "\n\n" + filler(n_chars, rng)
    return filler(n_chars // 2, rng) + "\n\n" + state + "\n\n" + filler(n_chars // 2, rng)


def top(answer) -> str:
    return max(answer.probabilities, key=answer.probabilities.get)


def evaluate(inner, chunked, items: list[dict], question: Question, pad_chars: int, orders: int, seed: int = 0) -> list[dict]:
    """One row per item: the answer on the short item, and on each padded version with and without chunking."""
    rng = random.Random(seed)
    rows = []
    for it in items:
        row = {"id": it["id"], "truth": str(it["truth"]), "short": top(decide_one(inner, it["state"], question, n_orders=orders))}
        for pos in POSITIONS:
            long_state = pad(it["state"], pos, pad_chars, rng)
            row[pos + "_plain"] = top(decide_one(inner, long_state, question, n_orders=orders))
            row[pos + "_chunked"] = top(decide_one(chunked, long_state, question, n_orders=orders))
        rows.append(row)
    return rows


def summarise(rows_by_task: dict[str, list[dict]]) -> dict:
    conds = ["short"] + [f"{p}_{m}" for p in POSITIONS for m in ("plain", "chunked")]

    def acc(rows, c):
        return sum(r[c] == r["truth"] for r in rows) / len(rows)

    out = {"tasks": {}, "pooled": {}}
    every = [r for rows in rows_by_task.values() for r in rows]
    for name, rows in rows_by_task.items():
        out["tasks"][name] = {"n": len(rows), **{c: acc(rows, c) for c in conds}}
    out["pooled"] = {"n": len(every), **{c: acc(every, c) for c in conds}}
    for m in ("plain", "chunked"):
        out["pooled"]["padded_" + m] = sum(acc(every, f"{p}_{m}") for p in POSITIONS) / len(POSITIONS)
    return out


def markdown(cfg: dict, timestamp: str, summary: dict) -> str:
    p = summary["pooled"]
    name = cfg.get("model") or cfg.get("backend")
    if cfg.get("scoring") and cfg["scoring"] != "letter":
        name += f" ({cfg['scoring']} scoring)"
    L = [f"# Long-input test: {name}", "",
         f"Run at {timestamp}. {p['n']} test items, each padded with about {cfg['pad_chars']:,} characters of unrelated filler in three positions. "
         f"Chunking splits text over {cfg['chunk_chars']:,} characters into overlapping pieces (`max_evidence`).", "",
         f"- **Short original item:** {p['short']:.1%} right (the ceiling).",
         f"- **Padded, plain backend:** {p['padded_plain']:.1%} right on average across the three positions.",
         f"- **Padded, with chunking:** {p['padded_chunked']:.1%} right on average.", "",
         "| Task | Items | Short | Filler before, plain | before, chunked | after, plain | after, chunked | both, plain | both, chunked |",
         "|---|---|---|---|---|---|---|---|---|"]
    for t, s in summary["tasks"].items():
        L.append(f"| {t} | {s['n']} | {s['short']:.0%} | " + " | ".join(f"{s[f'{pos}_{m}']:.0%}" for pos in POSITIONS for m in ("plain", "chunked")) + " |")
    L += ["", "The filler has nothing to do with any label, so padding never changes the right answer. "
              "A few dozen items per task is small: treat gaps of a few points as noise.", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backend", choices=["keyword", "ollama"], default="keyword")
    ap.add_argument("--model", default="gemma3")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--scoring", choices=["letter", "word", "auto"], default="letter")
    ap.add_argument("--tasks", default="all")
    ap.add_argument("--per-task", type=int, default=25)
    ap.add_argument("--pad-chars", type=int, default=12000)
    ap.add_argument("--chunk-chars", type=int, default=3000)
    ap.add_argument("--orders", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=180.0)
    ap.add_argument("--tasks-dir", default="bench/tasks_v2")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    bench_run.TASKS_DIR = BENCH.parent / args.tasks_dir
    inner = bench_run.make_backend(args.backend, args.model, args.host, args.timeout, args.scoring)
    chunked = ChunkedBackend(inner, max_chars=args.chunk_chars, overlap=min(300, args.chunk_chars // 10))
    names = None if args.tasks == "all" else [t.strip() for t in args.tasks.split(",")]
    tasks = bench_run.load_tasks(names, args.per_task)
    rows_by_task = {}
    for name, t in tasks.items():
        items = [r for r in t["items"] if r["split"] == "test"]
        rows_by_task[name] = evaluate(inner, chunked, items, t["question"], args.pad_chars, args.orders)
        print(f"[{name}] {len(items)} items done", flush=True)
    cfg = {"backend": args.backend, "model": args.model if args.backend == "ollama" else None,
           "scoring": args.scoring if args.backend == "ollama" else None, "orders": args.orders, "per_task": args.per_task,
           "pad_chars": args.pad_chars, "chunk_chars": args.chunk_chars}
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = summarise(rows_by_task)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"config": cfg, "timestamp": stamp, "summary": summary, "items": rows_by_task}, indent=1))
    out.with_suffix(".md").write_text(markdown(cfg, stamp, summary))
    print(f"receipts: {out}\nscoreboard: {out.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
