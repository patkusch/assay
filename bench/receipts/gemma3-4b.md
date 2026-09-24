# assay scoreboard: gemma3

Run at 2026-09-24T15:18:45+00:00. Backend `ollama`, 3 option orderings, tasks: phishing, command_safety, routing, urgency. Python 3.14.3, assay 0.1.0, Ollama 0.33.3.

Every number below is measured on the **test half** of each task only. The calibrator was fitted on the dev half and never graded on it. The right answers were written by construction, never by a model (see `bench/tasks/README.md`).

## Did it clear the bar?

The bar was set in `docs/PLAN.md` before any measuring.

- **PASS.** Shuffling the option order must cut the order-flip rate versus a single ordering.
  Order-flip rate went from 15.8% to 12.5% over 120 test items. By task: lower in 2, higher in 2, unchanged in 0.
- **PASS.** Calibration must cut expected calibration error versus the uncalibrated probabilities.
  Calibration error went from 0.135 to 0.119 over 120 test items (against a single ordering it started at 0.202). By task: lower in 1, higher in 3, unchanged in 0.

**Overall: PASS.** Both parts of the bar were met on this run.

## Scoreboard (all tasks together, test half)

| Measure | Single order | Shuffled | Shuffled + calibrated | Ordinary LLM answer | What it means |
|---|---|---|---|---|---|
| Accuracy | 78.3% | 80.0% | 80.0% | 79.2% | How often the top answer matches the answer written by construction. Higher is better. |
| Calibration error (ECE) | 0.202 | 0.135 | 0.119 | 0.129 | How far stated confidence is from the actual hit rate, on average. 0.10 means about 10 points off. Lower is better. |
| Brier score | 0.410 | 0.352 | 0.339 | 0.362 | Punishes confident wrong answers; 0 is perfect; guessing evenly scores 0.5 on a yes/no question and 0.8 on five options. Lower is better. |
| Order-flip rate | 15.8% | 12.5% | 12.5% | n/a | Share of items whose top answer changes when the options are shown in reverse order. Lower is better. |
| Latency, typical (p50) | 202 ms | 605 ms | 605 ms | 576 ms | Half of items were answered faster than this. |
| Latency, slow end (p95) | 218 ms | 642 ms | 642 ms | 715 ms | Nineteen in twenty items were answered faster than this. |
| Accuracy at 100% coverage | 78.3% | 80.0% | 80.0% | 79.2% | Accuracy when answering everything (the same as Accuracy above). |
| Accuracy at 80% coverage | 84.4% | 86.5% | 87.5% | 85.4% | Accuracy if the system only answers its most confident 80% of items. It should rise as the share falls. |
| Accuracy at 60% coverage | 86.1% | 90.3% | 90.3% | 84.7% | Accuracy if the system only answers its most confident 60% of items. It should rise as the share falls. |
| Accuracy at 40% coverage | 91.7% | 91.7% | 95.8% | 85.4% | Accuracy if the system only answers its most confident 40% of items. It should rise as the share falls. |

**Saying "not sure" (calibrated condition):** it abstained on 50.8% of items (more than one answer could not be ruled out). On the items it did answer, it was right 93.2% of the time. The true answer was inside its answer set 92.5% of the time; the target was 90.0%. Average set size: 1.69 answers.

## By task (test half)

| Task | Items | Flip rate: single → shuffled | ECE: shuffled → calibrated | Accuracy: single / shuffled / calibrated / ordinary LLM | Bar |
|---|---|---|---|---|---|
| phishing | 30 | 13.3% → 0.0% | 0.169 → 0.191 | 76.7% / 90.0% / 90.0% / 73.3% | flip PASS, ECE FAIL |
| command_safety | 30 | 36.7% → 20.0% | 0.105 → 0.206 | 80.0% / 76.7% / 76.7% / 83.3% | flip PASS, ECE FAIL |
| routing | 30 | 6.7% → 10.0% | 0.182 → 0.214 | 86.7% / 76.7% / 76.7% / 96.7% | flip FAIL, ECE FAIL |
| urgency | 30 | 6.7% → 20.0% | 0.135 → 0.128 | 70.0% / 76.7% / 76.7% / 63.3% | flip FAIL, ECE PASS |

## Against an ordinary LLM answer

The ordinary answer asks the same model to write JSON with a stated confidence, and that confidence is graded as its probability.

| Measure | assay (shuffled + calibrated) | Ordinary LLM answer | Better |
|---|---|---|---|
| Accuracy | 80.0% | 79.2% | assay |
| Calibration error | 0.119 | 0.129 | assay |
| Brier score | 0.339 | 0.362 | assay |
| Typical latency (p50) | 605 ms | 576 ms | ordinary LLM |
| Slow-end latency (p95) | 642 ms | 715 ms | assay |

The ordinary answer failed to produce a usable reply on 0 items (counted as wrong). Note that assay's latency here includes several model calls per item (one per option ordering), so it can be slower than one ordinary call; the order-proofing is what that time buys.

## Read this before quoting any number

- The tasks are synthetic, small (about 30 test items each) and labelled by the person who built the engine. Gaps of a few points can be noise.
- Calibration was fitted on about 30 dev items per task. That is enough to run, not enough to be precise.
- Accuracy at coverage on small sets moves in big steps: each item is worth several points at 40% coverage.
- The order-flip check compares the top answer with the options shown in forward versus reversed order. It does not test rewording.
- Full per-item predictions are in the receipts JSON next to this file, so every number can be recomputed.
