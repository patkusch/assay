# Long-input combine modes: one table

Built by `bench/longinput_summary.py` from the receipts in `bench/receipts/`. All runs are gemma3 4B, word scoring. The first row covers 3 padding positions and 100 items; the rest cover the hardest position (filler on both sides) on a smaller, shared 60-item slice, so those three are directly comparable to each other and only roughly comparable to the first.

| Combine mode | Padded, plain | Padded, chunked | Chunked beat plain? |
|---|---|---|---|
| max_evidence (default, 3 positions, 100 items) | 59.3% | 53.7% | no |
| mean_logprob (both position only, 60 items) | 56.7% | 38.3% | no |
| head_tail (both position only, 60 items) | 56.7% | 35.0% | no |
| confident_weighted (both position only, 60 items) | 56.7% | 38.3% | no |

**None beat doing nothing.** Full explanation and per-task tables: [docs/LONG_INPUT.md](../docs/LONG_INPUT.md). The recommendation is to keep the state short, not to pick one of these.

