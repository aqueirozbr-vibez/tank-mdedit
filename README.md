# mdedit

A small text editor core with a markdown preview, written by the SENNO software
factory from hand-written specs (phase 1: spec to green branch, builder on
Claude Code).

- `specs/` holds one spec per task; each names its files, its acceptance
  criteria and the unit tests the builder must write.
- `tests/acceptance/` is the holdout. Humans write it; the factory's builder
  may not change it. The acceptance tests for these specs are kept outside
  the repository until a branch is evaluated.
- Standard library only. Python 3.12, ruff, mypy strict, pytest.

Planned modules: `buffer` (text by offset and line/column), `history`
(undo/redo), `inline` and `blocks` (markdown to HTML), `search` (find and
replace) and `stats` (word count, reading time, outline). An editor session
and command-line entry point that tie them together come after these merge.
