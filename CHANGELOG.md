# Changelog

## Unreleased
- **Label bias, found and fixed.** `bench/label_bias.py` and `bench/bias_summary.py` found that every system we tried over-predicts one label on some tasks, most clearly "billing" on routing (1.7x-2.7x its true rate); reordering the options does not fix this, and can make it worse. `PriorCalibrator` corrects it: +3 to +9 accuracy points on every system, measured on real receipts, for a confidence-error cost that ranges from negligible to real. `assay calibrate --method prior` fits it, the bundle saves and loads it by kind. Fixed a bug along the way: a saved calibration bundle could previously only ever reload as the plain calibrator, silently dropping any other kind.
- **Wording matters more than option order.** The rewording test (`bench/rewording.py`) found the answer changes with how the question is worded on 27-37% of items, against 10.7% for reversed options. A question can carry `alternates` (other wordings); assay averages the odds across them. Measured: that beats a single wording, and simple majority voting across separate calls beats it by a point or two more.
- **Long input: four combine modes measured, none help.** `max_evidence`, `mean_logprob`, `head_tail` and a new `confident_weighted` mode (weights chunks by their own top-vs-second confidence margin) were all measured on real padded messages and all did worse than doing nothing. `confident_weighted` gave the identical answer to plain averaging on every one of 60 items: real per-chunk confidence sits above 0.99 almost everywhere, filler included, so there was nothing to weight by. Recommendation unchanged: keep the state short.
- **Two shipped examples were quietly untested.** `examples/agent_command.json` and two others used a shorter, unbenchmarked wording. Caught live: the old wording called a safe force-push "destructive" (wrong, 85.5% confident); the benchmarked wording calls it "risky" (right, 99.99997%). All three examples now use the exact wording that was actually measured, and the published demo page was rebuilt to match.
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
