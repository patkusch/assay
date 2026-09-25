# assay scoreboard: verdict

Run at 2026-09-24T23:11:01+00:00. Backend `verdict`, 3 option orderings, tasks: phishing, command_safety, routing, urgency. Python 3.14.3, assay 0.1.0.

Every number below is measured on the **test half** of each task only. The calibrator was fitted on the dev half and never graded on it. The right answers were written by construction, never by a model (see `bench/tasks/README.md`).

## Did it clear the bar?

The bar was set in `docs/PLAN.md` before any measuring.

- **PASS.** Shuffling the option order must cut the order-flip rate versus a single ordering.
  Order-flip rate went from 6.6% to 3.8% over 912 test items. By task: lower in 1, higher in 1, unchanged in 2.
- **PASS.** Calibration must cut expected calibration error versus the uncalibrated probabilities.
  Calibration error went from 0.113 to 0.048 over 912 test items (against a single ordering it started at 0.123). By task: lower in 3, higher in 1, unchanged in 0.

**Overall: PASS.** Both parts of the bar were met on this run.

## Scoreboard (all tasks together, test half)

| Measure | Single order | Shuffled | Shuffled + calibrated | What it means |
|---|---|---|---|---|
| Accuracy | 43.0% | 42.5% | 42.5% | How often the top answer matches the answer written by construction. Higher is better. |
| Calibration error (ECE) | 0.123 | 0.113 | 0.048 | How far stated confidence is from the actual hit rate, on average. 0.10 means about 10 points off. Lower is better. |
| Brier score | 0.675 | 0.681 | 0.627 | Punishes confident wrong answers; 0 is perfect; guessing evenly scores 0.5 on a yes/no question and 0.8 on five options. Lower is better. |
| Order-flip rate | 6.6% | 3.8% | 3.8% | Share of items whose top answer changes when the options are shown in reverse order. Lower is better. |
| Latency, typical (p50) | 46 ms | 136 ms | 136 ms | Half of items were answered faster than this. |
| Latency, slow end (p95) | 54 ms | 152 ms | 152 ms | Nineteen in twenty items were answered faster than this. |
| Accuracy at 100% coverage | 43.0% | 42.5% | 42.5% | Accuracy when answering everything (the same as Accuracy above). |
| Accuracy at 80% coverage | 41.5% | 41.6% | 47.4% | Accuracy if the system only answers its most confident 80% of items. It should rise as the share falls. |
| Accuracy at 60% coverage | 46.5% | 45.6% | 54.6% | Accuracy if the system only answers its most confident 60% of items. It should rise as the share falls. |
| Accuracy at 40% coverage | 52.3% | 53.2% | 63.6% | Accuracy if the system only answers its most confident 40% of items. It should rise as the share falls. |

**Saying "not sure" (calibrated condition):** it abstained on 90.6% of items (more than one answer could not be ruled out). On the items it did answer, it was right 77.9% of the time. The true answer was inside its answer set 90.1% of the time; the target was 90.0%. Average set size: 2.87 answers.

## By task (test half)

| Task | Items | Flip rate: single → shuffled | ECE: shuffled → calibrated | Accuracy: single / shuffled / calibrated / ordinary LLM | Bar |
|---|---|---|---|---|---|
| phishing | 232 | 0.0% → 0.0% | 0.034 → 0.042 | 56.0% / 56.0% / 56.0% / n/a | flip n/a, ECE FAIL |
| command_safety | 280 | 0.7% → 5.0% | 0.093 → 0.004 | 33.6% / 34.3% / 34.3% / n/a | flip FAIL, ECE PASS |
| routing | 214 | 27.1% → 9.8% | 0.243 → 0.156 | 56.1% / 53.3% / 53.3% / n/a | flip PASS, ECE PASS |
| urgency | 186 | 0.0% → 0.0% | 0.209 → 0.010 | 25.8% / 25.8% / 25.8% / n/a | flip n/a, ECE PASS |

## Against an ordinary LLM answer

Not run in this receipts file (it needs a live Ollama model).

## Read this before quoting any number

- The tasks are synthetic and labelled by construction, with 186 to 280 test items per task. Gaps of a couple of points are still within noise for a single task; `bench/significance.py` gives intervals for the pooled gaps.
- Calibration was fitted on 93 to 141 dev items per task. Our calibration study found the error stops improving at about 80 examples per question.
- Accuracy at coverage moves in steps: each item is worth a fraction of a point, and more at 40% coverage.
- The order-flip check compares the top answer with the options shown in forward versus reversed order. It does not test rewording.
- Full per-item predictions are in the receipts JSON next to this file, so every number can be recomputed.
