"""A readable view of an answer for the terminal: one block per question with a bar for every option."""
from __future__ import annotations

BAR = 24


def _bar(p: float) -> str:
    filled = max(0, min(BAR, round(p * BAR)))
    if p > 0 and filled == 0:
        filled = 1  # a tiny probability still shows as a sliver, so it is not mistaken for zero
    return "█" * filled + "░" * (BAR - filled)


def _pct(p: float) -> str:
    return f"{p * 100:.1f}%" if (p >= 0.995 or p < 0.005) and p not in (0.0, 1.0) else f"{p * 100:.0f}%"


def format_answers(result: dict, questions: dict | None = None) -> str:
    """Turn a response dict (as printed by `decide`) into text. `questions` maps id to instruction text (optional)."""
    lines = []
    head = f"answered by {result.get('model', '?')} in {result.get('latency_ms', 0):.0f} ms"
    lines += [head, ""]
    for qid, a in result["answers"].items():
        probs = a["probabilities"]
        width = min(22, max(len(str(k)) for k in probs))
        value = a["value"]
        if isinstance(value, float):
            shown = f"{value:.2f}" if len(probs) > 2 and all(k.isdigit() for k in probs) else f"{value * 100:.0f}% yes"
        else:
            shown = str(value)
        tag = "calibrated" if a.get("calibrated") else "not calibrated"
        lines.append(f"{qid}: {shown}")
        if questions and questions.get(qid):
            lines.append(f"  {questions[qid][:100]}")
        best = max(probs, key=probs.get)
        for label, p in probs.items():
            mark = "*" if label == best else " "
            lines.append(f" {mark} {str(label)[:width]:<{width}}  {_bar(p)}  {_pct(p):>6}")
        note = f"  confidence {a['confidence'] * 100:.0f}%, stable across option orders {a['stability'] * 100:.0f}%, {tag}"
        lines.append(note)
        if a.get("abstain"):
            lines.append("  ⚠ not sure: " + " or ".join(str(x) for x in a.get("prediction_set", [])))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
