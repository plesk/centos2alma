---
name: pleskdistup-test
description: Run unit tests for the pleskdistup framework / dist-upgrader / centos2alma. Use whenever the user asks to run, execute, or check tests, or wants to verify a single test case after a change. Examples - "run the tests", "run the unittest suite", "test this change", "rerun test_files", "do the tests still pass".
---

# pleskdistup-test

Test runners for the pleskdistup common library. Tests live in `dist-upgrader/pleskdistup/common/tests/` and use Python's `unittest` with mocked filesystem and command execution.

## Full suite from centos2alma root

```sh
python3 -m unittest discover dist-upgrader/pleskdistup/common/tests/
```

## Full suite via Buck (from dist-upgrader/)

```sh
cd dist-upgrader
buck2 test //pleskdistup/common:libs.tests
```

This is what CI runs. The `python_test` target executes all modules via `tests.test_main`.

## Single test module

```sh
python3 -m unittest pleskdistup.common.tests.test_files
```

## Single test case or method

```sh
python3 -m unittest pleskdistup.common.tests.test_files.TestCase.test_method
```

## Note on test layout

Tests do `from src import ...`, not `from pleskdistup.common.src import ...` — the test layout uses `src` as the package root, which matters if you're authoring new tests.

## What needs coverage

New utilities under `pleskdistup/common/` are expected to ship with tests. Action-level code in `pleskdistup/actions/` and `centos2almaconverter/actions/` is generally tested via the action's own logic; mock external dependencies (files, subprocess) rather than touching the real system.
