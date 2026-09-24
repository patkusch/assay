"""Command line: `python -m assay decide|serve|backends`. Prints JSON."""
from __future__ import annotations

import argparse
import json
import sys

from .server import BadRequest, run_request, serve
from .types import BackendError

BACKENDS = {
    "ollama": "local Ollama model reading option probabilities (needs `ollama serve`)",
    "keyword": "test stand-in that counts option words in the state (no model)",
}


def make_backend(kind: str, model: str, host: str, timeout: float):
    if kind == "keyword":
        from .backends.mock import KeywordBackend
        return KeywordBackend()
    from .backends.ollama import OllamaBackend
    return OllamaBackend(model=model, host=host, timeout=timeout)


def parse_question_arg(spec: str) -> dict:
    """Read 'kind:instructions[:opt1|opt2]'. For a score, the option part is the number of levels."""
    kind, _, rest = spec.partition(":")
    if not rest:
        raise BadRequest(f"question {spec!r} must look like kind:instructions[:opt1|opt2]")
    q: dict = {"type": kind.strip()}
    if kind == "choice":
        instructions, _, opts = rest.rpartition(":")
        if not instructions:
            raise BadRequest("a choice question needs options: choice:instructions:opt1|opt2")
        q["instructions"], q["options"] = instructions, [o.strip() for o in opts.split("|")]
    elif kind == "score":
        instructions, _, lv = rest.rpartition(":")
        if instructions and lv.strip().isdigit():
            q["instructions"], q["levels"] = instructions, int(lv)
        else:
            q["instructions"] = rest
    else:
        q["instructions"] = rest
    return q


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="assay", description="Typed, calibrated decisions from a small local model.")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp):
        sp.add_argument("--backend", choices=list(BACKENDS), default="ollama")
        sp.add_argument("--model", default="gemma3")
        sp.add_argument("--host", default="http://127.0.0.1:11434", help="Ollama address")
        sp.add_argument("--timeout", type=float, default=60)
        sp.add_argument("--orders", type=int, default=3, help="how many option orderings to average")

    d = sub.add_parser("decide", help="answer questions about a situation and print JSON")
    d.add_argument("--state", help="the situation, as text")
    d.add_argument("--question", action="append", default=[],
                   help="kind:instructions[:opt1|opt2]; kind is choice, score or noul (repeatable)")
    d.add_argument("--request", help="a JSON file in the same shape the server takes ('-' for stdin)")
    common(d)

    s = sub.add_parser("serve", help="run the HTTP server")
    s.add_argument("--bind", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8787)
    common(s)

    sub.add_parser("backends", help="list the available backends")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "backends":
            print(json.dumps(BACKENDS, indent=2))
            return 0
        backend = make_backend(args.backend, args.model, args.host, args.timeout)
        if args.cmd == "serve":
            serve(backend, args.bind, args.port, args.orders)
            return 0
        if args.request:
            raw = sys.stdin.read() if args.request == "-" else open(args.request, encoding="utf-8").read()
            body = json.loads(raw)
        else:
            if args.state is None or not args.question:
                raise BadRequest("give --request FILE, or --state plus at least one --question")
            body = {"state": args.state,
                    "questions": {f"q{i + 1}": parse_question_arg(q) for i, q in enumerate(args.question)}}
        print(json.dumps(run_request(backend, body, n_orders=args.orders), indent=2))
        return 0
    except (BadRequest, ValueError, OSError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2
    except BackendError as e:
        print(json.dumps({"error": f"backend failed: {e}"}), file=sys.stderr)
        return 3
