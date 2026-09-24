# assay

Ask a small local model a question and get back a **typed answer with a probability you can check**, not a paragraph.

assay is an open, local take on the idea behind TypeSafe AI's Jev (launched 15 September 2026): a model that never chats. You hand it a situation and some questions. It hands back a choice, a score or a yes/no probability, in about half a second, on a laptop, for no money.

Jev is closed, hosted and behind a waitlist, and its accuracy claims are graded by two other models. assay is the version you can run, read and test yourself. Its main job is to be honest about how much to trust each answer.

- Pure Python standard library. Nothing to install.
- Same three question types as Jev, so a request written for one can be tried on the other.
- Runs on a small model through [Ollama](https://ollama.com). No text is generated: it reads the model's odds for each option in one step.

## Try it

```bash
ollama pull gemma3
python -m assay decide --backend ollama --model gemma3 \
  --state "I was charged twice this month and nobody answers my emails." \
  --question "choice:Which team should get this?:billing|technical support|sales"
```

```bash
python -m assay serve --model gemma3 --port 8787   # POST /v1/systemone, shaped like Jev's
```

In Python:

```python
from assay import Question, Request, decide
from assay.backends.ollama import OllamaBackend

request = Request(
    state="rm -rf ~/projects/old",
    questions={"risk": Question("choice", "How dangerous is this command?", options=["safe", "risky", "destructive"])},
)
answer = decide(OllamaBackend("gemma3"), request).answers["risk"]
print(answer.value, answer.confidence, answer.stability, answer.abstain)
```

## What is different from just asking a model

1. **Order-proof.** Models lean towards whichever option they see first. assay shows the options in rotated orders and averages the results. Each answer carries a `stability` number: how often the top pick survived reordering.
2. **Calibration you can fit.** Raw model odds are far too confident. Give assay a few dozen labelled examples of your task and it rescales the odds so "80% sure" is closer to right 80% of the time (`assay.calibrate.TemperatureCalibrator`).
3. **It can say "not sure".** The calibrator also works out which answers cannot be ruled out. If more than one remains, the answer is marked `abstain`.
4. **A scoreboard that reports failures.** `bench/` holds four small tasks whose right answers were written by construction, never taken from another model. Every run writes raw receipts you can recompute.

## What we measured

Model: gemma3 4B on an Apple M5 laptop. Four tasks (phishing, command safety, support routing, ticket urgency), 30 dev and 30 test items each. Calibration was fitted on dev and every number below is from test. Full table and per-item receipts: [bench/receipts/gemma3-4b.md](bench/receipts/gemma3-4b.md).

| | One ordering | Shuffled | Shuffled + calibrated | Ordinary LLM answer |
|---|---|---|---|---|
| Accuracy | 78.3% | 80.0% | 80.0% | 79.2% |
| Calibration error (lower is better) | 0.202 | 0.135 | 0.119 | 0.129 |
| Answer flips when options are reversed | 15.8% | 12.5% | 12.5% | n/a |
| Typical time | 202 ms | 605 ms | 605 ms | 576 ms |

"Ordinary LLM answer" means asking the same model to write JSON with a stated confidence.

What that says, plainly:

- **Reading the odds beats asking the model to state its confidence, but not by much.** Calibration error 0.119 against 0.129 on 120 test items is inside the noise.
- **The pre-set bar passed only on the totals.** Shuffling cut answer flips overall (15.8% to 12.5%) but helped in 2 tasks and hurt in 2. Calibration cut error overall but helped in 1 task and hurt in 3. With 30 test items a task, that is what noise looks like. We are not claiming either fix works until it is shown on bigger sets.
- **Abstaining is the clearest win.** Calibrated, it declined 50.8% of items and was right on 93.2% of the ones it answered. Answering only its most confident 40% of items, it was right 95.8% of the time.
- **It is slower than one call.** Three orderings mean three model calls, about 600 ms against Jev's claimed 70 to 500 ms. One ordering is 202 ms.

## Bigger benchmark (v2)

The 30-item tasks above were too small to trust. `bench/tasks_v2/` has 1,370 items (about 900 in the test half), still labelled by construction. Every item was then labelled blind by an independent reader who saw only the text and the written rules. Items they disagreed with, or called ambiguous, were dropped, never relabelled (203 of 1,573; details in [bench/audit/AUDIT.md](bench/audit/AUDIT.md)).

One known skew: the middle urgency levels were the fuzziest, so level 3 kept only 22 items. Also, the readers are models, so they may share blind spots with whoever wrote the items.

v2 results for gemma3 4B and 12B, and a side-by-side against the open clones [von](https://github.com/wfzyx/von) and [openJev-verdict-2.0](https://github.com/Heman10x-NGU/openJev-verdict-2.0) (adapters in `bench/adapters/`), were still running when this was written. The numbers in the table above are from the small v1 set only.

## Limits

- The tasks are small, made up, and labelled by the author. Treat gaps of a few points as noise.
- Calibration from about 30 examples is enough to run and not enough to be precise.
- The flip check reverses the option order. It does not test rewording, long inputs or padded input.
- Only gemma3 4B has been measured. Larger models and the Ollama-free path are untested.
- More than 36 options is not supported by the Ollama backend (Jev allows 255).
- A probability is not a guarantee. A confident answer can still be wrong.

## Layout

| Path | What it is |
|---|---|
| `src/assay/engine.py` | Rotates the options, averages the odds, applies calibration, returns a typed answer. |
| `src/assay/calibrate.py`, `metrics.py` | Fits the rescaling and the "not sure" threshold; measures calibration error and Brier score. |
| `src/assay/backends/` | Ollama backend and simple test backends. |
| `src/assay/server.py`, `cli.py` | `POST /v1/systemone` and the command line. |
| `bench/` | Tasks, runner, scoreboard, receipts. |
| `docs/PLAN.md` | Why this exists, what the research found, and the bar we set before measuring. |

Run the tests: `PYTHONPATH=src python3 -m unittest discover -s tests`

## Next

Bigger labelled sets (hundreds of items a task), gemma3 12B and a small encoder backend for comparison, calibration pooled across similar tasks, a long-input path, and running the same tasks against other open Jev alternatives.

MIT licence.
