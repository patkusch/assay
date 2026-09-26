# assay scoreboard: gemma3 (word scoring)

Run at 2026-09-25T13:50:32+00:00. Backend `ollama`, 3 option orderings, tasks: phishing, command_safety, routing, urgency. Python 3.14.3, assay 0.1.0, Ollama 0.33.3.

Every number below is measured on the **test half** of each task only. The calibrator was fitted on the dev half and never graded on it. The right answers were written by construction, never by a model (see `bench/tasks/README.md`).

## Did it clear the bar?

The bar was set in `docs/PLAN.md` before any measuring.

- **PASS.** Shuffling the option order must cut the order-flip rate versus a single ordering.
  Order-flip rate went from 6.4% to 4.3% over 912 test items. By task: lower in 4, higher in 0, unchanged in 0.
- **PASS.** Calibration must cut expected calibration error versus the uncalibrated probabilities.
  Calibration error went from 0.189 to 0.062 over 912 test items (against a single ordering it started at 0.199). By task: lower in 4, higher in 0, unchanged in 0.

**Overall: PASS.** Both parts of the bar were met on this run.

## Scoreboard (all tasks together, test half)

| Measure | Single order | Shuffled | Shuffled + calibrated | What it means |
|---|---|---|---|---|
| Accuracy | 78.9% | 78.0% | 78.0% | How often the top answer matches the answer written by construction. Higher is better. |
| Calibration error (ECE) | 0.199 | 0.189 | 0.062 | How far stated confidence is from the actual hit rate, on average. 0.10 means about 10 points off. Lower is better. |
| Brier score | 0.410 | 0.402 | 0.325 | Punishes confident wrong answers; 0 is perfect; guessing evenly scores 0.5 on a yes/no question and 0.8 on five options. Lower is better. |
| Order-flip rate | 6.4% | 4.3% | 4.3% | Share of items whose top answer changes when the options are shown in reverse order. Lower is better. |
| Latency, typical (p50) | 209 ms | 572 ms | 572 ms | Half of items were answered faster than this. |
| Latency, slow end (p95) | 407 ms | 640 ms | 640 ms | Nineteen in twenty items were answered faster than this. |
| Accuracy at 100% coverage | 78.9% | 78.0% | 78.0% | Accuracy when answering everything (the same as Accuracy above). |
| Accuracy at 80% coverage | 86.4% | 84.8% | 85.6% | Accuracy if the system only answers its most confident 80% of items. It should rise as the share falls. |
| Accuracy at 60% coverage | 86.3% | 86.1% | 92.2% | Accuracy if the system only answers its most confident 60% of items. It should rise as the share falls. |
| Accuracy at 40% coverage | 91.8% | 87.9% | 94.0% | Accuracy if the system only answers its most confident 40% of items. It should rise as the share falls. |

**Saying "not sure" (calibrated condition):** it abstained on 44.8% of items (more than one answer could not be ruled out). On the items it did answer, it was right 93.4% of the time. The true answer was inside its answer set 90.8% of the time; the target was 90.0%. Average set size: 1.55 answers.

## By task (test half)

| Task | Items | Flip rate: single → shuffled | ECE: shuffled → calibrated | Accuracy: single / shuffled / calibrated / ordinary LLM | Bar |
|---|---|---|---|---|---|
| phishing | 232 | 0.9% → 0.0% | 0.074 → 0.070 | 92.2% / 92.2% / 92.2% / n/a | flip PASS, ECE PASS |
| command_safety | 280 | 2.9% → 1.8% | 0.199 → 0.024 | 78.6% / 77.9% / 77.9% / n/a | flip PASS, ECE PASS |
| routing | 214 | 6.1% → 3.3% | 0.313 → 0.154 | 68.2% / 65.4% / 65.4% / n/a | flip PASS, ECE PASS |
| urgency | 186 | 18.8% → 14.5% | 0.191 → 0.108 | 75.3% / 74.7% / 74.7% / n/a | flip PASS, ECE PASS |

## Against an ordinary LLM answer

Not run in this receipts file (it needs a live Ollama model).

## Read this before quoting any number

- The tasks are synthetic and labelled by construction, with 186 to 280 test items per task. Gaps of a couple of points are still within noise for a single task; `bench/significance.py` gives intervals for the pooled gaps.
- Calibration was fitted on 93 to 141 dev items per task. Our calibration study found the error stops improving at about 80 examples per question.
- Accuracy at coverage moves in steps: each item is worth a fraction of a point, and more at 40% coverage.
- The order-flip check compares the top answer with the options shown in forward versus reversed order. It does not test rewording.
- Full per-item predictions are in the receipts JSON next to this file, so every number can be recomputed.
