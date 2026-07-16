---
name: pleskdistup-lint
description: Run flake8 and mypy linters against the pleskdistup / centos2alma codebase. Use when the user asks to lint, type-check, run flake8, or run mypy, or wants a full sweep before commit. A PostToolUse hook already auto-lints individual files after every Edit/Write — invoke this skill for batch / full-tree checks. Examples - "run the linters", "lint the whole repo", "type-check", "check with flake8 before I commit".
---

# pleskdistup-lint

Lint and type-check the codebase.

A `PostToolUse` hook at `.github/hooks/lint-after-edit.sh` runs `flake8` and `mypy` on every Python file you Edit or Write, so per-file checks happen automatically. Invoke this skill manually for **batch runs across the whole tree** (e.g. before a commit, or to catch cross-file mypy issues the single-file hook misses).

## flake8 (matches CI)

CI ignores `E501` (line length); star imports (`F401`/`F403`) are allowed only in `__init__.py`; `*.defs.py` Buck helpers are excluded.

```sh
# From dist-upgrader/:
cd dist-upgrader
flake8 --extend-ignore=E501 \
  --per-file-ignores='pleskdistup/__init__.py:F401,F403 pleskdistup/*/__init__.py:F401,F403' \
  --extend-exclude '*.defs.py'
```

## mypy — full package check (from dist-upgrader/)

Two passes: package code, then `common/tests` separately (their layout uses `src` as the package root).

```sh
cd dist-upgrader
mypy --exclude pleskdistup/common/tests --package pleskdistup
MYPYPATH=pleskdistup/common mypy --explicit-package-bases pleskdistup/common/tests
```

## mypy — quick check from centos2alma root

```sh
mypy dist-upgrader/
```

## Hook behavior

The auto-lint hook:
- only runs on `*.py` files (skips `*.defs.py`)
- exits with code 2 and surfaces stderr back to Claude when either tool finds errors
- silently skips if `flake8` / `mypy` aren't installed
