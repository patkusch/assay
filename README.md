# assay

[![tests](https://github.com/patkusch/assay/actions/workflows/ci.yml/badge.svg)](https://github.com/patkusch/assay/actions/workflows/ci.yml)

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
4. **A scoreboard that reports failures.** `bench/` holds four tasks (1,370 items) whose right answers were written by construction, never taken from another model, and checked by a blind reader. Every run writes raw receipts you can recompute.

## See it

`docs/demo/index.html` is a single page you can open in any browser. It replays the real benchmark receipts: each system's odds for every option on every test item, a chart of whether its confidence can be trusted, a chart of what happens if you only keep its most confident answers, and how often the answer changes when the options are reversed. A last panel talks to your own running server.

```bash
make demo          # rebuild the page from bench/receipts
open docs/demo/index.html
```

Nothing on the page is invented and no model needs to be running to view it. The live panel needs `python -m assay serve --model gemma3 --cors`.

## What we measured

Model: gemma3 4B on an Apple M5 laptop. Four tasks (phishing, command safety, support routing, ticket urgency), 1,370 items, labelled by construction and then checked blind (details in [bench/audit/AUDIT.md](bench/audit/AUDIT.md)). Calibration was fitted on a separate third of the items, and every number below is from the other 912 test items. Full tables and per-item receipts: [bench/receipts/v2-gemma3-4b.md](bench/receipts/v2-gemma3-4b.md).

| | One ordering | Shuffled | Shuffled + calibrated | Plain answer |
|---|---|---|---|---|
| Right answers | 72.4% | 74.6% | 74.6% | 81.7% |
| Confidence error (lower is better) | 0.265 | 0.146 | 0.096 | 0.110 |
| Answer flips when options are reversed | 20.3% | 10.7% | 10.7% | n/a |
| Typical time | 205 ms | 598 ms | 598 ms | 639 ms |

"Plain answer" means asking the same model to write JSON with a stated confidence, the usual way to do this.

What that says, plainly:

- **Shuffling the options works.** Answers that flipped when the options were reversed fell from 20.3% to 10.7%, and that gap is well outside noise. It helped in 3 of 4 tasks (command safety fell from 41.8% to 18.6%) and made urgency worse (9.7% to 18.3%).
- **Calibration works overall, not everywhere.** Confidence error fell from 0.146 to 0.096, also outside noise. Per task it helped in 2 of 4 and did not help in command safety or urgency.
- **The plain answer is more accurate.** 81.7% against 74.6%, and that gap is real. It is biggest in routing, where the plain answer got 95.8% right and reading the option odds got 58.4%. With five options, the first-letter odds of a small model are a weak signal. assay is level or ahead on phishing and urgency.
- **On confidence error, assay and the plain answer are level.** 0.096 against 0.110 is inside the noise.
- **Abstaining is the clearest win.** Calibrated, it said "not sure" on 55.5% of items and was right on 91.1% of the ones it answered. Keeping only its most confident 40% of items, it was right 93.2% of the time, against 85.8% for the plain answer.
- **It is not faster than one plain call.** Three orderings mean three model calls: about 600 ms, the same as the plain answer. One ordering is 205 ms.

Which gaps are outside noise, from 2,000 resamples of the test items: [bench/receipts/v2-gemma3-4b-significance.md](bench/receipts/v2-gemma3-4b-significance.md).

### Beside the open clones

The same 912 items, with [von](https://github.com/wfzyx/von) and [openJev-verdict-2.0](https://github.com/Heman10x-NGU/openJev-verdict-2.0) run as shipped inside assay's scoring loop ([bench/adapters/](bench/adapters/)), order-shuffled:

| | assay + gemma3 4B | von 1.2 | openJev-verdict-2.0 |
|---|---|---|---|
| Right answers | 74.6% | 59.5% | 42.5% |
| Confidence error, shuffled | 0.146 | 0.043 | 0.113 |
| Confidence error, calibrated | 0.096 | 0.029 | 0.048 |
| Answer flips when options are reversed | 10.7% | 0.0% | 3.8% |
| Typical time | 598 ms | 125 ms | 136 ms |

assay with gemma3 is the most accurate on these tasks. Both clones are much faster, and von is far better calibrated and never changes with option order. They are small special-purpose models (395 and 151 million parameters) that were not tuned for these tasks, and their own benchmarks may show different numbers. So assay's value is not raw accuracy. It is the tooling around any model: order-proofing, a calibration you can fit and check, "not sure" answers, and a scoreboard that reports failures.

### Earlier, smaller run

The first run used 30 test items per task and could not tell any of this apart from noise. Its receipts stay in `bench/receipts/gemma3-4b.*` so the change is visible.

## Limits

- The tasks are synthetic and labelled by construction. Blind readers checked every label, but the readers are models and may share blind spots with whoever wrote the items. The middle urgency levels lost the most items in that check, so level 3 is thin (22 items).
- Calibration was fitted on 93 to 141 items per task. The study in [docs/CALIBRATION_STUDY.md](docs/CALIBRATION_STUDY.md) found about 50 to 100 is enough.
- The flip check reverses the option order. It does not test rewording or long inputs. The long-input wrapper ([docs/LONG_INPUT.md](docs/LONG_INPUT.md)) is only tested on mock backends so far.
- Only gemma3 4B is measured on the full set. A 12B run is in progress and will be added.
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

The gemma3 12B run, a measured test of the long-input wrapper, a rewording test (the flip check only reverses the options), a small encoder backend to close the speed gap, and a fix for routing, where reading the option odds falls well behind a plain answer.

MIT licence.
