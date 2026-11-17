# Adding to assay

- Plain Python, standard library only, so there stays nothing to install.
- Every change comes with a test. `make test` must pass before a push. Never pipe the test output into something that hides a failure.
- A number in the README comes from a receipt in `bench/receipts/`, made by a script in `bench/`, and says how many items it was measured on. A measurement that showed no benefit still goes in.
- Wording is plain English: say what a thing does and why, and put the plain meaning next to every number.
- A new command-line flag is mentioned in the README or `docs/CHOOSING_SETTINGS.md`, with the measurement behind it.
