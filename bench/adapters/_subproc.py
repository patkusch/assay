"""Shared plumbing for the Von and Verdict adapters: a kept-alive worker process speaking JSON lines, and a smoke test.

Assay stays dependency-free. Each project's own code (torch, transformers ...) lives in its own venv under
assay-clones/, and a tiny worker script there does the real inference. This module only starts the worker and
talks to it.
"""
from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from assay.types import BackendError, Question  # noqa: E402

FLOOR = 1e-9


def clones_dir() -> Path:
    """Where the untrusted clones live. Override with ASSAY_CLONES; default is a sibling of the assay repo."""
    return Path(os.environ.get("ASSAY_CLONES", ROOT.parent / "assay-clones"))


class WorkerBackend:
    """Backend that forwards every call to a long-lived worker in the clone's own venv."""

    name = "worker"
    repo_dir = ""       # folder name under assay-clones
    worker_file = ""    # script under assay-clones/workers
    startup_timeout = 300.0
    call_timeout = 120.0
    level_template = "{label}"   # text shown to the model for one score level

    def __init__(self, clones: Path | None = None, level_template: str | None = None):
        self.clones = Path(clones) if clones else clones_dir()
        if level_template:
            self.level_template = level_template
        self.python = self.clones / self.repo_dir / ".venv" / "bin" / "python"
        self.worker = self.clones / "workers" / self.worker_file
        self.proc: subprocess.Popen | None = None
        self.calls = 0
        self.truncated_items = 0     # calls where the project cut the state to fit its length limit
        self.latencies_ms: list[float] = []
        self.abstain_mass: list[float] = []

    # -- availability ------------------------------------------------------------------------------------------
    def installed(self) -> bool:
        return self.python.exists() and self.worker.exists()

    # -- process handling --------------------------------------------------------------------------------------
    def _start(self) -> None:
        if not self.installed():
            raise BackendError(f"{self.name}: clone/venv not found under {self.clones / self.repo_dir}")
        env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false",
                   HF_HOME=str(self.clones / ".hf-cache"), PYTHONDONTWRITEBYTECODE="1")
        self.proc = subprocess.Popen([str(self.python), str(self.worker)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL if os.environ.get("ASSAY_QUIET_WORKER") else None,
                                     text=True, env=env, cwd=str(self.clones / self.repo_dir))
        line = self._readline(self.startup_timeout)
        if not json.loads(line).get("ready"):
            raise BackendError(f"{self.name}: worker did not report ready: {line!r}")

    def _readline(self, timeout: float) -> str:
        import selectors
        assert self.proc and self.proc.stdout
        sel = selectors.DefaultSelector()
        sel.register(self.proc.stdout, selectors.EVENT_READ)
        if not sel.select(timeout):
            self.close()
            raise BackendError(f"{self.name}: worker timed out after {timeout:.0f}s")
        line = self.proc.stdout.readline()
        if not line:
            raise BackendError(f"{self.name}: worker exited (code {self.proc.poll()})")
        return line

    def close(self) -> None:
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
        self.proc = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- the Backend protocol ----------------------------------------------------------------------------------
    def descriptions(self, question: Question, labels: list[str]) -> list[str]:
        """What the model reads for each label. Choices and yes/no use the label itself; score levels use level_template."""
        if question.type == "score":
            return [self.level_template.format(label=l, levels=question.levels) for l in labels]
        return list(labels)

    def logprobs(self, state: str, question: Question, labels: list[str]) -> list[float]:
        if self.proc is None or self.proc.poll() is not None:
            self._start()
        assert self.proc and self.proc.stdin
        req = {"qtype": question.type, "instructions": question.instructions, "labels": labels, "state": state,
               "descriptions": self.descriptions(question, labels)}
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()
        out = json.loads(self._readline(self.call_timeout))
        if not out.get("ok"):
            raise BackendError(f"{self.name}: {out.get('error')}")
        probs = out["probs"]
        if len(probs) != len(labels):
            raise BackendError(f"{self.name}: got {len(probs)} scores for {len(labels)} labels")
        self.calls += 1
        self.truncated_items += 1 if out.get("truncated") else 0
        if "abstain_p" in out:
            self.abstain_mass.append(out["abstain_p"])
        return [math.log(max(float(p), FLOOR)) for p in probs]


# ---------------------------------------------------------------------------------------------------------------
# smoke test: 5 items per task, single fixed order, timed per call
# ---------------------------------------------------------------------------------------------------------------
def smoke(backend: WorkerBackend, per_task: int = 5, tasks: list[str] | None = None, split: str = "test") -> dict:
    """Runs `per_task` items of each task in its canonical option order. Returns accuracy and per-call latency (ms)."""
    specs = json.loads((ROOT / "bench" / "tasks" / "tasks.json").read_text())
    report: dict = {}
    for name in tasks or list(specs):
        q = specs[name]["question"]
        question = Question(type=q["type"], instructions=q["instructions"], options=q.get("options", []), levels=q.get("levels", 5))
        question.validate()
        labels = question.labels()
        rows = [json.loads(l) for l in (ROOT / "bench" / "tasks" / f"{name}.jsonl").read_text().splitlines() if l.strip()]
        rows = [r for r in rows if r["split"] == split][:per_task]
        correct, lats, detail = 0, [], []
        for r in rows:
            t0 = time.perf_counter()
            lp = backend.logprobs(r["state"], question, labels)
            lats.append((time.perf_counter() - t0) * 1000)
            pred = labels[max(range(len(lp)), key=lp.__getitem__)]
            correct += pred == r["truth"]
            detail.append((r["id"], r["truth"], pred))
        report[name] = {"n": len(rows), "correct": correct, "accuracy": correct / max(len(rows), 1),
                        "latency_ms_median": sorted(lats)[len(lats) // 2] if lats else None,
                        "latency_ms_mean": sum(lats) / len(lats) if lats else None, "detail": detail}
    return report


def smoke_main(cls) -> None:
    import argparse
    ap = argparse.ArgumentParser(description=f"Smoke test for the {cls.name} adapter")
    ap.add_argument("--per-task", type=int, default=5)
    ap.add_argument("--level-template", default=None, help="text for a score level, e.g. 'Level {label} of {levels}'")
    args = ap.parse_args()
    b = cls(level_template=args.level_template)
    t0 = time.perf_counter()
    b.logprobs("warm-up", Question(type="noul", instructions="Is this a test?"), ["yes", "no"])
    print(f"{b.name}: worker start + first call {time.perf_counter() - t0:.1f}s", file=sys.stderr)
    rep = smoke(b, args.per_task)
    for name, r in rep.items():
        print(f"{name:15s} {r['correct']}/{r['n']}  median {r['latency_ms_median']:.0f} ms  mean {r['latency_ms_mean']:.0f} ms")
        for d in r["detail"]:
            print("   ", *d)
    print(f"truncated items: {b.truncated_items}  calls: {b.calls}")
    b.close()
