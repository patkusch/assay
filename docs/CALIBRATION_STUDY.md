# Calibration study: what to do when you only have a few labelled examples

## The short answer

Use one temperature per task, fitted on that task's own examples. That is what assay already did.
The fancier ideas did not beat it.

Sharing one temperature across tasks was worse. Blending each task's temperature with a shared one
was about the same as the plain version, and sometimes worse.

You need at least 20 labelled examples to get any calibration. You need about 50 before the result stops
jumping around, and about 80 before you can lean on it.

## Why we ran this

The first benchmark used only 30 labelled examples per task. On that run, fitting a temperature
made calibration error better in 1 task out of 4 and worse in 3.

The guess was that 30 examples is too few for each task to find its own temperature. If so,
tasks should borrow strength from each other. We tested that guess. It was wrong for the data we have.

## What was tested

Everything here was run offline on saved results. No model was called.

Each task has a dev half and a test half. Every method learned only from the dev half.
Every score below comes only from the test half, which the method never saw.

The methods:

| Name | What it does |
|---|---|
| raw | Leaves the model's probabilities alone. |
| task | Learns one temperature per task from that task's examples. |
| pooled | Learns one temperature from all the tasks' examples together and uses it for every task. |
| shrunk | Takes the task's own temperature and pulls it toward the pooled one. The more examples the task has, the less it is pulled. The weight on the task's own value is n / (n + 30), where n is its number of examples. |
| bias | Task temperature plus a small nudge on each answer label. A prototype only. |

All five also learn the "not sure" rule (the conformal answer set), aimed at the true answer
being in the set 90% of the time. For raw, that rule works on the untouched probabilities.

Three saved runs were used:

- **Von** and **openJev-verdict**: two open models that give typed answers. Four tasks each, 93 to 141 dev examples per task, 186 to 280 test examples per task.
- **gemma3 4B** (the first run): four tasks, 30 dev and 30 test examples each.

The task answers were written by construction, not by a model. The tasks are synthetic.
Treat the numbers as evidence about method, not as a ranking of models.

"ECE" is calibration error: how far stated confidence is from how often the model is right.
0.10 means about 10 points off on average. Lower is better.
"NLL" is how surprised the model is by the true answer. Lower is better.

## Result 1: with all the dev examples, per-task fitting wins

Average over the four tasks, on the test half. Lower is better for ECE and NLL.

| Run | Method | ECE | NLL |
|---|---|---|---|
| Von (93-141 dev items per task) | raw | 0.107 | 1.014 |
| | task | **0.061** | 0.982 |
| | pooled | 0.104 | 1.013 |
| | shrunk | 0.064 | 0.983 |
| openJev-verdict (same sizes) | raw | 0.145 | 1.243 |
| | task | **0.053** | 1.139 |
| | pooled | 0.115 | 1.228 |
| | shrunk | 0.064 | 1.150 |

What this means: on Von, per-task fitting cut calibration error from about 11 points off to about 6 off.
On openJev-verdict it cut it from about 15 points off to about 5 off.

Pooled barely moved anything on Von and helped only a little on openJev-verdict.

The reason is simple. The tasks need different temperatures. On Von, the best temperature was 0.51 for
phishing (the model was too timid) and 1.91 for command safety (too bold). On openJev-verdict it ranged
from 0.28 to 20. One shared number cannot fit tasks that need opposite corrections.

## Result 2: with few examples, shrinking did not win either

Average test ECE over the four tasks. Each cell is the mean of 20 random draws of that many dev items per task.
The spread across draws is in the study output.

| Run | Dev items per task | raw | task | pooled | shrunk |
|---|---|---|---|---|---|
| Von | 20 | 0.107 | 0.100 | 0.121 | 0.100 |
| | 30 | 0.107 | 0.091 | 0.110 | **0.083** |
| | 50 | 0.107 | **0.074** | 0.110 | 0.077 |
| | 80 | 0.107 | **0.065** | 0.109 | 0.067 |
| openJev-verdict | 20 | 0.145 | **0.083** | 0.126 | 0.109 |
| | 30 | 0.145 | **0.079** | 0.120 | 0.094 |
| | 50 | 0.145 | **0.068** | 0.125 | 0.095 |
| | 80 | 0.145 | **0.062** | 0.125 | 0.080 |

What this means:

- On Von at 20 to 30 examples, shrunk was slightly better than task. At 30 it was 0.083 against 0.091. That is a gap of under one point, and the draws vary by about 1.5 points, so it is not a clear win. Shrunk beat task in 65% of individual draws at 30 examples.
- On openJev-verdict, shrunk was worse than task at every size. The task temperatures are far apart, so pulling them toward each other only does harm.
- Pooled won on a couple of single tasks (Von command safety and routing) but lost on the average.

We also tried different values for the shrinking constant. A small value (10 to 30) was about as good as
plain per-task fitting on Von. On openJev-verdict, the smaller the value the better; zero was best. A large value hurts.
So the exact value does matter, and the safe direction is small.

## Result 3: how many labelled examples do you need

