# assay scoreboard: gemma3:12b

Run at 2026-09-25T12:33:30+00:00. Backend `ollama`, 3 option orderings, tasks: phishing, command_safety, routing, urgency. Python 3.14.3, assay 0.1.0, Ollama 0.33.3.

Every number below is measured on the **test half** of each task only. The calibrator was fitted on the dev half and never graded on it. The right answers were written by construction, never by a model (see `bench/tasks/README.md`).

> **Quick run:** only the first 80 items of each split were used. Do not quote these numbers.

## Did it clear the bar?

The bar was set in `docs/PLAN.md` before any measuring.

- **PASS.** Shuffling the option order must cut the order-flip rate versus a single ordering.
  Order-flip rate went from 7.8% to 3.1% over 320 test items. By task: lower in 3, higher in 1, unchanged in 0.
- **PASS.** Calibration must cut expected calibration error versus the uncalibrated probabilities.
  Calibration error went from 0.058 to 0.029 over 320 test items (against a single ordering it started at 0.084). By task: lower in 3, higher in 1, unchanged in 0.

**Overall: PASS.** Both parts of the bar were met on this run.

## Scoreboard (all tasks together, test half)

| Measure | Single order | Shuffled | Shuffled + calibrated | Ordinary LLM answer | What it means |
|---|---|---|---|---|---|
| Accuracy | 91.6% | 90.0% | 90.0% | 85.0% | How often the top answer matches the answer written by construction. Higher is better. |
| Calibration error (ECE) | 0.084 | 0.058 | 0.029 | 0.091 | How far stated confidence is from the actual hit rate, on average. 0.10 means about 10 points off. Lower is better. |
| Brier score | 0.164 | 0.169 | 0.162 | 0.254 | Punishes confident wrong answers; 0 is perfect; guessing evenly scores 0.5 on a yes/no question and 0.8 on five options. Lower is better. |
| Order-flip rate | 7.8% | 3.1% | 3.1% | n/a | Share of items whose top answer changes when the options are shown in reverse order. Lower is better. |
| Latency, typical (p50) | 693 ms | 1969 ms | 1969 ms | 1887 ms | Half of items were answered faster than this. |
| Latency, slow end (p95) | 1023 ms | 2132 ms | 2132 ms | 2417 ms | Nineteen in twenty items were answered faster than this. |
| Accuracy at 100% coverage | 91.6% | 90.0% | 90.0% | 85.0% | Accuracy when answering everything (the same as Accuracy above). |
| Accuracy at 80% coverage | 96.9% | 95.3% | 96.1% | 90.6% | Accuracy if the system only answers its most confident 80% of items. It should rise as the share falls. |
| Accuracy at 60% coverage | 96.9% | 97.9% | 97.9% | 90.6% | Accuracy if the system only answers its most confident 60% of items. It should rise as the share falls. |
| Accuracy at 40% coverage | 96.9% | 98.4% | 99.2% | 86.7% | Accuracy if the system only answers its most confident 40% of items. It should rise as the share falls. |

**Saying "not sure" (calibrated condition):** it abstained on 6.6% of items (more than one answer could not be ruled out). On the items it did answer, it was right 93.0% of the time. The true answer was inside its answer set 92.5% of the time; the target was 90.0%. Average set size: 1.07 answers.

## By task (test half)

| Task | Items | Flip rate: single → shuffled | ECE: shuffled → calibrated | Accuracy: single / shuffled / calibrated / ordinary LLM | Bar |
|---|---|---|---|---|---|
| phishing | 80 | 12.5% → 0.0% | 0.036 → 0.036 | 97.5% / 92.5% / 92.5% / 71.2% | flip PASS, ECE FAIL |
| command_safety | 80 | 10.0% → 6.2% | 0.143 → 0.078 | 80.0% / 80.0% / 80.0% / 80.0% | flip PASS, ECE PASS |
| routing | 80 | 1.2% → 3.8% | 0.060 → 0.056 | 95.0% / 92.5% / 92.5% / 96.2% | flip FAIL, ECE PASS |
| urgency | 80 | 7.5% → 2.5% | 0.090 → 0.081 | 93.8% / 95.0% / 95.0% / 92.5% | flip PASS, ECE PASS |

## Against an ordinary LLM answer

The ordinary answer asks the same model to write JSON with a stated confidence, and that confidence is graded as its probability.

| Measure | assay (shuffled + calibrated) | Ordinary LLM answer | Better |
|---|---|---|---|
| Accuracy | 90.0% | 85.0% | assay |
| Calibration error | 0.029 | 0.091 | assay |
| Brier score | 0.162 | 0.254 | assay |
| Typical latency (p50) | 1969 ms | 1887 ms | ordinary LLM |
| Slow-end latency (p95) | 2132 ms | 2417 ms | assay |

The ordinary answer failed to produce a usable reply on 0 items (counted as wrong). Note that assay's latency here includes several model calls per item (one per option ordering), so it can be slower than one ordinary call; the order-proofing is what that time buys.

## Read this before quoting any number

- The tasks are synthetic and labelled by construction, with 80 test items per task. That is small: gaps of a few points can be noise.
- Calibration was fitted on 80 dev items per task. Our calibration study found the error stops improving at about 80 examples per question.
- Accuracy at coverage on small sets moves in big steps: each item is worth several points at 40% coverage.
- The order-flip check compares the top answer with the options shown in forward versus reversed order. It does not test rewording.
- Full per-item predictions are in the receipts JSON next to this file, so every number can be recomputed.
