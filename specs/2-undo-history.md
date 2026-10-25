# 2 — undo history

risk: risk:low

## Outcome

The editor can undo and redo changes through a `History` of document
snapshots (module `mdedit.history`) with a bounded depth.

## Scope

- mdedit/history.py
- tests/unit/test_history.py

## Non-goals

- Any change outside the two files in Scope.
- Diffing or merging snapshots; a snapshot is a whole `str`.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN `History("a")` is created THE SYSTEM SHALL report `current == "a"`,
   `can_undo is False` and `can_redo is False`.
2. WHEN `record(state)` is called with a state different from `current` THE
   SYSTEM SHALL make `state` the `current` one, so that `undo()` returns and
   restores the previous state.
3. WHEN `record(state)` is called with a state equal to `current` THE SYSTEM
   SHALL change nothing, including the redo states.
4. WHEN `undo()` is followed by `redo()` THE SYSTEM SHALL return and restore
   the state that was current before the undo.
5. WHEN `record(state)` is called after an `undo()` with a different state THE
   SYSTEM SHALL discard every redo state, so `can_redo` becomes `False`.
6. WHEN `undo()` is called with nothing to undo, or `redo()` with nothing to
   redo, THE SYSTEM SHALL raise `LookupError` and leave `current` unchanged.
7. WHEN `History("s0", limit=3)` has recorded `"s1"` to `"s5"` THE SYSTEM
   SHALL keep only the 3 most recent undo steps: three `undo()` calls return
   `"s4"`, `"s3"` and `"s2"`, and a fourth raises `LookupError`.
8. WHEN `History` is created with `limit` below 1 THE SYSTEM SHALL raise
   `ValueError`; the default `limit` is 100.

## Constraints

Standard library only. The code passes `mypy --strict` and ruff with the
repository's settings.

## Open questions

None.

## Test plan

- AC1 to AC8 -> tests/acceptance/test_2_history.py
- AC1 to AC8 unit -> tests/unit/test_history.py
