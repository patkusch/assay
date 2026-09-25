"""A small web server that answers typed decision requests, shaped like the Jev `POST /v1/systemone` call.

Why: so any program in any language can send "here is a situation, here are my questions" and get back
typed, calibrated answers over plain HTTP. Standard library only.
"""
from __future__ import annotations

import copy
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .engine import decide
from .types import BackendError, Question, Request

MAX_BODY_BYTES = 4 * 1024 * 1024


class BadRequest(ValueError):
    """The caller sent something we cannot use. Becomes an HTTP 400 with a plain message."""


def state_to_text(state: object) -> str:
    """Turn the situation into text: strings as they are, lists joined by lines, anything else as JSON."""
    if isinstance(state, str):
        return state
    if isinstance(state, list):
        return "\n".join(s if isinstance(s, str) else json.dumps(s, ensure_ascii=False) for s in state)
    return json.dumps(state, ensure_ascii=False)


def parse_request(body: object) -> tuple[Request, str | None]:
    """Check a decoded JSON body and turn it into a Request plus the optional model name."""
    if not isinstance(body, dict):
        raise BadRequest("body must be a JSON object")
    if "state" not in body or body["state"] is None:
        raise BadRequest("missing 'state'")
    questions = body.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise BadRequest("'questions' must be a non-empty object of id -> question")
    model = body.get("model")
    if model is not None and not isinstance(model, str):
        raise BadRequest("'model' must be a string")
    parsed: dict[str, Question] = {}
    for qid, spec in questions.items():
        if not isinstance(spec, dict):
            raise BadRequest(f"question {qid!r} must be an object")
        instructions = spec.get("instructions")
        if not isinstance(instructions, str) or not instructions.strip():
            raise BadRequest(f"question {qid!r} needs non-empty 'instructions'")
        options = spec.get("options", [])
        if not isinstance(options, list) or not all(isinstance(o, str) for o in options):
            raise BadRequest(f"question {qid!r}: 'options' must be a list of strings")
        levels = spec.get("levels", 5)
        if isinstance(levels, bool) or not isinstance(levels, int):
            raise BadRequest(f"question {qid!r}: 'levels' must be an integer")
        q = Question(str(spec.get("type", "")), instructions, options, levels)
        try:
            q.validate()
        except ValueError as e:
            raise BadRequest(f"question {qid!r}: {e}") from e
        parsed[qid] = q
    return Request(state_to_text(body["state"]), parsed), model


def response_body(request: Request, response) -> dict:
    """The JSON reply: the engine's answer, plus a `choice`/`score`/`noul` field on each answer that repeats `value`."""
    out = response.to_dict()
    for qid, q in request.questions.items():
        out["answers"][qid][q.type] = out["answers"][qid]["value"]
    return out


def backend_for(backend, model: str | None):
    """Use the server's backend, or a copy pointed at the model the caller asked for (if the backend has one)."""
    if model and hasattr(backend, "model") and model != backend.model:
        clone = copy.copy(backend)
        clone.model = model
        clone.name = f"{getattr(backend, 'name', 'backend').split(':')[0]}:{model}"
        return clone
    return backend


def run_request(backend, body: object, *, n_orders: int = 3, calibrators: dict | None = None,
                confidence_floor: float = 0.0, bundle=None) -> dict:
    """The whole job for one decoded request body. Shared by the server and the command line.

    If a `bundle` is given and the caller asked for a different model than the server's,
    and that model is not the one it was fitted with, the calibration is left out: it would be wrong for that model.
    """
    request, model = parse_request(body)
    used = backend_for(backend, model)
    if bundle is not None and calibrators and used is not backend and bundle.check(getattr(used, "name", "unknown")):
        calibrators = None
    resp = decide(used, request, n_orders=n_orders, calibrators=calibrators, confidence_floor=confidence_floor)
    return response_body(request, resp)


def make_server(backend, host: str = "127.0.0.1", port: int = 8787, n_orders: int = 3,
                calibrators: dict | None = None, confidence_floor: float = 0.0,
                bundle=None) -> ThreadingHTTPServer:
    """Build the server without starting it (port 0 picks a free port). Useful for tests.

    Pass a `CalibrationBundle` as `bundle` to use its calibrators and to serve `GET /v1/calibration`.
    """
    if bundle is not None and calibrators is None:
        calibrators = bundle.calibrators

    class Handler(BaseHTTPRequestHandler):
        server_version = "assay"

        def _send(self, code: int, payload: dict) -> None:
            data = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/healthz":
                self._send(200, {"status": "ok", "backend": getattr(backend, "name", "unknown")})
            elif self.path == "/v1/calibration":
                if bundle is None:
                    self._send(404, {"error": "no calibration is loaded"})
                else:
                    out = bundle.summary()
                    out["warning"] = bundle.check(getattr(backend, "name", "unknown"))
                    self._send(200, out)
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/v1/systemone":
                self._send(404, {"error": "not found"})
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                self._send(400, {"error": "bad Content-Length"})
                return
            if length <= 0 or length > MAX_BODY_BYTES:
                self._send(400, {"error": f"body must be 1..{MAX_BODY_BYTES} bytes"})
                return
            try:
                body = json.loads(self.rfile.read(length))
            except ValueError:
                self._send(400, {"error": "body is not valid JSON"})
                return
            try:
                self._send(200, run_request(backend, body, n_orders=n_orders, calibrators=calibrators,
                                              confidence_floor=confidence_floor, bundle=bundle))
            except BadRequest as e:
                self._send(400, {"error": str(e)})
            except BackendError as e:
                self._send(502, {"error": f"backend failed: {e}"})

        def log_message(self, fmt, *args):  # keep the console quiet
            pass

    return ThreadingHTTPServer((host, port), Handler)


def serve(backend, host: str = "127.0.0.1", port: int = 8787, n_orders: int = 3,
          calibrators: dict | None = None, confidence_floor: float = 0.0, bundle=None) -> None:
    """Run the server until interrupted."""
    srv = make_server(backend, host, port, n_orders, calibrators, confidence_floor, bundle)
    print(f"assay listening on http://{host}:{srv.server_address[1]} (backend: {getattr(backend, 'name', '?')})", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
