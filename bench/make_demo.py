"""Builds the visual demo page (docs/demo/index.html) from saved benchmark receipts.

The page replays real results: every bar, dot and line comes from the receipts files. Nothing is invented,
and no model needs to be running to build or open it. Run it again whenever new receipts land.

    python bench/make_demo.py                                  # uses whichever v2 receipts exist
    python bench/make_demo.py --system gemma=bench/receipts/v2-gemma3-4b.json --system von=bench/receipts/v2-von.json
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

BENCH = Path(__file__).resolve().parent
ROOT = BENCH.parent

TASK_INFO = {
    "phishing": ("Phishing emails", "Phishing"),
    "command_safety": ("Shell commands", "Commands"),
    "routing": ("Support routing", "Routing"),
    "urgency": ("Ticket urgency", "Urgency"),
}
SYSTEM_INFO = {
    "gemma": ("assay + gemma3 4B", "assay", "A small chat model whose odds for each option are read directly, then order-shuffled and calibrated by assay. 4 billion parameters, on a laptop."),
    "von": ("von 1.2", "von", "An open 395-million-parameter model that scores every option at once, run inside assay's scoring loop. Order-proof by design."),
    "verdict": ("openJev-verdict-2.0", "Verdict", "An open 151-million-parameter model, run inside assay's scoring loop. Its licence is unclear."),
}
DEFAULTS = [("gemma", "v2-gemma3-4b.json"), ("von", "v2-von.json"), ("verdict", "v2-verdict.json")]


def r3(x: float) -> float:
    return round(x, 4)


def build(systems: list[tuple[str, Path]]) -> dict:
    loaded = [(sid, json.loads(p.read_text())) for sid, p in systems]
    tasks_order = list(loaded[0][1]["tasks"])
    tasks: dict = {}
    for name in tasks_order:
        q = loaded[0][1]["tasks"][name]["question"]
        if q["type"] == "choice":
            labels = list(q["options"])
        elif q["type"] == "noul":
            labels = ["yes", "no"]
        else:
            labels = [str(i) for i in range(1, int(q.get("levels", 5)) + 1)]
        title, short = TASK_INFO.get(name, (name, name))
        tasks[name] = {"title": title, "short": short, "labels": labels}

    items: dict[str, dict] = {}
    sys_meta = []
    for sid, rec in loaded:
        label, short, sub = SYSTEM_INFO[sid]
        pooled = rec["pooled"]
        lat = {c: (pooled.get(k, {}).get("test") or {}).get("latency_p50_ms") for c, k in
               (("a", "single"), ("b", "shuffled"), ("c", "calibrated"), ("p", "llm_baseline"))}
        has_plain = False
        for name in tasks_order:
            labels = tasks[name]["labels"]
            for it in rec["tasks"][name]["items"]:
                if it["split"] != "test":
                    continue
                row = items.setdefault(it["id"], {"id": it["id"], "t": name, "x": None, "y": labels.index(str(it["truth"])),
                                                  "h": bool(it.get("hard")), "k": it.get("kind", ""), "s": {}})
                entry: dict = {}
                if "single" in it:
                    entry["a"] = [r3(it["single"]["probs"][l]) for l in labels]
                    entry["fs"] = int(it["single"]["top"] != it["single"]["top_reversed"])
                    entry["ta"] = labels.index(str(it["single"]["top"]))
                if "shuffled" in it:
                    entry["b"] = [r3(it["shuffled"]["probs"][l]) for l in labels]
                    entry["fb"] = int(it["shuffled"]["top"] != it["shuffled"]["top_reversed"])
                    entry["tb"] = labels.index(str(it["shuffled"]["top"]))
                if "calibrated" in it:
                    entry["c"] = [r3(it["calibrated"]["probs"][l]) for l in labels]
                    entry["set"] = sorted(labels.index(l) for l in it["calibrated"]["prediction_set"])
                    entry["tc"] = labels.index(str(it["calibrated"]["top"]))
                bl = it.get("llm_baseline")
                if bl and not bl.get("failed") and bl.get("probs"):
                    entry["p"] = [r3(bl["probs"][l]) for l in labels]
                    entry["tp"] = labels.index(str(bl["pred"]))
                    has_plain = True
                row["s"][sid] = entry
        sys_meta.append({"id": sid, "label": label, "short": short, "sub": sub, "hasPlain": has_plain, "lat": lat,
                         "model": rec["config"].get("model") or rec["config"].get("backend"), "run": rec["timestamp"][:10]})

    # attach item text from the task files (receipts do not carry it)
    tasks_dir = BENCH / "tasks_v2"
    for name in tasks_order:
        for line in (tasks_dir / f"{name}.jsonl").read_text().splitlines():
            r = json.loads(line)
            if r["id"] in items:
                items[r["id"]]["x"] = r["state"]
    missing = [i for i, r in items.items() if r["x"] is None]
    if missing:
        raise SystemExit(f"{len(missing)} receipt items are not in bench/tasks_v2, e.g. {missing[:3]}. Use receipts from the v2 set.")
    # keep only items every system measured, so the side-by-side is fair
    common = [r for r in items.values() if all(s["id"] in r["s"] for s in sys_meta)]

    examples = []
    for f in sorted((ROOT / "examples").glob("*.json")):
        body = json.loads(f.read_text())
        examples.append({"name": f.stem.replace("_", " "), "body": body})

    foot = (
        f"Built {date.today().isoformat()} from receipts in <code>bench/receipts/</code>: "
        + "; ".join(f"{s['label']} (run {s['run']})" for s in sys_meta)
        + f". {len(common):,} test items. The right answers were written by construction and each item was then checked "
        "by a blind reader; ambiguous items were dropped, never relabelled. The blind readers are models, so they may share "
        "blind spots with whoever wrote the items. The middle urgency levels lost the most items in that check. "
        "Von and Verdict are run as shipped inside assay's scoring loop with the adapters in <code>bench/adapters/</code>; "
        "their own benchmarks may show different numbers. "
        'Code and receipts: <a href="https://github.com/patkusch/assay">github.com/patkusch/assay</a>.'
    )
    return {"taskOrder": tasks_order, "tasks": tasks, "systems": sys_meta, "items": common, "examples": examples, "foot": foot}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--system", action="append", default=[], help="id=receipts.json, id one of gemma, von, verdict")
    ap.add_argument("--out", default=str(ROOT / "docs" / "demo" / "index.html"))
    args = ap.parse_args()
    if args.system:
        systems = []
        for spec in args.system:
            sid, path = spec.split("=", 1)
            if sid not in SYSTEM_INFO:
                raise SystemExit(f"unknown system id {sid!r}; choose from {', '.join(SYSTEM_INFO)}")
            systems.append((sid, Path(path)))
    else:
        systems = [(sid, BENCH / "receipts" / f) for sid, f in DEFAULTS if (BENCH / "receipts" / f).exists()]
    if not systems:
        raise SystemExit("no receipts found; run bench/run.py with --tasks-dir bench/tasks_v2 first")
    data = build(systems)
    html = (BENCH / "demo_template.html").read_text().replace("/*DATA*/", json.dumps(data, separators=(",", ":")).replace("</", "<\\/"))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB): {len(data['items'])} items, systems {[s['id'] for s in data['systems']]}")


if __name__ == "__main__":
    main()
