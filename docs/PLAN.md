# assay: plan

## What we are copying
TypeSafe AI's Jev (launched 2026-09-15) is a model that never writes text. You give it a situation and a
list of questions. It gives back typed answers (a choice, a score, or a yes/no probability) with confidence,
in 70-500 ms, for almost no money. Three question types, questions answered independently.

## What is weak about it (from the research)
- Closed, hosted, waitlisted. No weights, no self-hosting.
- Its own accuracy tests grade it against two other models' answers, and the tests were written by its own team.
- Calibration (do "80% sure" answers come out right 80% of the time?) is claimed, never shown. An outside test found
  poor calibration on a single yes/no question.
- "Cannot hallucinate" only means the answer has the right shape, not that it is right.
- Sensitive to how options are ordered and phrased; long, padded inputs hurt it.

## What the open clones still miss (GitHub survey, 33 repos)
1. No neutral calibration test. Every clone grades itself on its own set.
2. Calibration does not carry over to a new task, and nobody ships a quick per-task fix.
3. Option-order stability is checked almost nowhere.
4. Long, messy input is untested.
5. There is no one-step install: a typed schema in, a typed and calibrated answer out, running on a laptop.

## What assay does
Same three question types as Jev, so requests are portable. Runs on a Mac with a small local model reading
option probabilities in one pass (no text generation). Then it adds the parts nobody ships:

1. **Order-proof answers.** Options are shown in rotated orders and the results averaged. Each answer reports a
   `stability` number: how often the top pick survived reordering.
2. **Calibration you can fit in minutes.** Give it a few dozen labelled examples for your task; it fits temperature
   scaling and a split-conformal threshold. Every run reports Brier score and expected calibration error.
3. **Says "not sure".** When the calibrated answer set has more than one option, the answer is marked `abstain`.
4. **Honest scoreboard.** A benchmark whose labels are written by construction (never taken from another model),
   comparing assay against an ordinary generate-and-parse LLM on accuracy, calibration, latency p50/p95, order-flip
   rate, and accuracy at fixed coverage. Raw receipts are committed.
5. **Zero dependencies.** Pure Python standard library, HTTP server that mimics `POST /v1/systemone`.

## Build order (three agents in parallel, then integrate)
| Module | Owner | Files |
|---|---|---|
| Backends + server + CLI | agent A | `backends/ollama.py`, `server.py`, `cli.py` |
| Calibration + metrics | agent B | `calibrate.py`, `metrics.py` |
| Benchmark harness + labelled tasks | agent C | `bench/` |
| Engine, types, plan, README, live run, push | main | everything else |

## Success bar (set before measuring)
On our own benchmark, with gemma3 4B locally: order-shuffling must cut the order-flip rate versus a single
ordering, and calibration must cut expected calibration error versus raw probabilities. If either fails, we say so
in the README instead of hiding it.

## Result against the bar (2026-09-25, gemma3 4B, 912 test items)
- Shuffling cut the order-flip rate from 20.3% to 10.7%. Met, and outside noise. It helped in 3 of 4 tasks and hurt in urgency.
- Calibration cut expected calibration error from 0.146 to 0.096. Met, and outside noise. It helped in 2 of 4 tasks.
- Not part of the bar, but found: a plain generate-and-parse answer from the same model is 7 points more accurate (81.7% against 74.6%), mostly on routing. The two are level on confidence error.
Details: `bench/receipts/v2-gemma3-4b.md` and `bench/receipts/v2-gemma3-4b-significance.md`.
