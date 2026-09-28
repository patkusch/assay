"""Pulls the long-input combine-mode receipts into one table.

Reproducible: rerun any time a new combine mode gets measured, and it picks up whatever receipts exist.

    python bench/longinput_summary.py
"""
from __future__ import annotations

import json
from pathlib import Path

BENCH = Path(__file__).resolve().parent
RUNS = [
    ("max_evidence (default, 3 positions, 100 items)", "longinput-gemma3-4b-word.json"),
    ("mean_logprob (both position only, 60 items)", "longinput-gemma3-4b-word-meanlogprob.json"),
    ("head_tail (both position only, 60 items)", "longinput-gemma3-4b-word-headtail.json"),
    ("confident_weighted (both position only, 60 items)", "longinput-gemma3-4b-word-confweighted.json"),
]


def main() -> None:
    L = ["# Long-input combine modes: one table", "",
         "Built by `bench/longinput_summary.py` from the receipts in `bench/receipts/`. All runs are gemma3 4B, "
         "word scoring. The first row covers 3 padding positions and 100 items; the rest cover the hardest "
         "position (filler on both sides) on a smaller, shared 60-item slice, so those three are directly "
         "comparable to each other and only roughly comparable to the first.", "",
         "| Combine mode | Padded, plain | Padded, chunked | Chunked beat plain? |", "|---|---|---|---|"]
    for label, fname in RUNS:
        p = BENCH / "receipts" / fname
        if not p.exists():
            continue
        d = json.loads(p.read_text())["summary"]["pooled"]
        plain, chunked = d["padded_plain"], d["padded_chunked"]
        L.append(f"| {label} | {plain:.1%} | {chunked:.1%} | {'yes' if chunked > plain else 'no'} |")
    L += ["", "**None beat doing nothing.** Full explanation and per-task tables: "
              "[docs/LONG_INPUT.md](../docs/LONG_INPUT.md). The recommendation is to keep the state short, not to "
              "pick one of these.", ""]
    out = BENCH / "receipts" / "longinput-summary.md"
    out.write_text("\n".join(L) + "\n")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
