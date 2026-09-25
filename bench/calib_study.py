"""How should assay calibrate when it only has a few labelled examples?

Works OFFLINE on a saved receipts file (no model is called). Every task in the file has a dev half and a
test half. Every method below is fitted on the dev half ONLY and graded on the test half ONLY.

Methods compared:

  raw      no temperature change (T = 1), but still a conformal "not sure" threshold fitted on dev
  task     one temperature per task, fitted on that task's dev items (what assay did before)
  pooled   one temperature for all tasks, fitted on every task's dev items together
  shrunk   each task's own temperature pulled toward the pooled one, weight n / (n + k) on its own
  bias     task temperature plus one adjustable nudge per answer label (a prototype, see below)

Then a small-data sweep: refit every method on only 20, 30, 50, 80 dev items (and all of them),
many random subsamples each, and see how the test-half calibration error behaves.

    python bench/calib_study.py bench/receipts/v2-von.json bench/receipts/v2-verdict.json --out study.md
"""
from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assay.calibrate import (  # noqa: E402
    FixedTemperatureCalibrator, ShrunkTemperatureCalibrator, TemperatureCalibrator,
    _apply_temperature, _fit_temperature, pooled_temperature,
)
from assay.metrics import accuracy, brier, ece, nll  # noqa: E402

ALPHA = 0.1
SIZES = (20, 30, 50, 80)
METHODS = ("raw", "task", "pooled", "shrunk", "bias")
METHOD_NOTE = {
    "raw": "no temperature (T = 1)",
    "task": "own temperature per task",
    "pooled": "one shared temperature",
    "shrunk": "own temperature pulled toward the shared one",
    "bias": "own temperature plus a nudge per answer label",
}


# ---------------------------------------------------------------------------------------------------
# the prototype that only ships if it wins: temperature plus a per-label bias
# ---------------------------------------------------------------------------------------------------
class _BiasCalibrator(TemperatureCalibrator):
    """Temperature, then a small additive nudge on each label's log-score, kept small by a ridge penalty."""

    def __init__(self, lam: float = 0.05) -> None:
        super().__init__()
        self.lam = lam
        self.bias: dict[str, float] = {}

    def _pick_temperature(self, samples: list[dict]) -> float:
        t = _fit_temperature(samples)
        labels = sorted({k for s in samples for k in s["probs"]})
        b = {k: 0.0 for k in labels}
        n = len(samples)
        for _ in range(300):
            grad = {k: self.lam * b[k] for k in labels}
            for s in samples:
                q = self._softmax(s["probs"], t, b)
                for k in labels:
                    grad[k] += (q[k] - (1.0 if k == s["truth"] else 0.0)) / n
            for k in labels:
                b[k] -= 0.5 * grad[k]
        self.bias = b
        return t

    @staticmethod
    def _softmax(probs: dict[str, float], t: float, bias: dict[str, float]) -> dict[str, float]:
        z = {k: math.log(max(p, 1e-12)) / t + bias.get(k, 0.0) for k, p in probs.items()}
        m = max(z.values())
        e = {k: math.exp(v - m) for k, v in z.items()}
        tot = sum(e.values())
        return {k: v / tot for k, v in e.items()}

    def _scaled(self, sample: dict) -> dict:
        return {"probs": self._softmax(sample["probs"], self.temperature, self.bias), "truth": sample["truth"]}

    def transform(self, probs: dict[str, float]) -> dict[str, float]:
        return self._softmax(probs, self.temperature, self.bias) if self.fitted else dict(probs)


# ---------------------------------------------------------------------------------------------------
# fitting and grading
# ---------------------------------------------------------------------------------------------------
def make_calibrators(dev_by_task: dict[str, list[dict]], k: float) -> dict[str, dict[str, TemperatureCalibrator]]:
    """Fit every method for every task using only the dev samples handed in."""
    pooled_t = pooled_temperature(dev_by_task)
    out: dict[str, dict[str, TemperatureCalibrator]] = {}
    for task, dev in dev_by_task.items():
        out[task] = {
            "raw": FixedTemperatureCalibrator(1.0).fit(dev, ALPHA),
            "task": TemperatureCalibrator().fit(dev, ALPHA),
            "pooled": FixedTemperatureCalibrator(pooled_t).fit(dev, ALPHA),
            "shrunk": ShrunkTemperatureCalibrator(pooled_t, k).fit(dev, ALPHA),
            "bias": _BiasCalibrator().fit(dev, ALPHA),
        }
    return out


