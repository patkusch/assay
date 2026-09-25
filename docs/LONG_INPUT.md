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

## The honest limit

This is proven on mock backends only. The tests show that a decisive sentence hidden in the middle of 20 KB
of filler is found by `max_evidence` and missed by cutting off the first few thousand characters, that
words are never split, and that short input is unchanged. It has **not** been measured with a live model
yet. Open questions that only a live run can answer: how well real small models score a piece that has no
evidence in it (if they lean toward one option on empty text, `max_evidence` will pick that up), and
whether the extra calls are worth their cost. Treat the defaults as a starting point until that
measurement is done.
