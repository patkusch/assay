"""A backend that asks a local Ollama model to pick a lettered option and reads back its odds.

Why: the model never writes an answer. It is shown the choices as A, B, C... and we read how likely
it thought each letter was as its very first word. That is one short pass, cheap, and gives real
probabilities rather than a guess parsed out of prose. Only the Python standard library is used.
"""
from __future__ import annotations

import json
import math
import socket
import urllib.error
import urllib.request

from ..types import BackendError, Question

# Single-character symbols that a tokenizer almost always keeps as one token.
# Letters first (models are best with these), then digits if there are more than 26 options.
SYMBOLS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
TOP_LOGPROBS = 20
FLOOR_MARGIN = 5.0  # a letter the model did not rank gets (lowest ranked score - this)


def option_codes(n: int) -> list[str]:
    """The short codes shown next to the options: A, B, C, ... then 0-9 after Z."""
    if n > len(SYMBOLS):
        raise BackendError(
            f"OllamaBackend can show at most {len(SYMBOLS)} options in one question (got {n}); "
            "split the choice into smaller groups"
        )
    return list(SYMBOLS[:n])


def build_prompt(state: str, question: Question, labels: list[str]) -> tuple[str, list[str]]:
    """Turn a question and its options into a prompt that asks for one letter.

    Returns the prompt and the code (letter) shown for each label, in the order given.
    """
    codes = option_codes(len(labels))
    lines = [
        "You are a careful decision maker. Read the situation, then answer the question by "
        "giving the code of exactly one option.",
        "",
        "SITUATION:",
        state.strip(),
        "",
        "QUESTION:",
        question.instructions.strip(),
    ]
    if question.type == "score":
        lines += [
            "",
            f"This is a rating on a scale from 1 to {question.levels}: 1 = lowest, "
            f"{question.levels} = highest. Each option below is one rating.",
        ]
    elif question.type == "noul":
        lines += ["", "This is a yes or no question."]
    lines += ["", "OPTIONS:"]
    for code, label in zip(codes, labels):
        lines.append(f"{code}. {label}")
    lines += ["", "Reply with the code of your chosen option only, nothing else.", "ANSWER:"]
    return "\n".join(lines), codes


def _logsumexp(xs: list[float]) -> float:
    m = max(xs)
    return m + math.log(sum(math.exp(x - m) for x in xs))


def parse_scores(data: dict, codes: list[str]) -> list[float]:
    """Read the model's first-word odds out of an Ollama reply and line them up with `codes`.

    Spellings of the same code ("A", " A", "a") are pooled. A code the model did not rank in its
    top list gets a floor just below the lowest one it did rank.
    """
    entries = data.get("logprobs")
    if not entries or not isinstance(entries, list):
        raise BackendError(
            "Ollama reply had no logprobs. This needs an Ollama version that supports "
            "logprobs (v0.12.11 or newer)."
        )
    tops = entries[0].get("top_logprobs") or []
    if not tops:
        tops = [{"token": entries[0].get("token", ""), "logprob": entries[0].get("logprob", 0.0)}]
    wanted = {c.lower(): i for i, c in enumerate(codes)}
    found: list[list[float]] = [[] for _ in codes]
    lowest = min(float(t["logprob"]) for t in tops)
    for t in tops:
        key = str(t.get("token", "")).strip().lower()
        if key in wanted:
            found[wanted[key]].append(float(t["logprob"]))
    if not any(found):
        seen = ", ".join(repr(str(t.get("token", ""))) for t in tops[:5])
        raise BackendError(
            f"model did not pick any option code {codes[0]}..{codes[-1]} as its first token "
            f"(it preferred: {seen}). Try a larger or instruction-tuned model."
        )
    floor = lowest - FLOOR_MARGIN
    return [_logsumexp(f) if f else floor for f in found]


class OllamaBackend:
    """Scores candidate answers with a local Ollama model, one short call per ordering."""

    def __init__(self, model: str = "gemma3", host: str = "http://127.0.0.1:11434", timeout: float = 60):
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout
        self.name = f"ollama:{model}"

    def _post(self, path: str, payload: dict) -> dict:
        req = urllib.request.Request(
            self.host + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            e.close()
            try:
                detail = json.loads(body).get("error", body)
            except ValueError:
                detail = body
            if e.code == 404 or "not found" in str(detail).lower():
                raise BackendError(
                    f"Ollama does not have model {self.model!r} ({detail}). "
                    f"Pull it first: ollama pull {self.model}"
                ) from e
            raise BackendError(f"Ollama returned HTTP {e.code}: {detail}") from e
        except (socket.timeout, TimeoutError) as e:
            raise BackendError(f"Ollama at {self.host} did not answer within {self.timeout}s") from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise BackendError(f"Ollama at {self.host} did not answer within {self.timeout}s") from e
            raise BackendError(
                f"cannot reach Ollama at {self.host} ({e.reason}). Is `ollama serve` running?"
            ) from e
        except ValueError as e:
            raise BackendError(f"Ollama sent a reply that is not JSON: {e}") from e

    def logprobs(self, state: str, question: Question, labels: list[str]) -> list[float]:
        prompt, codes = build_prompt(state, question, labels)
        data = self._post("/api/generate", {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 1},
            "logprobs": True,
            "top_logprobs": TOP_LOGPROBS,
        })
        return parse_scores(data, codes)