def grade(cal: TemperatureCalibrator, test: list[dict]) -> dict:
    scaled = [{"probs": cal.transform(s["probs"]), "truth": s["truth"]} for s in test]
    sets = [cal.prediction_set(s["probs"]) for s in scaled]
    return {
        "T": cal.temperature,
        "ece": ece(scaled), "brier": brier(scaled), "nll": nll(scaled), "acc": accuracy(scaled),
        "cov": sum(1 for s, ps in zip(test, sets) if s["truth"] in ps) / len(test),
        "size": sum(len(ps) for ps in sets) / len(sets),
        "abstain": sum(1 for ps in sets if len(ps) > 1) / len(sets),
    }


def load(path: str) -> tuple[dict, dict[str, list[dict]], dict[str, list[dict]]]:
    r = json.loads(Path(path).read_text())
    dev: dict[str, list[dict]] = {}
    test: dict[str, list[dict]] = {}
    for name, t in r["tasks"].items():
        rows = [{"probs": i["shuffled"]["probs"], "truth": i["truth"], "split": i["split"]} for i in t["items"]]
        dev[name] = [{"probs": x["probs"], "truth": x["truth"]} for x in rows if x["split"] == "dev"]
        test[name] = [{"probs": x["probs"], "truth": x["truth"]} for x in rows if x["split"] == "test"]
    return r, dev, test


# ---------------------------------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------------------------------
def _f(x: float, d: int = 3) -> str:
    return f"{x:.{d}f}"


