# Hand-over: gemma3 (word scoring) first, gemma3:12b when unsure

Made with `bench/handover.py` from saved receipts, calibrated odds, on the 320 test items both runs share. An item goes to the big model when the small model's confidence is below the cut-off. Time is the small model's call plus the big model's when it was handed up. "Random, same share" hands up the same number of items picked at random (mean of 200 draws).

"Gap to big alone" is the rule's right-answer rate minus the big model's, in points, with a 95% interval from 1,000 resamples of the items: an interval that includes zero means the gap is inside noise. The last two columns look only at the handed-up items: how many the small model had right, and how many the big model got right.

| Rule | Share handed up | Right answers | Gap to big alone | Random, same share | Time per item | Small model on handed-up | Big model on handed-up |
|---|---|---|---|---|---|---|---|
| small model alone | 0.0% | 76.6% | -13.4 (-17.8 to -9.1) | 76.6% | 0.55 s | n/a | n/a |
| hand up when not sure | 44.7% | 89.1% | -0.9 (-2.5 to +0.3) | 82.7% | 1.46 s | 58.7% | 86.7% |
| hand up below 50% | 7.5% | 80.0% | -10.0 (-13.8 to -6.2) | 77.5% | 0.70 s | 41.7% | 87.5% |
| hand up below 60% | 14.1% | 81.9% | -8.1 (-11.6 to -4.7) | 78.4% | 0.82 s | 44.4% | 82.2% |
| hand up below 70% | 22.5% | 84.7% | -5.3 (-8.4 to -2.5) | 79.6% | 1.03 s | 50.0% | 86.1% |
| hand up below 80% | 41.2% | 88.4% | -1.6 (-3.8 to +0.3) | 82.2% | 1.39 s | 56.8% | 85.6% |
| hand up below 90% | 76.2% | 90.3% | +0.3 (+0.0 to +0.9) | 86.8% | 2.04 s | 70.5% | 88.5% |
| hand up below 95% | 96.2% | 90.0% | +0.0 (+0.0 to +0.0) | 89.5% | 2.39 s | 75.6% | 89.6% |
| hand up below 99% | 100.0% | 90.0% | +0.0 (+0.0 to +0.0) | 90.0% | 2.48 s | 76.6% | 90.0% |
| big model alone | 100.0% | 90.0% | +0.0 (+0.0 to +0.0) | 90.0% | 2.48 s | 76.6% | 90.0% |

## Per task: right answers (share handed up)

| Rule | command_safety | phishing | routing | urgency |
|---|---|---|---|---|
| small model alone | 76.2% (0.0%) | 91.2% (0.0%) | 62.5% (0.0%) | 76.2% (0.0%) |
| hand up when not sure | 77.5% (45.0%) | 92.5% (15.0%) | 92.5% (76.2%) | 93.8% (42.5%) |
| hand up below 50% | 77.5% (1.2%) | 91.2% (0.0%) | 70.0% (16.2%) | 81.2% (12.5%) |
| hand up below 60% | 76.2% (11.2%) | 92.5% (3.8%) | 70.0% (18.8%) | 88.8% (22.5%) |
| hand up below 70% | 78.8% (17.5%) | 92.5% (8.8%) | 77.5% (37.5%) | 90.0% (26.2%) |
| hand up below 80% | 77.5% (38.8%) | 92.5% (13.8%) | 92.5% (81.2%) | 91.2% (31.2%) |
| hand up below 90% | 80.0% (77.5%) | 92.5% (70.0%) | 92.5% (100.0%) | 96.2% (57.5%) |
| hand up below 95% | 80.0% (97.5%) | 92.5% (100.0%) | 92.5% (100.0%) | 95.0% (87.5%) |
| hand up below 99% | 80.0% (100.0%) | 92.5% (100.0%) | 92.5% (100.0%) | 95.0% (100.0%) |
| big model alone | 80.0% (100.0%) | 92.5% (100.0%) | 92.5% (100.0%) | 95.0% (100.0%) |
