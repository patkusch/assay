# Hand-over: gemma3 first, gemma3:12b when unsure

Made with `bench/handover.py` from saved receipts, calibrated odds, on the 320 test items both runs share. An item goes to the big model when the small model's confidence is below the cut-off. Time is the small model's call plus the big model's when it was handed up. "Random, same share" hands up the same number of items picked at random (mean of 200 draws).

"Gap to big alone" is the rule's right-answer rate minus the big model's, in points, with a 95% interval from 1,000 resamples of the items: an interval that includes zero means the gap is inside noise. The last two columns look only at the handed-up items: how many the small model had right, and how many the big model got right.

| Rule | Share handed up | Right answers | Gap to big alone | Random, same share | Time per item | Small model on handed-up | Big model on handed-up |
|---|---|---|---|---|---|---|---|
| small model alone | 0.0% | 74.1% | -15.9 (-20.6 to -11.2) | 74.1% | 0.57 s | n/a | n/a |
| hand up when not sure | 52.5% | 88.4% | -1.6 (-3.4 to +0.0) | 82.6% | 1.58 s | 60.1% | 87.5% |
| hand up below 50% | 13.4% | 77.5% | -12.5 (-16.6 to -8.4) | 76.3% | 0.84 s | 62.8% | 88.4% |
| hand up below 60% | 39.1% | 86.6% | -3.4 (-5.9 to -0.9) | 80.2% | 1.31 s | 59.2% | 91.2% |
| hand up below 70% | 49.4% | 89.4% | -0.6 (-2.2 to +0.9) | 81.9% | 1.55 s | 56.3% | 87.3% |
| hand up below 80% | 63.1% | 90.6% | +0.6 (+0.0 to +1.6) | 84.2% | 1.84 s | 62.4% | 88.6% |
| hand up below 90% | 82.5% | 90.6% | +0.6 (+0.0 to +1.6) | 87.3% | 2.15 s | 68.9% | 89.0% |
| hand up below 95% | 88.1% | 90.3% | +0.3 (+0.0 to +0.9) | 88.1% | 2.24 s | 70.6% | 89.0% |
| hand up below 99% | 93.8% | 90.0% | +0.0 (+0.0 to +0.0) | 89.0% | 2.36 s | 72.3% | 89.3% |
| big model alone | 100.0% | 90.0% | +0.0 (+0.0 to +0.0) | 90.0% | 2.50 s | 74.1% | 90.0% |

## Per task: right answers (share handed up)

| Rule | command_safety | phishing | routing | urgency |
|---|---|---|---|---|
| small model alone | 75.0% (0.0%) | 82.5% (0.0%) | 60.0% (0.0%) | 78.8% (0.0%) |
| hand up when not sure | 77.5% (51.2%) | 92.5% (46.2%) | 92.5% (81.2%) | 91.2% (31.2%) |
| hand up below 50% | 73.8% (11.2%) | 82.5% (0.0%) | 66.2% (23.8%) | 87.5% (18.8%) |
| hand up below 60% | 77.5% (46.2%) | 92.5% (21.2%) | 80.0% (43.8%) | 96.2% (45.0%) |
| hand up below 70% | 76.2% (50.0%) | 92.5% (28.7%) | 92.5% (73.8%) | 96.2% (45.0%) |
| hand up below 80% | 80.0% (60.0%) | 92.5% (50.0%) | 92.5% (95.0%) | 97.5% (47.5%) |
| hand up below 90% | 80.0% (90.0%) | 92.5% (90.0%) | 92.5% (100.0%) | 97.5% (50.0%) |
| hand up below 95% | 80.0% (98.8%) | 92.5% (100.0%) | 92.5% (100.0%) | 96.2% (53.8%) |
| hand up below 99% | 80.0% (100.0%) | 92.5% (100.0%) | 92.5% (100.0%) | 95.0% (75.0%) |
| big model alone | 80.0% (100.0%) | 92.5% (100.0%) | 92.5% (100.0%) | 95.0% (100.0%) |
