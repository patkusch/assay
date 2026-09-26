"""Does the answer change when the question is worded differently? (the rewording test)

Each test item is asked four ways: the original instructions and three hand-written rewordings in
`bench/rewordings.json`, all keeping every label definition. The items and their right answers do not change, so the
labels stay valid. We count how often the top answer differs between wordings. The option order is averaged over
`--orders` rotations as usual, so this isolates the effect of the wording.

    python bench/rewording.py --backend ollama --model gemma3 --scoring word --per-task 60 --out bench/receipts/rewording-gemma3-4b-word.json
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
sys.path.insert(0, str(BENCH.parent / "src"))

from assay import Question, decide_one  # noqa: E402
import run as bench_run  # noqa: E402


def variants(task_spec: dict, name: str) -> list[str]:
    """The original instructions first, then the hand-written rewordings."""
    extra = json.loads((BENCH / "rewordings.json").read_text())[name]
    return [task_spec["question"]["instructions"]] + extra


def make_question(spec: dict, instructions: str) -> Question:
    q = spec["question"]
    return Question(type=q["type"], instructions=instructions, options=q.get("options", []), levels=q.get("levels", 5))


def top_label(answer) -> str:
    return max(answer.probabilities, key=answer.probabilities.get)


def run(backend, per_task: int, orders: int, tasks_dir: Path, names: list[str] | None = None, progress=None) -> dict:
    tasks = bench_run.load_tasks(names, per_task)
    out = {"tasks": {}}
    for name, t in tasks.items():
        items = [r for r in t["items"] if r["split"] == "test"]
        vs = variants(t["spec"], name)
        rows = []
        for n, it in enumerate(items, 1):
            tops = []
            for text in vs:
                ans = decide_one(backend, it["state"], make_question(t["spec"], text), n_orders=orders)
                tops.append(top_label(ans))
            rows.append({"id": it["id"], "truth": str(it["truth"]), "hard": it.get("hard", False), "tops": tops})
            if progress and n % 20 == 0:
                progress(f"[{name}] {n}/{len(items)}")
        out["tasks"][name] = {"n_variants": len(vs), "items": rows}
    return out


def summarise(receipts: dict) -> dict:
    """Numbers per task and pooled: accuracy of each wording, and how often the answer changed with the wording."""
    summary = {"tasks": {}}
    pooled_any = pooled_pair = pooled_pairs = pooled_n = 0
    pooled_acc: list[list[int]] = []
    for name, t in receipts["tasks"].items():
        rows = t["items"]
        k = t["n_variants"]
        acc = [sum(r["tops"][v] == r["truth"] for r in rows) / len(rows) for v in range(k)]
        any_change = sum(len(set(r["tops"])) > 1 for r in rows) / len(rows)
        pairs = list(itertools.combinations(range(k), 2))
        pair_dis = sum(r["tops"][a] != r["tops"][b] for r in rows for a, b in pairs) / (len(rows) * len(pairs))
        summary["tasks"][name] = {"n": len(rows), "accuracy_by_wording": acc, "accuracy_spread": max(acc) - min(acc),
                                  "answer_changed_with_wording": any_change, "pairwise_disagreement": pair_dis}
        pooled_any += sum(len(set(r["tops"])) > 1 for r in rows)
        pooled_pair += sum(r["tops"][a] != r["tops"][b] for r in rows for a, b in pairs)
        pooled_pairs += len(rows) * len(pairs)
        pooled_n += len(rows)
        pooled_acc.append([sum(r["tops"][v] == r["truth"] for r in rows) for v in range(k)])
    k = len(pooled_acc[0])
    acc = [sum(a[v] for a in pooled_acc) / pooled_n for v in range(k)]
    summary["pooled"] = {"n": pooled_n, "accuracy_by_wording": acc, "accuracy_spread": max(acc) - min(acc),
                         "answer_changed_with_wording": pooled_any / pooled_n, "pairwise_disagreement": pooled_pair / pooled_pairs}
    return summary


def markdown(receipts: dict, summary: dict) -> str:
    cfg = receipts["config"]
    name = cfg.get("model") or cfg.get("backend")
    if cfg.get("scoring") and cfg["scoring"] != "letter":
        name += f" ({cfg['scoring']} scoring)"
    p = summary["pooled"]
    L = [f"# Rewording test: {name}", "",
         f"Run at {receipts['timestamp']}. {p['n']} test items, each asked with the original question and 3 rewordings that keep every label definition. "
         f"Option order was averaged over {cfg['orders']} rotations, so only the wording changes.", "",
         f"- **The answer changed with the wording on {p['answer_changed_with_wording']:.1%} of items** (at least one wording gave a different top answer).",
         f"- **Two wordings disagreed on {p['pairwise_disagreement']:.1%} of pairs** on average.",
         f"- **Accuracy by wording:** " + ", ".join(f"{a:.1%}" for a in p["accuracy_by_wording"]) + f" (spread {p['accuracy_spread'] * 100:.1f} points). The first is the original wording.", "",
         "| Task | Items | Answer changed with wording | Pairwise disagreement | Accuracy by wording | Spread |", "|---|---|---|---|---|---|"]
    for t, s in summary["tasks"].items():
        L.append(f"| {t} | {s['n']} | {s['answer_changed_with_wording']:.1%} | {s['pairwise_disagreement']:.1%} | "
                 + " / ".join(f"{a:.0%}" for a in s["accuracy_by_wording"]) + f" | {s['accuracy_spread'] * 100:.1f} pts |")
    L += ["", "The rewordings are in `bench/rewordings.json`. Each was written by hand to keep the same label definitions; a test checks the key terms are all still there. "
              "A few dozen items per task is small, so treat gaps of a few points as noise.", ""]
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--backend", choices=["keyword", "ollama"], default="keyword")
    ap.add_argument("--model", default="gemma3")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--scoring", choices=["letter", "word", "auto"], default="letter")
    ap.add_argument("--tasks", default="all")
    ap.add_argument("--per-task", type=int, default=60, help="test items per task (the first N of the test split)")
    ap.add_argument("--orders", type=int, default=3)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--tasks-dir", default="bench/tasks_v2")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    tasks_dir = (BENCH.parent / args.tasks_dir)
    bench_run.TASKS_DIR = tasks_dir
    backend = bench_run.make_backend(args.backend, args.model, args.host, args.timeout, args.scoring)
    names = None if args.tasks == "all" else [t.strip() for t in args.tasks.split(",")]
    receipts = run(backend, args.per_task, args.orders, tasks_dir, names, progress=lambda m: print(m, flush=True))
    receipts["config"] = {"backend": args.backend, "model": args.model if args.backend == "ollama" else None,
                          "scoring": args.scoring if args.backend == "ollama" else None, "orders": args.orders,
                          "per_task": args.per_task, "tasks_dir": args.tasks_dir}
    receipts["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = summarise(receipts)
    receipts["summary"] = summary
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipts, indent=1, ensure_ascii=False))
    out.with_suffix(".md").write_text(markdown(receipts, summary))
    print(f"receipts: {out}\nscoreboard: {out.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
