"""Adapter: openJev-verdict (github.com/Heman10x-NGU/openJev-verdict-2.0) as an assay Backend.

Uses the project's own `core.engine_encoder.DecisionEngine` with its published checkpoint
`heman10x/rlcd-modernbert-151m` (151M parameters, GLiClass ModernBERT-base, safetensors), on CPU, inside its own venv.
NOTE: the "Verdict 2.0" model.pt in the repo is a Git-LFS pointer and the HF repo named in the README does not exist, so the
only obtainable weights are this GLiClass checkpoint, which the repo's own engine and calibrator.json drive.

Mapping of assay's question types onto the project's native ones
  choice  -> Choice: each label is an option whose description is the label; the engine phrases it "It is <label>".
  score   -> Score: one level per label, description = `level_template` (default just the number), numeric value = the
             label's number, shown to the model as "<description> (Value: n)". Built with model_construct because the
             project insists that level values increase in the order given, which assay's shuffled orders break.
  noul    -> Noul: the proposition is assay's instruction text VERBATIM. The project phrases the labels "true: <p>" and
             "false: not <p>", which reads awkwardly when <p> is a question. That is a mapping compromise.
The engine adds a third candidate, "insufficient evidence". Its mass is DROPPED and only the substantive options are
returned (assay softmaxes them again); the dropped mass is kept in `abstain_mass`. Probabilities are the engine's calibrated
ones (per-k temperature from calibrator.json).

Order handling: the model reads the options as a packed list and is NOT order invariant (the project reports a 4.8% flip
rate), so assay's shuffling is doing real work here.

Length limits: the engine truncates the whole prompt to 512 tokens, from the END, so a long STATE loses its tail while the
options and question (which come first) survive. The adapter does not change the state; `truncated_items` counts the calls
where the prompt exceeded 512 tokens and so was cut by the engine. At most 24 options are supported.
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _subproc import WorkerBackend, smoke_main
else:
    from ._subproc import WorkerBackend, smoke_main


class VerdictBackend(WorkerBackend):
    name = "openjev-verdict"
    repo_dir = "openJev-verdict-2.0"
    worker_file = "verdict_worker.py"


if __name__ == "__main__":
    smoke_main(VerdictBackend)
