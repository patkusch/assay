"""Adapter: Von 1.2 (github.com/wfzyx/von, weights wfzyx/von on Hugging Face) as an assay Backend.

Von is a 395M-parameter ModernBERT-large that scores every option in ONE forward pass (option markers in a packed
sequence). This adapter calls Von's own `OptionMarkerBackend` inside its own venv via a JSON-lines worker.

Mapping of assay's question types onto Von's native ones
  choice  -> von Choice: criteria = {label: None}; Von then reads the label text itself as the option description.
             Von's probabilities (temperature-calibrated, rounded to 4 decimals) are returned as log-probabilities, floor 1e-9.
  score   -> von Score: one description per level, in the order assay presents them. assay only has the level NUMBER,
             so the description is `level_template` (default just "3"). Von is trained on worded levels, so this is a
             compromise; pass level_template="Level {label} of {levels}" to try worded levels. Von's own probabilities
             are per position, mapped back to labels by position.
  noul    -> von Noul with no criteria (its zero-shot mode, which applies Von's fitted "no-state bias" correction).
             Von returns only P(true); log P(yes)=log p and log P(no)=log(1-p), aligned to the labels.

Order handling: Von 1.2 blocks options from seeing each other and resets their positions, so its scores are order
invariant by construction; assay's option shuffling therefore changes nothing. It still works, it is simply redundant.

Length limits: the context is 8192 tokens. If question + options + state exceed 8000 tokens the STATE is cut (tail dropped)
and `truncated_items` counts how many calls were cut. Question and options are never cut.

Not used: the `.pt` checkpoint is loaded by Von with torch.load(weights_only=True); it was scanned for non-tensor pickle
globals before first use (see the safety review).
"""
from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _subproc import WorkerBackend, smoke_main
else:
    from ._subproc import WorkerBackend, smoke_main


class VonBackend(WorkerBackend):
    name = "von-1.2"
    repo_dir = "von"
    worker_file = "von_worker.py"


if __name__ == "__main__":
    smoke_main(VonBackend)
