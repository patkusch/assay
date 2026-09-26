# Rewording test: gemma3 (word scoring)

Run at 2026-09-26T14:13:11+00:00. 240 test items, each asked with the original question and 3 rewordings that keep every label definition. Option order was averaged over 3 rotations, so only the wording changes.

- **The answer changed with the wording on 27.5% of items** (at least one wording gave a different top answer).
- **Two wordings disagreed on 16.2% of pairs** on average.
- **Accuracy by wording:** 78.3%, 80.4%, 84.2%, 77.9% (spread 6.2 points). The first is the original wording.

| Task | Items | Answer changed with wording | Pairwise disagreement | Accuracy by wording | Spread |
|---|---|---|---|---|---|
| phishing | 60 | 6.7% | 3.6% | 90% / 92% / 88% / 88% | 3.3 pts |
| command_safety | 60 | 36.7% | 20.6% | 78% / 73% / 65% / 58% | 20.0 pts |
| routing | 60 | 40.0% | 25.0% | 63% / 73% / 92% / 82% | 28.3 pts |
| urgency | 60 | 26.7% | 15.8% | 82% / 83% / 92% / 83% | 10.0 pts |

The rewordings are in `bench/rewordings.json`. Each was written by hand to keep the same label definitions; a test checks the key terms are all still there. A few dozen items per task is small, so treat gaps of a few points as noise.
