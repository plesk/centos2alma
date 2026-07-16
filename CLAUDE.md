# centos2alma

Conversion tool for **CentOS 7 → AlmaLinux 8** servers running Plesk. It wraps the
AlmaLinux ELevate/leapp modernization framework and adds the Plesk-specific
repository and configuration handling needed for the conversion to succeed.

## Layout

- `dist-upgrader/` is a git submodule holding the generic **pleskdistup** framework
  (the `DistUpgrader` base class, the `ActiveAction`/`CheckAction` primitives, the
  phase/stage engine, and reusable common actions shared across dist-upgraders).
  This is not specific to CentOS→Alma; treat it as an upstream dependency.
- `centos2almaconverter/` — the CentOS 7 → AlmaLinux 8 specialization built on top
  of that framework. This is where all conversion-specific logic lives.
  - `upgrader.py` holds the `Centos2AlmaConverter` subclass. Defines source/target
    distros and, most importantly, **which actions run, grouped into named stages
    and in what order** (`construct_actions`), plus the pre-conversion checks
    (`get_check_actions`) and CLI options (`parse_args`).
  - `actions/` — the conversion-specific `ActiveAction` / `CheckAction`
    implementations (leapp install & config, repository adoption, database
    upgrades, package/service fixups, named/php/perl/postgres handling, etc.).

## What is centos2alma-specific vs. framework

- The **framework** (`dist-upgrader/pleskdistup`) provides the machinery: how
  actions and checks are defined and executed, phases (PREPARE/FINISH), resume
  across reboot, feedback collection, and a library of `common_actions`.
- **centos2alma** decides *what* actually runs for this conversion: the concrete
  action list and its ordering in `construct_actions`, the CentOS→Alma checks in
  `get_check_actions`, and actions that only make sense here (leapp setup, Plesk
  repo adoption, CentOS-vault/EOL handling). Actions come from either
  `centos2alma_actions` (specific) or `common_actions` (from the framework).

## Common tasks

- Adding/removing/reordering a conversion step → edit the `actions_map` stages in
  `construct_actions` (order within a stage is execution order).
- Adding a pre-conversion guard → add a `CheckAction` in `get_check_actions`
  (see the `pleskdistup-checkaction` skill for idioms).
- Adding a CLI flag → wire it in `parse_args` and store it on the converter.

## Dev

- Linting (flake8 + mypy) and unit tests run against the codebase — use the
  `pleskdistup-lint` and `pleskdistup-test` skills.
- The tool is built with Buck (`BUCK`) and shipped as a single zipped binary.
