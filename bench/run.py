"""The assay benchmark harness.

What it does, in plain words: for each labelled task it asks the same model the same questions four ways
and grades every way against answers that were written by construction (never by another model):

  single        one fixed option order, raw probabilities
  shuffled      the options shown in several rotated orders and averaged (assay's order-proofing)
  calibrated    shuffled, then a per-task calibrator that was FITTED ON THE DEV HALF and is GRADED ON THE
                TEST HALF, so it is never marked on the data it learned from
  llm_baseline  an ordinary "generate a JSON answer and a confidence" call to the same Ollama model

Every number in the report comes from the test half. Full per-item receipts are written as JSON, and a
plain-English scoreboard is written next to them by bench/report.py.

    python bench/run.py --backend keyword --tasks all --orders 3 --out bench/receipts/keyword.json
    python bench/run.py --backend ollama --model gemma3 --tasks all --orders 3 --out bench/receipts/gemma3.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
ROOT = BENCH_DIR.parent
for _p in (str(ROOT / "src"), str(BENCH_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import _local as M  # noqa: E402  (local scoring helpers; see that file)
from assay.engine import orderings, softmax  # noqa: E402
from assay.types import Question  # noqa: E402

TASKS_DIR = BENCH_DIR / "tasks"
COVERAGES = (1.0, 0.8, 0.6, 0.4)
CONDITIONS = ("single", "shuffled", "calibrated", "llm_baseline")


# ---------------------------------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------------------------------
def load_tasks(names: list[str] | None = None, limit: int | None = None) -> dict[str, dict]:
    """Reads the task files. `limit` keeps only the first N items of each split (for quick runs and tests)."""
    specs = json.loads((TASKS_DIR / "tasks.json").read_text())
    names = names or list(specs)
    out = {}
    for name in names:
        if name not in specs:
            raise SystemExit(f"unknown task {name!r}; choose from {', '.join(specs)}")
        rows = [json.loads(line) for line in (TASKS_DIR / f"{name}.jsonl").read_text().splitlines() if line.strip()]
        if limit:
            kept: list[dict] = []
            for split in ("dev", "test"):
                kept += [r for r in rows if r["split"] == split][:limit]
            rows = kept
        q = specs[name]["question"]
        question = Question(type=q["type"], instructions=q["instructions"], options=q.get("options", []), levels=q.get("levels", 5))
        question.validate()
        out[name] = {"spec": specs[name], "question": question, "items": rows}
    return out


def _load_calibrator():
    """Uses the real `assay.calibrate.TemperatureCalibrator` when it exists, else the local stand-in."""
    try:
        from assay.calibrate import TemperatureCalibrator  # type: ignore
        return TemperatureCalibrator, "assay.calibrate"
    except ImportError:
        return M.LocalCalibrator, "bench/_local.py (assay.calibrate not importable)"


def make_backend(kind: str, model: str, host: str, timeout: float):
    if kind == "keyword":
        from assay.backends.mock import KeywordBackend
        return KeywordBackend()
    if kind == "ollama":
        from assay.backends.ollama import OllamaBackend
        return OllamaBackend(model, host, timeout=timeout)
    raise SystemExit(f"unknown backend {kind!r}")


# ---------------------------------------------------------------------------------------------------
# scoring one item
# ---------------------------------------------------------------------------------------------------
def score(backend, state: str, q: Question, base: list[str], n_orders: int) -> dict[str, float]:
    """Average option probabilities over `n_orders` rotations of `base`. Same maths as assay.engine.decide_one.

    The result is keyed in canonical label order so that exact ties break the same way whatever `base` is;
    a flip therefore only happens when the model itself changes its mind.
    """
    per = []
    for order in orderings(base, n_orders):
        raw = backend.logprobs(state, q, order)
        if len(raw) != len(order):
            raise ValueError(f"backend returned {len(raw)} scores for {len(order)} labels")
        per.append(dict(zip(order, softmax(raw))))
    return {l: sum(p[l] for p in per) / len(per) for l in q.labels()}


def _timed(fn):
    t0 = time.perf_counter()
    val = fn()
    return val, (time.perf_counter() - t0) * 1000.0


def run_item(backend, item: dict, q: Question, n_orders: int) -> dict:
    """Runs the single and shuffled conditions for one item, plus the reversed-order pass used for the flip check."""
    labels = q.labels()
    rev = list(reversed(labels))
    single, lat1 = _timed(lambda: score(backend, item["state"], q, labels, 1))
    single_rev = score(backend, item["state"], q, rev, 1)
    shuf, latn = _timed(lambda: score(backend, item["state"], q, labels, n_orders))
    shuf_rev = score(backend, item["state"], q, rev, n_orders)
    return {
        "single": {"probs": single, "top": M.top_label(single), "top_reversed": M.top_label(single_rev), "latency_ms": lat1},
        "shuffled": {"probs": shuf, "probs_reversed": shuf_rev, "top": M.top_label(shuf), "top_reversed": M.top_label(shuf_rev), "latency_ms": latn},
    }


# ---------------------------------------------------------------------------------------------------
# the ordinary generate-and-parse baseline
# ---------------------------------------------------------------------------------------------------
def make_ollama_baseline(model: str, host: str, timeout: float):
    """Returns a function (state, question) -> {answer, confidence, latency_ms, failed}.

    It asks the same Ollama model to WRITE a JSON answer with a stated confidence, at temperature 0, the way
    most people use an LLM as a classifier today. The JSON schema forces the answer into the allowed options.
    """
    host = host.rstrip("/")

    def call(state: str, q: Question) -> dict:
        labels = q.labels()
        schema = {
            "type": "object",
            "properties": {"answer": {"type": "string", "enum": labels}, "confidence": {"type": "number", "minimum": 0, "maximum": 1}},
            "required": ["answer", "confidence"],
        }
        prompt = (
            f"{q.instructions.strip()}\n\nAllowed answers: {', '.join(labels)}\n\nSITUATION:\n{state.strip()}\n\n"
            "Reply with JSON containing 'answer' (exactly one allowed answer) and 'confidence' "
            "(a number from 0 to 1: how likely you think it is that your answer is correct)."
        )
        body = json.dumps({"model": model, "prompt": prompt, "stream": False, "format": schema, "options": {"temperature": 0}}).encode()
        req = urllib.request.Request(host + "/api/generate", data=body, headers={"Content-Type": "application/json"})
        t0 = time.perf_counter()
        answer, conf, failed, err = None, None, True, None
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = json.loads(resp.read())["response"]
            obj = json.loads(text)
            answer, conf = str(obj["answer"]), float(obj["confidence"])
            failed = answer not in labels
        except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError) as e:
            err = f"{type(e).__name__}: {e}"
        return {"answer": answer if not failed else None, "confidence": conf, "latency_ms": (time.perf_counter() - t0) * 1000.0,
                "failed": failed, "error": err}

    return call


def baseline_sample(res: dict, labels: list[str], truth: str) -> dict:
    """Turns the model's stated answer and confidence into a probability vector so it can be graded like the others.

    The stated confidence is the probability of its chosen answer; the rest is shared equally among the other
    options. A confidence below 1/k would make some other option look likelier than the chosen one, so it is
    raised to 1/k, and a number between 1 and 100 is read as a percentage. A reply that could not be parsed counts as WRONG with a uniform guess.
    """
    k = len(labels)
    if res["failed"] or res["answer"] is None:
        return {"probs": {l: 1.0 / k for l in labels}, "truth": truth, "pred": None}
    c = res["confidence"]
    if 1.0 < c <= 100.0:  # the model wrote a percentage such as 85 instead of 0.85
        c /= 100.0
    c = min(1.0, max(1.0 / k, c))
    rest = (1.0 - c) / (k - 1) if k > 1 else 0.0
    return {"probs": {l: (c if l == res["answer"] else rest) for l in labels}, "truth": truth, "pred": res["answer"]}


# ---------------------------------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------------------------------
def condition_metrics(samples: list[dict], latencies: list[float], flips: list[bool] | None, sets: list[list[str]] | None = None) -> dict:
    """All the numbers for one condition on one set of items."""
    m: dict = {
        "n": len(samples),
        "accuracy": M.accuracy(samples),
        "ece": M.ece(samples),
        "brier": M.brier(samples),
        "nll": M.nll(samples),
        "latency_p50_ms": M.percentile(latencies, 50),
        "latency_p95_ms": M.percentile(latencies, 95),
        "flip_rate": (sum(flips) / len(flips)) if flips else None,
        "accuracy_at_coverage": {f"{int(c * 100)}": M.accuracy_at_coverage(samples, c) for c in COVERAGES},
        "abstain_rate": None,
        "accuracy_when_answered": None,
    }
    if sets is not None:
        answered = [(s, ps) for s, ps in zip(samples, sets) if len(ps) == 1]
        m["abstain_rate"] = 1 - len(answered) / len(samples) if samples else None
        m["accuracy_when_answered"] = (sum(1 for s, ps in answered if ps[0] == s["truth"]) / len(answered)) if answered else None
        m["set_coverage"] = sum(1 for s, ps in zip(samples, sets) if s["truth"] in ps) / len(samples) if samples else None
        m["avg_set_size"] = sum(len(ps) for ps in sets) / len(sets) if sets else None
    return m


def _collect(records: list[dict], cond: str, splits: tuple[str, ...]):
    rs = [r for r in records if r["split"] in splits and cond in r]
    samples = []
    for r in rs:
        s = {"probs": r[cond]["probs"], "truth": r["truth"]}
        if "pred" in r[cond]:
            s["pred"] = r[cond]["pred"]
        samples.append(s)
    lat = [r[cond]["latency_ms"] for r in rs]
    flips = [r[cond]["top"] != r[cond]["top_reversed"] for r in rs] if rs and "top_reversed" in rs[0][cond] else None
    sets = [r[cond]["prediction_set"] for r in rs] if rs and "prediction_set" in rs[0][cond] else None
    return samples, lat, flips, sets


# ---------------------------------------------------------------------------------------------------
# the run
# ---------------------------------------------------------------------------------------------------
def run_benchmark(backend, tasks: dict[str, dict], *, orders: int = 3, alpha: float = 0.1, baseline=None,
                  config: dict | None = None, progress=None) -> dict:
    """Runs every condition on every task and returns the full receipts dict."""
    say = progress or (lambda msg: None)
    Cal, cal_source = _load_calibrator()
    receipts = {
        "schema": 1,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "config": {**(config or {}), "orders": orders, "alpha": alpha, "calibrator": cal_source,
                   "metrics": "bench/_local.py (checked against assay.metrics in tests)",
                   "evaluated_on": "test split only; calibrator fitted on dev split only"},
        "versions": _versions(backend),
        "tasks": {},
    }
    # one untimed call so a cold model load does not pollute the first latency
    first = next(iter(tasks.values()))
    try:
        backend.logprobs(first["items"][0]["state"], first["question"], first["question"].labels())
        if baseline is not None:
            baseline(first["items"][0]["state"], first["question"])
    except Exception as e:  # noqa: BLE001  (a warm-up failure is reported, then the real run fails loudly)
        say(f"warm-up call failed: {e}")

    for name, t in tasks.items():
        q, items = t["question"], t["items"]
        labels = q.labels()
        say(f"[{name}] {len(items)} items")
        records = []
        for i, it in enumerate(items, 1):
            rec = {"id": it["id"], "split": it["split"], "truth": it["truth"], "hard": it.get("hard", False), "kind": it.get("kind", "")}
            rec.update(run_item(backend, it, q, orders))
            if baseline is not None:
                res = baseline(it["state"], q)
                smp = baseline_sample(res, labels, it["truth"])
                rec["llm_baseline"] = {"answer": res["answer"], "confidence": res["confidence"], "failed": res["failed"], "error": res["error"],
                                       "latency_ms": res["latency_ms"], "probs": smp["probs"], "pred": smp["pred"]}
            records.append(rec)
            if i % 20 == 0:
                say(f"[{name}] {i}/{len(items)}")

        # calibration: fit on dev only, apply to every item, grade on test only
        cal_info: dict = {}
        dev_samples = [{"probs": r["shuffled"]["probs"], "truth": r["truth"]} for r in records if r["split"] == "dev"]
        cal = Cal()
        try:
            cal.fit(dev_samples, alpha)
            fitted = True
            cal_info = {"n_fit": len(dev_samples), "temperature": getattr(cal, "temperature", None), "qhat": getattr(cal, "qhat", None),
                        "fit_report_in_sample": _jsonable(getattr(cal, "report", {}))}
        except ValueError as e:
            fitted = False
            cal_info = {"skipped": str(e)}
        if fitted:
            for r in records:
                p = cal.transform(r["shuffled"]["probs"])
                pr = cal.transform(r["shuffled"]["probs_reversed"])
                r["calibrated"] = {"probs": p, "top": M.top_label(p), "top_reversed": M.top_label(pr),
                                   "prediction_set": cal.prediction_set(p), "latency_ms": r["shuffled"]["latency_ms"]}

        conds: dict = {}
        for cond in CONDITIONS:
            if not any(cond in r for r in records):
                conds[cond] = {"skipped": "not run" if cond != "calibrated" else cal_info.get("skipped", "not run")}
                continue
            entry = {}
            for label, splits in (("test", ("test",)), ("dev", ("dev",))):
                if cond == "calibrated" and label == "dev":
                    continue  # the calibrator saw dev; grading it there would flatter it
                samples, lat, flips, sets = _collect(records, cond, splits)
                entry[label] = condition_metrics(samples, lat, flips, sets)
            conds[cond] = entry
        receipts["tasks"][name] = {"question": _question_dict(q), "n_items": len(items),
                                   "n_dev": sum(r["split"] == "dev" for r in records), "n_test": sum(r["split"] == "test" for r in records),
                                   "calibrator": cal_info, "conditions": conds, "items": records}

    receipts["pooled"] = pool(receipts)
    return receipts


def pool(receipts: dict) -> dict:
    """Test-split numbers over all tasks together (each task's own calibrator has already been applied)."""
    out: dict = {}
    for cond in CONDITIONS:
        recs = []
        for t in receipts["tasks"].values():
            recs += [r for r in t["items"] if r["split"] == "test" and cond in r]
        if not recs:
            out[cond] = {"skipped": "not run"}
            continue
        samples, lat, flips, sets = _collect(recs, cond, ("test",))
        out[cond] = {"test": condition_metrics(samples, lat, flips, sets)}
    return out


def _question_dict(q: Question) -> dict:
    return {"type": q.type, "instructions": q.instructions, "options": q.options, "levels": q.levels, "labels": q.labels()}


def _jsonable(x):
    try:
        json.dumps(x)
        return x
    except TypeError:
        return str(x)


def _versions(backend) -> dict:
    v = {"python": platform.python_version(), "platform": platform.platform()}
    try:
        import assay
        v["assay"] = getattr(assay, "__version__", "unknown")
    except ImportError:
        pass
    host = getattr(backend, "host", None)
    if host:
        try:
            with urllib.request.urlopen(host + "/api/version", timeout=5) as resp:
                v["ollama"] = json.loads(resp.read()).get("version")
        except (urllib.error.URLError, OSError, ValueError):
            v["ollama"] = "unreachable"
    return v


# ---------------------------------------------------------------------------------------------------
# command line
# ---------------------------------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Run the assay benchmark and write receipts plus a plain-English scoreboard.")
    ap.add_argument("--backend", choices=["keyword", "ollama"], default="keyword")
    ap.add_argument("--model", default="gemma3")
    ap.add_argument("--host", default="http://127.0.0.1:11434")
    ap.add_argument("--tasks", default="all", help="'all' or a comma-separated list of task names")
    ap.add_argument("--orders", type=int, default=3, help="how many option orderings to average in the shuffled condition")
    ap.add_argument("--alpha", type=float, default=0.1, help="conformal miss rate (0.1 = the true answer is in the set ~90%% of the time)")
    ap.add_argument("--limit", type=int, default=0, help="only the first N items of each split (quick runs)")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--no-baseline", action="store_true", help="skip the generate-and-parse baseline")
    ap.add_argument("--out", default=None, help="receipts path; default bench/receipts/<backend>-<model>.json")
    args = ap.parse_args(argv)

    names = None if args.tasks == "all" else [t.strip() for t in args.tasks.split(",") if t.strip()]
    tasks = load_tasks(names, args.limit or None)
    backend = make_backend(args.backend, args.model, args.host, args.timeout)
    baseline = None
    if args.backend == "ollama" and not args.no_baseline:
        baseline = make_ollama_baseline(args.model, args.host, args.timeout)
    out = Path(args.out) if args.out else BENCH_DIR / "receipts" / f"{args.backend}{'-' + args.model.replace(':', '_') if args.backend == 'ollama' else ''}.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    config = {"backend": args.backend, "model": args.model if args.backend == "ollama" else None, "host": args.host if args.backend == "ollama" else None,
              "tasks": list(tasks), "limit": args.limit or None, "baseline": "ollama /api/generate JSON" if baseline else "not run"}
    receipts = run_benchmark(backend, tasks, orders=args.orders, alpha=args.alpha, baseline=baseline, config=config,
                             progress=lambda m: print(m, file=sys.stderr))
    out.write_text(json.dumps(receipts, indent=1) + "\n")

    import report
    md_path = out.with_suffix(".md")
    md_path.write_text(report.build_report(receipts))
    print(f"receipts: {out}\nscoreboard: {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
