"""Compares the blind auditors' labels with the by-construction labels and writes the drop list.

The auditors saw only the item text and the written rules, never the answer key. This script is the
only place the two meet. Rules:
  * an item the auditor labelled differently is dropped (the written rule leaves it open to another reading);
  * an item the auditor flagged as ambiguous is dropped even if the labels match;
  * nothing is ever relabelled to match the auditor.
It prints agreement per task and how the easy/hard mix changed, so dropping cannot quietly make the set easier.

    python bench/audit_compare.py
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

BENCH = Path(__file__).resolve().parent
TASKS = ["phishing", "command_safety", "routing", "urgency"]


def main() -> None:
    drops: dict[str, list[str]] = {}
    lines = ["# Label audit", "",
             "Every item was labelled blind by an independent reader who saw only the text and the written rules. "
             "Items where the reader disagreed, or called the rules ambiguous, were dropped (never relabelled).", "",
             "| Task | Items audited | Agreed | Disagreed | Flagged ambiguous | Dropped | Hard share before → after |",
             "|---|---|---|---|---|---|---|"]
    detail = []
    for task in TASKS:
        rows = {r["id"]: r for r in (json.loads(l) for l in (BENCH / "tasks_v2" / f"{task}.jsonl").read_text().splitlines() if l.strip())}
        ans: dict = {}
        for half in "AB":
            ans.update(json.loads((BENCH / "audit" / f"{task}_{half}_answers.json").read_text()))
        missing = [i for i in rows if i not in ans]
        if missing:
            raise SystemExit(f"{task}: {len(missing)} items have no auditor label, e.g. {missing[:3]}")
        agreed = disagreed = amb = 0
        bad: list[str] = []
        confusion: Counter = Counter()
        for i, r in rows.items():
            a = ans[i]
            same = str(a["label"]) == str(r["truth"])
            if not same:
                disagreed += 1
                confusion[(r["truth"], str(a["label"]))] += 1
            if a.get("ambiguous"):
                amb += 1
            if same and not a.get("ambiguous"):
                agreed += 1
            else:
                bad.append(i)
                detail.append(f"- `{i}` truth={r['truth']} auditor={a['label']} ambiguous={bool(a.get('ambiguous'))} kind={r['kind']}: {a.get('note', '')}")
        drops[task] = [rows[i]["state"] for i in bad]
        n = len(rows)
        hard_before = sum(r["hard"] for r in rows.values()) / n
        kept = [r for i, r in rows.items() if i not in set(bad)]
        hard_after = sum(r["hard"] for r in kept) / max(1, len(kept))
        lines.append(f"| {task} | {n} | {agreed} ({agreed / n:.1%}) | {disagreed} ({disagreed / n:.1%}) | {amb} | {len(bad)} | "
                     f"{hard_before:.0%} → {hard_after:.0%} |")
        if confusion:
            lines_c = ", ".join(f"{t}→{a} ×{c}" for (t, a), c in confusion.most_common(6))
            detail.insert(0, f"**{task} disagreements (ours→auditor):** {lines_c}")
    (BENCH / "audit_drops.json").write_text(json.dumps(drops, indent=1, ensure_ascii=False) + "\n")
    lines += ["", "## What was dropped", ""] + detail
    (BENCH / "audit" / "AUDIT.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines[:12]))


if __name__ == "__main__":
    main()
