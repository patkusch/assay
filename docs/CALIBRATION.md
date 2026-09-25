# Calibration

## What it does

A small model sounds sure of itself when it should not be.
Calibration fixes that.
You give assay examples where you already know the right answer.
assay checks how often the model was right when it said "90% sure".
It then turns the model's confidence down, or up, to match.

It also learns when to say "not sure".
If two answers are still possible, the answer is marked `abstain`.

## Why it is tied to one model

The fix is measured on one model.
A different model needs its own fix.
The calibration file remembers which model made it.
If you use it with another model, assay prints a warning and carries on.
Do not ignore that warning.

## How many examples

- **Under 20 for a question:** assay refuses. There is too little to learn from.
- **20 to 39:** it works, but the scores are measured on the same examples it learned from. They look better than they will in real use.
- **40 or more:** assay hides half, learns from the other half, and tests on the hidden half. Those scores are honest.
- **More is better.** Aim for a few hundred if you can.

The examples must be true. If your labels are wrong, the calibration will be wrong.

## When to trust it

- Trust it for the same kind of text you calibrated on.
- Do not trust it for a different task, a different model, or very different wording.
- Read the "after" numbers as a guide, not a promise.
- A calibrated 80% still means one answer in five may be wrong.

## The commands

**1. Write your questions** in a request file. Only the `questions` part is used. See `examples/support_ticket.json`.

**2. Write your labelled examples**, one per line, in a `.jsonl` file:

```
{"question": "team", "state": "I was charged twice this month.", "truth": "billing"}
```

`question` is the id from your request file. `truth` is one of that question's answers. For a yes/no question use `"yes"` or `"no"`. For a score use the level, like `"3"`.
There is a format example in `examples/labelled_example.jsonl`. It has fewer than 20 rows per question, so it shows the shape but assay will refuse to fit it. Add more rows of your own.

**3. Fit it:**

```bash
python -m assay calibrate --backend ollama --model gemma3 \
  --request questions.json --labelled labelled.jsonl --out calib.json
```

Optional: `--orders 3` sets how many option orders are averaged. `--alpha 0.1` sets how often you accept the true answer falling outside the "not sure" set (0.1 means about one time in ten).

assay prints, for each question, the calibration error before and after (lower is better) and how often the true answer was inside the "not sure" set. Then it saves the file.

**4. Use it:**

```bash
python -m assay decide --backend ollama --model gemma3 --calibration calib.json --request my_request.json
python -m assay serve --model gemma3 --calibration calib.json
```

Answers that used it show `"calibrated": true`. Questions with no calibration in the file are answered as before.

To set a minimum confidence, add `--confidence-floor 0.7`. Any answer under 70% is marked `abstain`.

**5. Check what the server loaded:**

```bash
curl http://127.0.0.1:8787/v1/calibration
```

It lists each question, how many examples were used, and the scores. If nothing is loaded it answers 404.
