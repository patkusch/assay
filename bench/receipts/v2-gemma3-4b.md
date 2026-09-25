# assay scoreboard: gemma3

Run at 2026-09-24T23:19:37+00:00. Backend `ollama`, 3 option orderings, tasks: phishing, command_safety, routing, urgency. Python 3.14.3, assay 0.1.0, Ollama 0.33.3.

Every number below is measured on the **test half** of each task only. The calibrator was fitted on the dev half and never graded on it. The right answers were written by construction, never by a model (see `bench/tasks/README.md`).

## Did it clear the bar?

The bar was set in `docs/PLAN.md` before any measuring.

- **PASS.** Shuffling the option order must cut the order-flip rate versus a single ordering.
  Order-flip rate went from 20.3% to 10.7% over 912 test items. By task: lower in 3, higher in 1, unchanged in 0.
- **PASS.** Calibration must cut expected calibration error versus the uncalibrated probabilities.
  Calibration error went from 0.146 to 0.096 over 912 test items (against a single ordering it started at 0.265). By task: lower in 2, higher in 2, unchanged in 0.

**Overall: PASS.** Both parts of the bar were met on this run.

## Scoreboard (all tasks together, test half)

| Measure | Single order | Shuffled | Shuffled + calibrated | Ordinary LLM answer | What it means |
|---|---|---|---|---|---|
| Accuracy | 72.4% | 74.6% | 74.6% | 81.7% | How often the top answer matches the answer written by construction. Higher is better. |
| Calibration error (ECE) | 0.265 | 0.146 | 0.096 | 0.110 | How far stated confidence is from the actual hit rate, on average. 0.10 means about 10 points off. Lower is better. |
| Brier score | 0.538 | 0.429 | 0.382 | 0.322 | Punishes confident wrong answers; 0 is perfect; guessing evenly scores 0.5 on a yes/no question and 0.8 on five options. Lower is better. |
| Order-flip rate | 20.3% | 10.7% | 10.7% | n/a | Share of items whose top answer changes when the options are shown in reverse order. Lower is better. |
| Latency, typical (p50) | 205 ms | 598 ms | 598 ms | 639 ms | Half of items were answered faster than this. |
| Latency, slow end (p95) | 310 ms | 673 ms | 673 ms | 818 ms | Nineteen in twenty items were answered faster than this. |
| Accuracy at 100% coverage | 72.4% | 74.6% | 74.6% | 81.7% | Accuracy when answering everything (the same as Accuracy above). |
| Accuracy at 80% coverage | 74.7% | 80.7% | 81.1% | 82.7% | Accuracy if the system only answers its most confident 80% of items. It should rise as the share falls. |
| Accuracy at 60% coverage | 81.4% | 81.9% | 84.7% | 88.3% | Accuracy if the system only answers its most confident 60% of items. It should rise as the share falls. |
| Accuracy at 40% coverage | 88.5% | 80.8% | 93.2% | 85.8% | Accuracy if the system only answers its most confident 40% of items. It should rise as the share falls. |

**Saying "not sure" (calibrated condition):** it abstained on 55.5% of items (more than one answer could not be ruled out). On the items it did answer, it was right 91.1% of the time. The true answer was inside its answer set 90.0% of the time; the target was 90.0%. Average set size: 1.71 answers.

## By task (test half)

| Task | Items | Flip rate: single → shuffled | ECE: shuffled → calibrated | Accuracy: single / shuffled / calibrated / ordinary LLM | Bar |
|---|---|---|---|---|---|
| phishing | 232 | 15.1% → 0.0% | 0.090 → 0.083 | 76.7% / 84.5% / 84.5% / 75.4% | flip PASS, ECE PASS |
| command_safety | 280 | 41.8% → 18.6% | 0.134 → 0.138 | 74.6% / 74.6% / 74.6% / 75.4% | flip PASS, ECE FAIL |
| routing | 214 | 7.0% → 5.6% | 0.356 → 0.188 | 64.0% / 58.4% / 58.4% / 95.8% | flip PASS, ECE PASS |
| urgency | 186 | 9.7% → 18.3% | 0.082 → 0.089 | 73.1% / 80.6% / 80.6% / 82.8% | flip FAIL, ECE FAIL |

## Against an ordinary LLM answer

The ordinary answer asks the same model to write JSON with a stated confidence, and that confidence is graded as its probability.

| Measure | assay (shuffled + calibrated) | Ordinary LLM answer | Better |
|---|---|---|---|
| Accuracy | 74.6% | 81.7% | ordinary LLM |
| Calibration error | 0.096 | 0.110 | assay |
| Brier score | 0.382 | 0.322 | ordinary LLM |
| Typical latency (p50) | 598 ms | 639 ms | assay |
| Slow-end latency (p95) | 673 ms | 818 ms | assay |

The ordinary answer failed to produce a usable reply on 0 items (counted as wrong). Note that assay's latency here includes several model calls per item (one per option ordering), so it can be slower than one ordinary call; the order-proofing is what that time buys.

## Read this before quoting any number

- The tasks are synthetic and labelled by construction, with 186 to 280 test items per task. Gaps of a couple of points are still within noise for a single task; `bench/significance.py` gives intervals for the pooled gaps.
- Calibration was fitted on 93 to 141 dev items per task. Our calibration study found the error stops improving at about 80 examples per question.
- Accuracy at coverage moves in steps: each item is worth a fraction of a point, and more at 40% coverage.
- The order-flip check compares the top answer with the options shown in forward versus reversed order. It does not test rewording.
- Full per-item predictions are in the receipts JSON next to this file, so every number can be recomputed.