def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def headline(dev, test, k) -> list[str]:
    cals = make_calibrators(dev, k)
    res = {t: {m: grade(cals[t][m], test[t]) for m in METHODS} for t in dev}
    L = ["| Task | Method | Temp | ECE | Brier | NLL | Accuracy | Coverage (target 90%) | Avg set size | Abstain |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for t in dev:
        for m in METHODS:
            g = res[t][m]
            L.append(f"| {t} (dev {len(dev[t])}, test {len(test[t])}) | {m} | {_f(g['T'], 2)} | {_f(g['ece'])} | {_f(g['brier'])} | "
                     f"{_f(g['nll'])} | {_pct(g['acc'])} | {_pct(g['cov'])} | {_f(g['size'], 2)} | {_pct(g['abstain'])} |")
    for m in METHODS:
        avg = {key: statistics.mean(res[t][m][key] for t in dev) for key in ("T", "ece", "brier", "nll", "acc", "cov", "size", "abstain")}
        L.append(f"| **average over tasks** | {m} | {_f(avg['T'], 2)} | {_f(avg['ece'])} | {_f(avg['brier'])} | {_f(avg['nll'])} | "
                 f"{_pct(avg['acc'])} | {_pct(avg['cov'])} | {_f(avg['size'], 2)} | {_pct(avg['abstain'])} |")
    # wins against raw, per task
    L += ["", "Tasks where the method beat raw (lower ECE / lower NLL), out of " + str(len(dev)) + ":", "",
          "| Method | ECE better | NLL better |", "|---|---|---|"]
    for m in METHODS[1:]:
        e = sum(1 for t in dev if res[t][m]["ece"] < res[t]["raw"]["ece"])
        n = sum(1 for t in dev if res[t][m]["nll"] < res[t]["raw"]["nll"])
        L.append(f"| {m} | {e} | {n} |")
    return L


def sweep(dev, test, k, reps: int, seed: int) -> list[str]:
    tasks = list(dev)
    sizes = [s for s in SIZES if all(s < len(dev[t]) for t in tasks)] + ["all"]
    # results[size][task][method] -> list of grade dicts
    results: dict = {sz: {t: {m: [] for m in METHODS} for t in tasks} for sz in sizes}
    for sz in sizes:
        n_rep = 1 if sz == "all" else reps
        for rep in range(n_rep):
            sub = {}
            for ti, t in enumerate(tasks):
                if sz == "all":
                    sub[t] = dev[t]
                else:
                    rng = random.Random(f"{seed}-{sz}-{rep}-{ti}")
                    sub[t] = rng.sample(dev[t], sz)
            cals = make_calibrators(sub, k)
            for t in tasks:
                for m in METHODS:
                    results[sz][t][m].append(grade(cals[t][m], test[t]))

    def cell(vals: list[float]) -> str:
        return f"{statistics.mean(vals):.3f} ± {statistics.pstdev(vals):.3f}" if len(vals) > 1 else f"{vals[0]:.3f}"

    L: list[str] = []
    L += ["Test-half ECE (mean ± spread over random dev subsamples; lower is better; 'all' is one fit so no spread):", ""]
    head = "| Task | Dev items used | " + " | ".join(METHODS) + " |"
    L += [head, "|" + "---|" * (len(METHODS) + 2)]
    for t in tasks:
        for sz in sizes:
            L.append(f"| {t} | {sz if sz != 'all' else 'all (' + str(len(dev[t])) + ')'} | " +
                     " | ".join(cell([g["ece"] for g in results[sz][t][m]]) for m in METHODS) + " |")
    L += ["", "Average over tasks (each cell: mean over subsamples of the task average; ± is the spread of that average):", ""]
    for key, label, fmt in (("ece", "ECE", "{:.3f}"), ("nll", "NLL", "{:.3f}"), ("cov", "Conformal coverage (target 90%)", "{:.1%}"),
                            ("size", "Average set size", "{:.2f}")):
        L += [f"**{label}**", "", "| Dev items per task | " + " | ".join(METHODS) + " |", "|" + "---|" * (len(METHODS) + 1)]
        for sz in sizes:
            row = []
            for m in METHODS:
                n_rep = len(results[sz][tasks[0]][m])
                per_rep = [statistics.mean(results[sz][t][m][r][key] for t in tasks) for r in range(n_rep)]
                mu, sd = statistics.mean(per_rep), (statistics.pstdev(per_rep) if n_rep > 1 else None)
                row.append(fmt.format(mu) + (f" ± {fmt.format(sd)}" if sd is not None else ""))
            L.append(f"| {sz if sz != 'all' else 'all'} | " + " | ".join(row) + " |")
        L.append("")
    L += ["How often each method beat 'task' on test ECE and on test NLL (same subsample, every task and every draw counted):", "",
          "| Dev items per task | pooled ECE | shrunk ECE | pooled NLL | shrunk NLL | raw ECE | raw NLL |", "|---|---|---|---|---|---|---|"]
    for sz in sizes:
        def rate(m: str, key: str) -> str:
            wins = tot = 0
            for t in tasks:
                for a, b in zip(results[sz][t][m], results[sz][t]["task"]):
                    tot += 1
                    wins += 1 if a[key] < b[key] else 0
            return _pct(wins / tot)
        L.append(f"| {sz} | {rate('pooled', 'ece')} | {rate('shrunk', 'ece')} | {rate('pooled', 'nll')} | {rate('shrunk', 'nll')} | "
                 f"{rate('raw', 'ece')} | {rate('raw', 'nll')} |")
    return L


def build(paths: list[str], k: float, reps: int, seed: int) -> str:
    L = ["# Calibration study output", "",
         f"Conformal target coverage {_pct(1 - ALPHA)}. Shrinkage constant k = {k:g}. {reps} random subsamples per size, seed {seed}. "
         "Every method is fitted on the dev half only and graded on the test half only.", "",
         "Methods: " + "; ".join(f"**{m}** = {METHOD_NOTE[m]}" for m in METHODS) + ".", ""]
    for p in paths:
        r, dev, test = load(p)
        cfg = r["config"]
        L += [f"## {Path(p).name} (backend {cfg.get('backend')}, model {cfg.get('model')})", "", "### Test-half results, fitted on all dev items", ""]
        L += headline(dev, test, k)
        L += ["", "### Small-data sweep", ""]
        L += sweep(dev, test, k, reps, seed)
        L += [""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compare calibration methods on saved receipts (offline, dev fits, test grades).")
    ap.add_argument("receipts", nargs="+")
    ap.add_argument("--out", default=None, help="write the markdown here as well as to stdout")
    ap.add_argument("--k", type=float, default=30.0, help="shrinkage constant")
    ap.add_argument("--reps", type=int, default=20, help="random subsamples per size")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)
    md = build(args.receipts, args.k, args.reps, args.seed)
    print(md)
    if args.out:
        Path(args.out).write_text(md + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
