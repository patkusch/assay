# Working in assay

Fast, local, typed decisions with calibrated confidence. An open take on the System One / Jev idea.

## Run the tests

You need Python 3.11 or newer.

```bash
make test
```

Every test should pass before you start and after you finish.

## Where things are

- `src/`: the code
- `tests/`: the tests
- `examples/`: worked examples
- `docs/`: written documentation
- `bench/`: measurement and benchmark scripts

## Before you commit

- Make sure the tests pass.
- Put changes people will notice in `CHANGELOG.md`.
- Do not put real passwords, keys or private data in test files or examples. Use made-up ones.
