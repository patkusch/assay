# assay scoreboard: von

Run at 2026-09-24T16:11:35+00:00. Backend `von`, 3 option orderings, tasks: phishing, command_safety, routing, urgency. Python 3.14.3, assay 0.1.0.

Every number below is measured on the **test half** of each task only. The calibrator was fitted on the dev half and never graded on it. The right answers were written by construction, never by a model (see `bench/tasks/README.md`).

## Did it clear the bar?

The bar was set in `docs/PLAN.md` before any measuring.

- **NOT APPLICABLE / NOT EVALUATED.** Shuffling the option order must cut the order-flip rate versus a single ordering.
  Order-flip rate went from 0.0% to 0.0% over 912 test items. By task: lower in 0, higher in 0, unchanged in 4. The single ordering never flipped, so there was nothing to cut: not applicable.
- **PASS.** Calibration must cut expected calibration error versus the uncalibrated probabilities.
  Calibration error went from 0.043 to 0.029 over 912 test items (against a single ordering it started at 0.043). By task: lower in 4, higher in 0, unchanged in 0.

**Overall: PASS (part not applicable).** Every part of the bar that applies was met on this run.

## Scoreboard (all tasks together, test half)

| Measure | Single order | Shuffled | Shuffled + calibrated | What it means |
|---|---|---|---|---|
| Accuracy | 59.5% | 59.5% | 59.5% | How often the top answer matches the answer written by construction. Higher is better. |
| Calibration error (ECE) | 0.043 | 0.043 | 0.029 | How far stated confidence is from the actual hit rate, on average. 0.10 means about 10 points off. Lower is better. |
| Brier score | 0.545 | 0.545 | 0.526 | Punishes confident wrong answers; 0 is perfect; guessing evenly scores 0.5 on a yes/no question and 0.8 on five options. Lower is better. |
| Order-flip rate | 0.0% | 0.0% | 0.0% | Share of items whose top answer changes when the options are shown in reverse order. Lower is better. |
| Latency, typical (p50) | 46 ms | 125 ms | 125 ms | Half of items were answered faster than this. |
| Latency, slow end (p95) | 67 ms | 176 ms | 176 ms | Nineteen in twenty items were answered faster than this. |
| Accuracy at 100% coverage | 59.5% | 59.5% | 59.5% | Accuracy when answering everything (the same as Accuracy above). |
| Accuracy at 80% coverage | 63.6% | 63.6% | 65.1% | Accuracy if the system only answers its most confident 80% of items. It should rise as the share falls. |
| Accuracy at 60% coverage | 70.6% | 70.6% | 71.5% | Accuracy if the system only answers its most confident 60% of items. It should rise as the share falls. |
| Accuracy at 40% coverage | 79.2% | 79.2% | 80.5% | Accuracy if the system only answers its most confident 40% of items. It should rise as the share falls. |

**Saying "not sure" (calibrated condition):** it abstained on 78.0% of items (more than one answer could not be ruled out). On the items it did answer, it was right 88.1% of the time. The true answer was inside its answer set 90.8% of the time; the target was 90.0%. Average set size: 2.46 answers.

## By task (test half)

| Task | Items | Flip rate: single → shuffled | ECE: shuffled → calibrated | Accuracy: single / shuffled / calibrated / ordinary LLM | Bar |
|---|---|---|---|---|---|
| phishing | 232 | 0.0% → 0.0% | 0.148 → 0.051 | 84.9% / 84.9% / 84.9% / n/a | flip n/a, ECE PASS |
| command_safety | 280 | 0.0% → 0.0% | 0.065 → 0.046 | 51.4% / 51.4% / 51.4% / n/a | flip n/a, ECE PASS |
| routing | 214 | 0.0% → 0.0% | 0.122 → 0.105 | 55.6% / 55.6% / 55.6% / n/a | flip n/a, ECE PASS |
| urgency | 186 | 0.0% → 0.0% | 0.092 → 0.042 | 44.6% / 44.6% / 44.6% / n/a | flip n/a, ECE PASS |

## Against an ordinary LLM answer

Not run in this receipts file (it needs a live Ollama model).

## Read this before quoting any number

- The tasks are synthetic and labelled by construction, with 186 to 280 test items per task. Gaps of a couple of points are still within noise for a single task; `bench/significance.py` gives intervals for the pooled gaps.
- Calibration was fitted on 93 to 141 dev items per task. Our calibration study found the error stops improving at about 80 examples per question.
- Accuracy at coverage moves in steps: each item is worth a fraction of a point, and more at 40% coverage.
- The order-flip check compares the top answer with the options shown in forward versus reversed order. It does not test rewording.
- Full per-item predictions are in the receipts JSON next to this file, so every number can be recomputed.
