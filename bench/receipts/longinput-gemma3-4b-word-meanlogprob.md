# Long-input test: gemma3 (word scoring)

Run at 2026-09-27T18:12:34+00:00. 60 test items, each padded with about 12,000 characters of unrelated filler in these positions: both. Chunking splits text over 3,000 characters into overlapping pieces (`mean_logprob`).

- **Short original item:** 86.7% right (the ceiling).
- **Padded, plain backend:** 56.7% right on average across the positions tested.
- **Padded, with chunking:** 38.3% right on average.

| Task | Items | Short | both, plain | both, chunked |
|---|---|---|---|---|
| phishing | 15 | 87% | 53% | 47% |
| command_safety | 15 | 87% | 60% | 53% |
| routing | 15 | 73% | 40% | 40% |
| urgency | 15 | 100% | 73% | 13% |

The filler has nothing to do with any label, so padding never changes the right answer. A few dozen items per task is small: treat gaps of a few points as noise.
