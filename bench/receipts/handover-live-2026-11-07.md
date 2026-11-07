# Hand-over: one live call

Run on 7 November 2026 on the Apple M5 laptop, with gemma3 4B first and gemma3 12B taking anything under 90% confidence. No calibration file was used, so the odds are the raw model odds. Output of `--format pretty`, unedited:

```
$ python -m assay decide --model gemma3 --handover gemma3:12b --handover-below 0.9 --format pretty \
    --state "I was charged twice this month and nobody answers my emails." \
    --question "choice:Which team should get this?:billing|technical support|sales" \
    --question "noul:Is the customer angry?" --question "score:How urgent is this?:5"

answered by ollama:gemma3, then ollama:gemma3:12b when unsure in 9835 ms

q1: billing
  Which team should get this?
 * billing            ████████████████████████  100.0%
   technical support  █░░░░░░░░░░░░░░░░░░░░░░░    0.0%
   sales              █░░░░░░░░░░░░░░░░░░░░░░░    0.0%
  confidence 100%, stable across option orders 100%, not calibrated, answered by ollama:gemma3

q2: 100% yes
  Is the customer angry?
 * yes  ████████████████████████  100.0%
   no   █░░░░░░░░░░░░░░░░░░░░░░░    0.0%
  confidence 100%, stable across option orders 100%, not calibrated, answered by ollama:gemma3

q3: 4.31
  How urgent is this?
   1  █░░░░░░░░░░░░░░░░░░░░░░░    0.0%
   2  █░░░░░░░░░░░░░░░░░░░░░░░    0.0%
   3  █░░░░░░░░░░░░░░░░░░░░░░░    0.0%
 * 4  ████████████████░░░░░░░░     69%
   5  ████████░░░░░░░░░░░░░░░░     31%
  confidence 69%, stable across option orders 67%, not calibrated, answered by ollama:gemma3:12b
```

What it shows: the plumbing works end to end. Two questions stayed with the 4B and the urgency question, where it was unsure, went to the 12B. The 9.8 seconds includes loading the 12B into memory for the first time.

What it also shows: without a calibration file the 4B's raw odds say 100% on the first two questions. Raw odds from a small model are far too confident (confidence error 0.265 before calibration on our benchmark), so uncalibrated, the hand-over will rarely fire. Fit a calibration for the task first and pass it with `--calibration`; the measured results in handover-4b-12b.md all use calibrated odds.
