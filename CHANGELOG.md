# Changelog

## Unreleased
- gemma3 4B run on the v2 set with bootstrap intervals (`bench/significance.py`); README rewritten with the real numbers and the routing weakness stated.
- Visual demo page (`docs/demo/index.html`) built from the saved receipts, with a live panel; `serve --cors` to allow it.
- Benchmark v2: 1,370 items, labelled by construction and checked blind; 203 ambiguous items dropped, never relabelled.
- Adapters and receipts for the open clones von and openJev-verdict-2.0.
- Scoreboard says "not applicable" when a model never flips under reordering, instead of failing it.
- Example requests, Makefile, and a doc on how assay lines up with Jev.

## 0.1.0 (2026-09-24)
- Engine: rotated option orders, averaged odds, typed answers with `stability`.
- Calibration: temperature scaling and a conformal "not sure" threshold, with honest held-out metrics.
- Ollama backend, `POST /v1/systemone` server and command line.
- Benchmark of 240 items with a generate-and-parse baseline and raw receipts.
