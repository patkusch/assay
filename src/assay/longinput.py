"""Long-input wrapper: score a long text in overlapping pieces so a small model is not diluted.

Why: a small model reads a 20 KB message and loses the one sentence that decides the answer.
`ChunkedBackend` wraps any backend, cuts a long state into pieces at paragraph and sentence
boundaries, asks the inner backend about each piece, and combines the scores. Short input is
passed straight through, untouched, so nothing changes for it. Standard library only.
"""
from __future__ import annotations

import math
import re

from .types import Backend, BackendError, Question

COMBINE_MODES = ("max_evidence", "mean_logprob", "first_and_last", "head_tail")
HEAD_TAIL_MARK = "\n[...]\n"

_WORD = re.compile(r"\S+\s*")
_SENTENCE_END = re.compile(r"[.!?][\"')\]]*\s*$")


class _Unit:
    """A piece of text that is never cut: a sentence (or a single word when a sentence is too long)."""
    __slots__ = ("text", "para_end")

    def __init__(self, text: str, para_end: bool):
        self.text, self.para_end = text, para_end


def _units(text: str, max_chars: int) -> list[_Unit]:
    """Split into sentences, remembering which ones end a paragraph. Joining the units gives back `text` exactly."""
    out: list[_Unit] = []
    lead = text[: len(text) - len(text.lstrip())]
    cur = lead  # leading whitespace rides along with the first sentence
    for m in _WORD.finditer(text[len(lead):]):
        word = m.group()
        cur += word
        trailing = word[len(word.rstrip()):]
        para = trailing.count("\n") >= 2
        if para or _SENTENCE_END.search(word):
            out.append(_Unit(cur, para))
            cur = ""
    if cur:
        out.append(_Unit(cur, True))
    # a sentence longer than a whole chunk falls back to words, so nothing is ever cut mid-word
    final: list[_Unit] = []
    for u in out:
        if len(u.text) <= max_chars:
            final.append(u)
            continue
        words = _WORD.findall(u.text)
        for i, w in enumerate(words):
            final.append(_Unit(w, u.para_end and i == len(words) - 1))
    return final


def split_text(text: str, max_chars: int = 3000, overlap: int = 300) -> list[str]:
    """Cut `text` into chunks of about `max_chars` at paragraph/sentence/word boundaries.

    Each chunk starts with the last whole sentences of the one before (up to `overlap` characters),
    so a sentence sitting on a boundary appears whole in a chunk. A single word longer than
    `max_chars` is kept whole rather than cut.
    """
    if len(text) <= max_chars:
        return [text]
    units = _units(text, max_chars)
    chunks: list[str] = []
    start = 0          # first unit of the current chunk (may be an overlap carry-over)
    fresh = 0          # first unit that has not been in any chunk yet
    n = len(units)
    while fresh < n:
        end, size = start, 0
        while end < n and (size + len(units[end].text) <= max_chars or end == fresh):
            size += len(units[end].text)
            end += 1
        if end < n:
            # prefer to stop at a paragraph break if one falls in the back half of the chunk
            acc, best = 0, None
            for i in range(start, end):
                acc += len(units[i].text)
                if units[i].para_end and i + 1 > fresh and acc >= max_chars / 2:
                    best = i + 1
            if best is not None:
                end = best
        chunks.append("".join(u.text for u in units[start:end]))
        fresh = end
        if fresh >= n:
            break
        # carry the last whole sentences forward as overlap, always leaving room for progress
        nxt, carried = end, 0
        while nxt - 1 > start and carried + len(units[nxt - 1].text) <= overlap:
            nxt -= 1
            carried += len(units[nxt].text)
        while nxt < end and carried + len(units[end].text) > max_chars and nxt < fresh:
            carried -= len(units[nxt].text)
            nxt += 1
        start = nxt
    return chunks


def _log_softmax(xs: list[float]) -> list[float]:
    m = max(xs)
    if not math.isfinite(m):
        return list(xs)
    z = m + math.log(sum(math.exp(x - m) for x in xs))
    return [x - z for x in xs]


