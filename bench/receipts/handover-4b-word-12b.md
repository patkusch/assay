# Hand-over: gemma3 (word scoring) first, gemma3:12b when unsure

Made with `bench/handover.py` from saved receipts, calibrated odds, on the 320 test items both runs share. An item goes to the big model when the small model's confidence is below the cut-off. Time is the small model's call plus the big model's when it was handed up. "Random, same share" hands up the same number of items picked at random (mean of 200 draws).

| Rule | Share handed up | Right answers | Random, same share | Time per item |
|---|---|---|---|---|
| small model alone | 0.0% | 76.6% | 76.6% | 0.55 s |
| hand up when not sure | 44.7% | 89.1% | 82.7% | 1.46 s |
| hand up below 50% | 7.5% | 80.0% | 77.5% | 0.70 s |
| hand up below 60% | 14.1% | 81.9% | 78.4% | 0.82 s |
| hand up below 70% | 22.5% | 84.7% | 79.6% | 1.03 s |
| hand up below 80% | 41.2% | 88.4% | 82.2% | 1.39 s |
| hand up below 90% | 76.2% | 90.3% | 86.8% | 2.04 s |
| hand up below 95% | 96.2% | 90.0% | 89.5% | 2.39 s |
| hand up below 99% | 100.0% | 90.0% | 90.0% | 2.48 s |
| big model alone | 100.0% | 90.0% | 90.0% | 2.48 s |

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
