"""Command line: `python -m assay decide|serve|calibrate|backends`."""
from __future__ import annotations

import argparse
import json
import sys

from .bundle import CalibrationBundle, describe, fit_bundle, load_labelled, questions_from_body
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
        sp.add_argument("--chunk-chars", type=int, default=0,
                        help="split situations longer than this many characters into overlapping pieces (0 = never split)")
        sp.add_argument("--chunk-combine", default="max_evidence",
                        choices=["max_evidence", "mean_logprob", "first_and_last", "head_tail"],
                        help="how to combine the pieces' scores (see docs/LONG_INPUT.md)")

    def answering(sp):
        sp.add_argument("--calibration", help="a file made by `assay calibrate`; its rescaling is applied to answers")
        sp.add_argument("--confidence-floor", type=float, default=0.0,
                        help="mark an answer 'abstain' when its confidence is below this (0 to 1)")

    d = sub.add_parser("decide", help="answer questions about a situation and print JSON")
    d.add_argument("--state", help="the situation, as text")
    d.add_argument("--question", action="append", default=[],
                   help="kind:instructions[:opt1|opt2]; kind is choice, score or noul (repeatable)")
    d.add_argument("--request", help="a JSON file in the same shape the server takes ('-' for stdin)")
    common(d)
    answering(d)

    s = sub.add_parser("serve", help="run the HTTP server")
    s.add_argument("--bind", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8787)
    common(s)
    answering(s)

    c = sub.add_parser("calibrate", help="fit a calibration from labelled examples and save it")
    c.add_argument("--request", required=True, help="a request-shaped JSON file; only its 'questions' are used")
    c.add_argument("--labelled", required=True, help='JSONL file, one {"question", "state", "truth"} per line')
    c.add_argument("--out", required=True, help="where to write the calibration file")
    c.add_argument("--alpha", type=float, default=0.1,
                   help="miss rate you accept for the not-sure set (0.1 = right answer inside it about 90%% of the time)")
    common(c)

    sub.add_parser("backends", help="list the available backends")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "backends":
            print(json.dumps(BACKENDS, indent=2))
            return 0
        backend = make_backend(args.backend, args.model, args.host, args.timeout)
        if getattr(args, "chunk_chars", 0):
            from .longinput import ChunkedBackend
            backend = ChunkedBackend(backend, max_chars=args.chunk_chars, overlap=min(300, args.chunk_chars // 10), combine=args.chunk_combine)
        if args.cmd == "calibrate":
            with open(args.request, encoding="utf-8") as f:
                questions = questions_from_body(json.load(f))
            bundle = fit_bundle(backend, questions, load_labelled(args.labelled), n_orders=args.orders, alpha=args.alpha)
            bundle.save(args.out)
            print(describe(bundle))
            print(f"\nSaved to {args.out}")
            return 0
        bundle = None
        if args.calibration:
            bundle = CalibrationBundle.load(args.calibration)
            warning = bundle.check(getattr(backend, "name", "unknown"))
            if warning:
                print(warning, file=sys.stderr)
        calibrators = bundle.calibrators if bundle else None
        if args.cmd == "serve":
            serve(backend, args.bind, args.port, args.orders, calibrators, args.confidence_floor, bundle)
            return 0
        if args.request:
            raw = sys.stdin.read() if args.request == "-" else open(args.request, encoding="utf-8").read()
            body = json.loads(raw)
        else:
            if args.state is None or not args.question:
                raise BadRequest("give --request FILE, or --state plus at least one --question")
            body = {"state": args.state,
                    "questions": {f"q{i + 1}": parse_question_arg(q) for i, q in enumerate(args.question)}}
        print(json.dumps(run_request(backend, body, n_orders=args.orders, calibrators=calibrators,
                                     confidence_floor=args.confidence_floor, bundle=bundle), indent=2))
        return 0
    except (BadRequest, ValueError, OSError) as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2
    except BackendError as e:
        print(json.dumps({"error": f"backend failed: {e}"}), file=sys.stderr)
        return 3