def _head_tail(text: str, max_chars: int) -> str:
    """The start and the end of the text (half the budget each), cut at word boundaries."""
    half = max(1, max_chars // 2)
    words = _WORD.findall(text)
    head, tail, used = [], [], 0
    for w in words:
        if used + len(w) > half and head:
            break
        head.append(w)
        used += len(w)
    used = 0
    for w in reversed(words[len(head):]):
        if used + len(w) > half and tail:
            break
        tail.append(w)
        used += len(w)
    tail.reverse()
    return "".join(head).rstrip() + HEAD_TAIL_MARK + "".join(tail).lstrip()


class ChunkedBackend:
    """Wrap a backend so long states are scored piece by piece. Same protocol, works with the engine unchanged.

    combine:
      max_evidence    per label, the best (highest) score over all chunks. Use when one sentence decides.
      mean_logprob    per label, the average score over all chunks. Use when the whole text carries the signal.
      first_and_last  only the first and last chunk, best of the two. Cheap; assumes the point is at either end.
      head_tail       one call on the start plus the end of the text, the middle is skipped. Cheapest.

    Each chunk's scores are turned into log-probabilities before combining (`normalize=True`) so a chunk
    cannot win just because the model's raw numbers happened to run high.
    After every call `last_trace` says what happened; `last_trace["truncated"]` is True if any text was
    left unscored (only when chunks were sampled, or in first_and_last / head_tail).
    """

    def __init__(
        self,
        inner: Backend,
        max_chars: int = 3000,
        overlap: int = 300,
        combine: str = "max_evidence",
        max_chunks: int = 12,
        normalize: bool = True,
    ):
        if combine not in COMBINE_MODES:
            raise ValueError(f"combine must be one of {COMBINE_MODES}")
        if max_chars < 1:
            raise ValueError("max_chars must be at least 1")
        if not (0 <= overlap < max_chars):
            raise ValueError("overlap must be 0 <= overlap < max_chars")
        if max_chunks < 2:
            raise ValueError("max_chunks must be at least 2")
        self.inner = inner
        self.max_chars, self.overlap, self.combine = max_chars, overlap, combine
        self.max_chunks, self.normalize = max_chunks, normalize
        self.name = f"chunked({getattr(inner, 'name', 'unknown')})"
        self.last_trace: dict = {}

    def logprobs(self, state: str, question: Question, labels: list[str]) -> list[float]:
        if len(state) <= self.max_chars:
            self.last_trace = {"mode": self.combine, "delegated": True, "chunks": 1, "scored": [0],
                               "winners": {}, "truncated": False, "sampled": False, "skipped": []}
            return self.inner.logprobs(state, question, labels)

        if self.combine == "head_tail":
            text = _head_tail(state, self.max_chars)
            scores = self.inner.logprobs(text, question, labels)
            self._check(scores, labels)
            self.last_trace = {"mode": "head_tail", "delegated": False, "chunks": 1, "scored": [0],
                               "winners": {}, "truncated": True, "sampled": False, "skipped": [],
                               "chars_total": len(state), "chars_scored": len(text)}
            return scores

        chunks = split_text(state, self.max_chars, self.overlap)
        total = len(chunks)
        if self.combine == "first_and_last":
            picks = sorted({0, total - 1})
        elif total > self.max_chunks:
            k = self.max_chunks  # evenly spaced, always including the first and the last
            picks = sorted({round(i * (total - 1) / (k - 1)) for i in range(k)})
        else:
            picks = list(range(total))
        skipped = [i for i in range(total) if i not in picks]

        per_chunk: list[list[float]] = []
        for i in picks:
            s = self.inner.logprobs(chunks[i], question, labels)
            self._check(s, labels)
            per_chunk.append(_log_softmax(s) if self.normalize else list(s))

        cols = list(zip(*per_chunk))
        if self.combine == "mean_logprob":
            out = [sum(c) / len(c) for c in cols]
        else:  # max_evidence and first_and_last both keep the strongest evidence per label
            out = [max(c) for c in cols]
        winners = {l: picks[max(range(len(c)), key=c.__getitem__)] for l, c in zip(labels, cols)}
        self.last_trace = {
            "mode": self.combine, "delegated": False, "chunks": total, "scored": picks,
            "winners": winners, "truncated": bool(skipped),
            "sampled": self.combine != "first_and_last" and total > self.max_chunks,
            "skipped": skipped,
        }
        return out

    @staticmethod
    def _check(scores: list[float], labels: list[str]) -> None:
        if len(scores) != len(labels):
            raise BackendError(f"inner backend returned {len(scores)} scores for {len(labels)} labels")
