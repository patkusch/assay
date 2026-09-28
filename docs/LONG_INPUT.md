# Long input

## What it does

Small models get diluted by long text. If the one sentence that decides the answer is buried in 20 KB of
other words, the model often reads past it. `ChunkedBackend` fixes this by reading the text in pieces.

It wraps any backend and looks like a backend itself, so the engine needs no change:

```python
from assay import decide
from assay.longinput import ChunkedBackend

backend = ChunkedBackend(OllamaBackend(...), max_chars=3000, overlap=300, combine="max_evidence")
response = decide(backend, request)
```

If the text is short enough (at most `max_chars`) the wrapper does nothing: the text goes straight to the
inner backend and the scores are identical. Long text is cut into pieces, each piece is scored on its own
with the same question, and the results are merged.

## How the text is cut

- At paragraph breaks where possible, otherwise at sentence ends, otherwise between words.
- A word is never cut in half. (A single word longer than `max_chars` is kept whole.)
- Each piece starts with the last sentences of the piece before it (up to `overlap` characters), so a
  sentence sitting on a boundary is always seen whole in at least one piece.
- The question and the options are never touched.
- Before merging, each piece's scores are turned into log-probabilities, so a piece cannot win just
  because the model's raw numbers ran high.

## Which mode to use

| Mode | What it does | Use it when | Cost |
|---|---|---|---|
| `max_evidence` (default) | For each option, keeps the strongest score from any piece | One buried sentence decides (a hidden link, a password request in a long email) | every piece |
| `mean_logprob` | Averages each option's score over all pieces | The whole text carries the signal (tone, overall complaint) | every piece |
| `first_and_last` | Scores only the first and last piece, keeps the stronger | The point is at the start or end (subject line, sign-off, latest reply on top or bottom) | two calls |
| `head_tail` | One call on the start plus the end, the middle is skipped | You need the cheapest option and accept losing the middle | one call |

`max_evidence` can be fooled the other way: a long text with one alarming sentence that is actually quoted
or negated will score as alarming. Use `mean_logprob` if that is your data.

## Never silently dropping text

`max_chunks` (default 12) caps the number of pieces scored. If a text needs more, pieces are sampled evenly
and the first and last are always kept. Every call writes a note to `backend.last_trace`:

```python
{"mode": "max_evidence", "chunks": 18, "scored": [0, 1, 3, ...], "skipped": [2, 5, ...],
 "winners": {"scam": 7, "safe": 0}, "truncated": True, "sampled": True}
```

- `chunks`: how many pieces the text made. `scored`: which ones were read. `skipped`: which were not.
- `winners`: for each option, the piece that gave it its best score. Useful when an answer looks wrong:
  print that piece and see what the model saw.
- `truncated` is True whenever any text went unread (sampling, `first_and_last` with more than two pieces,
  or `head_tail`). If it is False, every character was scored.

The engine asks several times with the options in different orders, so `last_trace` describes the most
recent call.

## Measured, and it did not help

100 real test items (gemma3 4B, word scoring), each padded with about 12,000 characters of unrelated filler
placed before the item, after it, or on both sides. The filler has nothing to do with any label, so the
right answer never changes. Full table: [bench/receipts/longinput-gemma3-4b-word.md](../bench/receipts/longinput-gemma3-4b-word.md).

| | Short original | Padded, plain | Padded, chunked (`max_evidence`) |
|---|---|---|---|
| Right answers | 84.0% | 59.3% | 53.7% |

- **Padding hurts a lot**, ceiling to plain: 84.0% down to 59.3%. That was expected.
- **Chunking made it worse, not better**: 53.7% against 59.3% for the plain backend on the same padded items. That was the opposite of what this wrapper is for.
- **The suspected reason** is the open question flagged below, now confirmed: a chunk with no real evidence in it still gets scored, and `max_evidence` takes the single highest score across all chunks. A small model given an evidence-free chunk and forced to pick one option leans toward whichever option its wording happens to favour, and if that lean is a strong `max_evidence` score, an irrelevant filler chunk can outvote the one real chunk. Splitting the text hands the model more chances to be confidently wrong, not fewer.
- **`command_safety` was the exception**, where chunking matched or beat the plain backend in two of three positions. The other three tasks lost ground everywhere chunking was tried.

**Conclusion: `max_evidence` is not recommended for real use as it stands.** The mock-backend tests below still hold; they proved the plumbing works, not that the strategy helps a real model. Until a real fix is found, a long input is better handled by keeping the state short (summarise before calling assay) than by chunking.

## The other combine modes were tried too, and neither fixed it

60 real test items (gemma3 4B, word scoring), padding on both sides only (the filler wraps the item, which
is the hardest case: the real content is buried in the middle, not at either end). Full tables:
[mean_logprob](../bench/receipts/longinput-gemma3-4b-word-meanlogprob.md),
[head_tail](../bench/receipts/longinput-gemma3-4b-word-headtail.md).

| | Padded, plain | `max_evidence`* | `mean_logprob` | `head_tail` |
|---|---|---|---|---|
| Right answers | 56.7% | ~52%* | 38.3% | 35.0% |

\* `max_evidence`'s number here is read off the "both" column of the 100-item run above (different item
count, so treat it as a rough guide, not a like-for-like row): on that slice alone it was roughly level
with the plain backend, not clearly worse. The pooled 53.7% above is dragged down mainly by the "before"
and "after" positions.

- **Neither alternative helped. Both did clearly worse than `max_evidence`.** `mean_logprob` averages every
  chunk's score, filler included, so a handful of irrelevant chunks steadily dilute the one real one.
  `head_tail` did worst of all, and that is expected by its own design: it reads only the start and end of
  the text and skips the middle outright, and "both" padding puts the real item exactly in that skipped
  middle. It was never going to see the message. `head_tail` still deserves a fair test on "before" or
  "after" padding, where the real content sits at one end within its reach; that has not been run.
- **The "discount an unsure chunk" idea from the previous version of this doc was not built or tested.**
  It remains the more promising direction than either mode tried here, since both `mean_logprob` and
  `head_tail` let every chunk count (or discard chunks) without ever asking the chunk itself how sure it
  was.
- **The recommendation is unchanged: keep the state short.** Three combine modes have now been measured on
  real padded input and none of them beat doing nothing.

## What the mock-backend tests still show

The tests below (mock backends only) show that a decisive sentence hidden in the middle of 20 KB of filler
is found by `max_evidence` and missed by cutting off the first few thousand characters, that words are
never split, and that short input is unchanged. That is the mechanism working as designed; the live result
above shows the mechanism is not enough on its own with a real, imperfect model.

## From the command line

Add `--chunk-chars 3000` to `decide`, `serve` or `calibrate` and situations longer than that are split into overlapping pieces. `--chunk-combine` picks how the pieces are combined (default `max_evidence`).
