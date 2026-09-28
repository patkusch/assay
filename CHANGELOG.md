# Changelog

## Unreleased
- **Label bias, found and fixed.** `bench/label_bias.py` and `bench/bias_summary.py` found that every system we tried over-predicts one label on some tasks, most clearly "billing" on routing (1.7x-2.7x its true rate); reordering the options does not fix this, and can make it worse. `PriorCalibrator` corrects it: +3 to +9 accuracy points on every system, measured on real receipts, for a confidence-error cost that ranges from negligible to real. `assay calibrate --method prior` fits it, the bundle saves and loads it by kind. Fixed a bug along the way: a saved calibration bundle could previously only ever reload as the plain calibrator, silently dropping any other kind.
- **Wording matters more than option order.** The rewording test (`bench/rewording.py`) found the answer changes with how the question is worded on 27-37% of items, against 10.7% for reversed options. A question can carry `alternates` (other wordings); assay averages the odds across them. Measured: that beats a single wording, and simple majority voting across separate calls beats it by a point or two more.
- **Long input: three combine modes measured, none help.** `max_evidence`, `mean_logprob` and `head_tail` were all measured on real padded messages and all did worse than doing nothing; `docs/LONG_INPUT.md` explains the likely cause (an irrelevant chunk can look just as confident as the real one). A fourth mode, `confident_weighted`, was built to test the "discount an unsure chunk" idea but is not yet measured against a real model.
- Word scoring (`--scoring word|auto`): the model replies with the option's own word and that word's odds are read. On gemma3 4B it beat letter scoring on accuracy, order flips and calibrated confidence error, outside noise.
- gemma3 12B measured on an 80-per-split subset; `bench/compare.py` compares any two runs on shared items with bootstrap intervals. A second, larger 12B run (word scoring) failed twice under memory pressure and is not measured; the Ollama backend now retries once after a timeout, found from that failure.
- `decide --format pretty` for a readable terminal view; `docs/CHOOSING_SETTINGS.md`.
- Demo shows word scoring beside letter scoring.
- gemma3 4B run on the v2 set with bootstrap intervals (`bench/significance.py`); README rewritten with the real numbers and the routing weakness stated.
- Visual demo page (`docs/demo/index.html`) built from the saved receipts, with a live panel; `serve --cors` to allow it. Published at [patkusch.github.io/assay/demo](https://patkusch.github.io/assay/demo/) via GitHub Pages.
- Benchmark v2: 1,370 items, labelled by construction and checked blind; 203 ambiguous items dropped, never relabelled.
- Adapters and receipts for the open clones von and openJev-verdict-2.0.
- Scoreboard says "not applicable" when a model never flips under reordering, instead of failing it.
- Example requests, Makefile, and a doc on how assay lines up with Jev.

## 0.1.0 (2026-09-24)
- Engine: rotated option orders, averaged odds, typed answers with `stability`.
- Calibration: temperature scaling and a conformal "not sure" threshold, with honest held-out metrics.
- Ollama backend, `POST /v1/systemone` server and command line.
- Benchmark of 240 items with a generate-and-parse baseline and raw receipts.
