"""Builds the larger benchmark set (bench/tasks_v2/) from the original items plus the extra batches.

The original 240 items (bench/tasks/) are kept unchanged so the first receipts stay reproducible.
The new items come from bench/extra/<task>_extra.py. Every label is still set by construction: the
author of each item decided it from the written rule; no model chose any label.

Two clean-up steps, both recorded in the open:
  * exact and near duplicates (same text once case, spacing and digits are ignored) are dropped;
  * items listed in bench/audit_drops.json are dropped. Those are items an independent reader, working only from the
    written rules, disagreed with. A disagreement means the rule leaves the item ambiguous, so the item is removed.
    It is never relabelled to match a model.

    python bench/make_tasks_v2.py
"""
from __future__ import annotations

import importlib
import json
import random
import re
import shutil
import sys
from pathlib import Path

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH))
OUT = BENCH / "tasks_v2"
SEED = 20260925
TASKS = ["phishing", "command_safety", "routing", "urgency"]


def norm(text: str) -> str:
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", text.lower())).strip()


def main() -> None:
    OUT.mkdir(exist_ok=True)
    shutil.copy(BENCH / "tasks" / "tasks.json", OUT / "tasks.json")
    drops = json.loads((BENCH / "audit_drops.json").read_text()) if (BENCH / "audit_drops.json").exists() else {}
    for task in TASKS:
        base = [json.loads(l) for l in (BENCH / "tasks" / f"{task}.jsonl").read_text().splitlines() if l.strip()]
        items = [{"state": r["state"], "truth": r["truth"], "hard": r["hard"], "kind": r["kind"], "origin": "v1"} for r in base]
        mod = importlib.import_module(f"extra.{task}_extra")
        new = mod.items(random.Random(SEED))
        items += [{"state": r["state"], "truth": str(r["truth"]), "hard": bool(r["hard"]), "kind": r["kind"], "origin": "v2"} for r in new]
        dropped_norm = {norm(t) for t in drops.get(task, [])}
        seen, kept, n_dup, n_audit = set(), [], 0, 0
        for it in items:
            k = norm(it["state"])
            if k in seen:
                n_dup += 1
                continue
            if k in dropped_norm:
                n_audit += 1
                continue
            seen.add(k)
            kept.append(it)
        rng = random.Random(SEED)
        groups: dict[tuple, list[dict]] = {}
        for it in kept:
            groups.setdefault((it["truth"], it["hard"]), []).append(it)
        i = 0
        for key in sorted(groups):
            rng.shuffle(groups[key])
            for it in groups[key]:
                it["split"] = "dev" if i % 3 == 0 else "test"  # one third dev, two thirds test
                i += 1
        rng.shuffle(kept)
        counters = {"dev": 0, "test": 0}
        rows = []
        for it in kept:
            counters[it["split"]] += 1
            rows.append({"id": f"{task}-{it['split']}-{counters[it['split']]:03d}", "state": it["state"], "truth": it["truth"],
                         "split": it["split"], "hard": it["hard"], "kind": it["kind"], "origin": it["origin"]})
        (OUT / f"{task}.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n")
        labels = {}
        for r in rows:
            labels[r["truth"]] = labels.get(r["truth"], 0) + 1
        print(f"{task}: {len(rows)} items (dev {counters['dev']}, test {counters['test']}), hard {sum(r['hard'] for r in rows)}, "
              f"dropped {n_dup} duplicates + {n_audit} audit; labels {dict(sorted(labels.items()))}")


if __name__ == "__main__":
    main()
