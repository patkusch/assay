# Choosing settings

What to turn on, and what each choice costs. Every number is from our own runs (see the linked receipts), on four made-up tasks. Your data may behave differently, so measure before you trust it.

## 1. Use the biggest model you can afford

This mattered more than anything else we tried. On the same 320 items, gemma3 12B was 15.9 points more accurate than gemma3 4B (90.0% against 74.1%). Its answers changed 3.1% of the time when the options were reversed, against 10.3%. The cost is time: about two seconds a call with three orderings, against about 0.6 seconds.

Where to look: [bench/receipts/comparisons.md](../bench/receipts/comparisons.md).

## 2. Ask for the option's word, not a letter

`--scoring word` asks the model to reply with the option's own word and reads that word's odds. `--scoring auto` does this whenever the options start with different letters, and falls back to letters when they don't. On the 4B model it was 3.4 points more accurate than letters, and the answer changed with the option order less than half as often.

It did not win everywhere: urgency went down 5.9 points on one run, which is inside noise for that task. Check your own task.

## 3. Let the options rotate

By default assay shows the options in three different orders and averages the results. This cut the share of answers that flipped when the options were reversed from 20.3% to 10.7% on the 4B letter run. It triples the number of model calls. Use `--orders 1` if speed matters more than stable answers.

## 4. Calibrate, and fit each question on its own

Raw odds from a small model are much too confident. Give assay 50 to 100 labelled examples per question and it rescales them. In our study the error stopped improving at about 80 examples. Fit each question separately: sharing one correction across questions did worse, because different questions need opposite corrections. See [CALIBRATION.md](CALIBRATION.md) and [CALIBRATION_STUDY.md](CALIBRATION_STUDY.md).

## 5. Treat "not sure" as an answer

Calibrated, the 4B model said "not sure" on about half the items and was right on 91% of the rest. The 12B model said "not sure" on 7% of items. Send those items to a person or a bigger model.

## 6. Know where a plain answer is better

Asking a small model to write JSON with a confidence is sometimes more accurate. On the 4B model it was 81.7% right against 74.6% (letters) or 78.0% (words), mostly on routing. At 12B that reversed: reading the odds got 90.0% against 85.0%. If you use a small model, run both on your own data.

## A sensible starting point

```bash
python -m assay serve --model gemma3:12b --scoring auto --orders 3 --calibration calib.json --cors
```

Fit `calib.json` first with `python -m assay calibrate` ([CALIBRATION.md](CALIBRATION.md)), then check the result with the benchmark runner (`bench/run.py`) on a few hundred of your own labelled items.
