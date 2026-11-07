.PHONY: test bench-quick serve example demo handover

PY ?= python3

test:
	PYTHONPATH=src $(PY) -m unittest discover -s tests

# a 20-item-per-split run on the keyword stand-in: proves the plumbing, says nothing about real models
bench-quick:
	PYTHONPATH=src $(PY) bench/run.py --backend keyword --limit 20 --out /tmp/assay-quick.json

serve:
	PYTHONPATH=src $(PY) -m assay serve --model gemma3 --port 8787

example:
	PYTHONPATH=src $(PY) -m assay decide --backend keyword --request examples/support_ticket.json

# rebuild the visual demo page from the saved v2 receipts
demo:
	$(PY) bench/make_demo.py

# rebuild the hand-over tables (small model first, 12B when unsure) from the saved receipts; no model needs to run
handover:
	$(PY) bench/handover.py bench/receipts/v2-gemma3-4b.json bench/receipts/v2-gemma3-12b.json --out bench/receipts/handover-4b-12b
	$(PY) bench/handover.py bench/receipts/v2-gemma3-4b-word.json bench/receipts/v2-gemma3-12b.json --out bench/receipts/handover-4b-word-12b