Per-task temperature, average test ECE over the four tasks. The "±" is how much it moves depending on
which examples you happened to label.

| Dev items per task | Von | openJev-verdict |
|---|---|---|
| 20 | 0.100 ± 0.022 | 0.083 ± 0.017 |
| 30 | 0.091 ± 0.016 | 0.079 ± 0.011 |
| 50 | 0.074 ± 0.013 | 0.068 ± 0.013 |
| 80 | 0.065 ± 0.008 | 0.062 ± 0.012 |
| all (93-141) | 0.061 | 0.053 |
| no calibration | 0.107 | 0.145 |

What this means:

- At 20 examples, on Von, per-task fitting was barely better than doing nothing (0.100 against 0.107), and the luck of the draw was bigger than the gain. On openJev-verdict, the tasks were so badly miscalibrated that even 20 examples helped a lot.
- The error keeps falling until about 80 examples, then flattens.
- The luck-of-the-draw spread roughly halves between 20 and 80 examples.

## Result 4: the "not sure" sets

The target was 90% of test answers inside the set.

- With 50 or more dev examples per task, coverage landed between 90% and 91% for every temperature method, on both runs.
- With 20 examples it typically moved by about 3.5 points either way from draw to draw.
- The choice of temperature method made almost no difference to how often the set held the true answer (all within half a point) or how big the sets were.

What this means: temperature changes the confidence numbers but hardly changes which answers make it into the set.
The set needs care in the same place as the temperature does: below about 50 examples, treat 90% as roughly 90%.

Both models gave more than one answer on most items (77% and 93% abstain on average). They are not very accurate on these tasks.
The abstain rate says the model is unsure, which is true here.

## Result 5: the first gemma3 run, with 30 examples

| Method | ECE | NLL |
|---|---|---|
| raw | **0.148** | 1.196 |
| task | 0.185 | 0.654 |
| pooled | 0.191 | 0.640 |
| shrunk | 0.199 | 0.640 |

- All three temperature methods cut NLL a lot (1.20 down to about 0.65) in all four tasks.
- None cut ECE. Raw had the lowest ECE. Per task, ECE improved in 1 of 4 tasks for task and for shrunk, and in 2 of 4 for pooled.
- Pooled and shrunk did not fix it. They landed close to per-task fitting on NLL.

Why we would not read much into the ECE result: the test half had only 30 items per task, spread over 10 confidence bands.
That is too few to tell a gap of 0.04 from noise. NLL uses every item and gave a clear, steady answer.
We do not think the first run showed that calibration hurts. We think it could not tell.

## What did NOT help

- **Pooled temperature.** Worse than per-task on both larger runs. Do not use it as the default.
- **Shrinking toward the pooled temperature.** No better than per-task once a task had about 90 examples, and worse when tasks disagree. Only a hint of gain on one run at 20 to 30 examples.
- **A bigger shrinking constant.** Worse. Small is safer.
- **Per-label nudges (the bias prototype).** Mixed, so it was not added to the library. It gave the best NLL in all three runs (for example, 1.065 against 1.139 on openJev-verdict), the best Brier score, higher accuracy (42.3% to 50.1% on openJev-verdict) and smaller answer sets. But its calibration error was worse than plain per-task fitting on all three runs. The sets also fell short of 90%: 87% at 20 to 30 examples and 89% at 50. The likely cause is that it learns extra dials from the same examples that set the "not sure" threshold, so the threshold is a little too optimistic. It is worth trying again with the examples split into two groups. That was not tested.

## Recommendation

1. **Default: one temperature per task**, fitted with `TemperatureCalibrator`. This is unchanged.
2. **Minimum: 20 examples** to fit at all (the library already refuses fewer). **Aim for 50.** At 50 the result stops jumping around. **80 is comfortable.** Beyond that, gains are small.
3. **Below 50 examples**, do not judge success by ECE alone. It is noisy at that size. Look at NLL or the Brier score, and expect the "90%" set to be somewhere between 87% and 93%.
4. **`ShrunkTemperatureCalibrator` is available but not the default.** Consider it only when you have 20 to 40 examples per task and several related tasks. Use `pooled_temperature` for the shared value and keep the constant small (10 to 30). The evidence for it is thin.
5. **`FixedTemperatureCalibrator`** applies a temperature you hand it and still learns the "not sure" rule. Use it only if you already have a good temperature from somewhere else.

## Limits of this study

- Two of the three runs come from open typed-answer models, not from a general language model. The third is gemma3 4B with very little data. Results on other models may differ.
- The tasks are synthetic and there are four of them per run.
- The random draws come from the same dev half each time, so they are not independent of each other. The spreads are a guide, not a guarantee.
- The shrinking constant of 30 was chosen before looking. The sweep afterwards showed smaller is safer.

## How to reproduce

```
python bench/calib_study.py bench/receipts/v2-von.json bench/receipts/v2-verdict.json \
    bench/receipts/gemma3-4b.json --out bench/receipts/calib_study.md
```

It reads saved results only and calls no model. The full tables (per task, every size, coverage, set size,
abstain rate) are in `bench/receipts/calib_study.md`.
