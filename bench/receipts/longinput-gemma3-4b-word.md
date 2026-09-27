# Long-input test: gemma3 (word scoring)

Run at 2026-09-26T17:29:09+00:00. 100 test items, each padded with about 12,000 characters of unrelated filler in three positions. Chunking splits text over 3,000 characters into overlapping pieces (`max_evidence`).

- **Short original item:** 84.0% right (the ceiling).
- **Padded, plain backend:** 59.3% right on average across the three positions.
- **Padded, with chunking:** 53.7% right on average.

| Task | Items | Short | Filler before, plain | before, chunked | after, plain | after, chunked | both, plain | both, chunked |
|---|---|---|---|---|---|---|---|---|
| phishing | 25 | 92% | 56% | 48% | 80% | 48% | 52% | 48% |
| command_safety | 25 | 76% | 68% | 60% | 52% | 60% | 48% | 60% |
| routing | 25 | 72% | 40% | 44% | 52% | 56% | 32% | 44% |
| urgency | 25 | 96% | 84% | 52% | 80% | 68% | 68% | 56% |

The filler has nothing to do with any label, so padding never changes the right answer. A few dozen items per task is small: treat gaps of a few points as noise.
