# Rewording test: gemma3

Run at 2026-09-26T13:56:48+00:00. 240 test items, each asked with the original question and 3 rewordings that keep every label definition. Option order was averaged over 3 rotations, so only the wording changes.

- **The answer changed with the wording on 37.1% of items** (at least one wording gave a different top answer).
- **Two wordings disagreed on 21.5% of pairs** on average.
- **Accuracy by wording:** 75.0%, 81.7%, 80.8%, 72.9% (spread 8.8 points). The first is the original wording.

| Task | Items | Answer changed with wording | Pairwise disagreement | Accuracy by wording | Spread |
|---|---|---|---|---|---|
| phishing | 60 | 20.0% | 10.8% | 82% / 92% / 83% / 75% | 16.7 pts |
| command_safety | 60 | 43.3% | 25.6% | 83% / 82% / 53% / 62% | 30.0 pts |
| routing | 60 | 45.0% | 27.5% | 58% / 72% / 88% / 73% | 30.0 pts |
| urgency | 60 | 40.0% | 21.9% | 77% / 82% / 98% / 82% | 21.7 pts |

The rewordings are in `bench/rewordings.json`. Each was written by hand to keep the same label definitions; a test checks the key terms are all still there. A few dozen items per task is small, so treat gaps of a few points as noise.
