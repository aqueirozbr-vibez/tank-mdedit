# 2 — Undo history

risk: risk:high

## Outcome

The editor can undo and redo changes through a `History` of whole-document snapshots, provided by the module `mdedit.history`, with a bounded number of undo steps (default 100).

## Scope

- mdedit/history.py
- tests/unit/test_history.py

## Non-goals

- Any change outside the two files in Scope, including other `mdedit` modules, package metadata and dependency files.
- Diffing or merging snapshots; a snapshot is a whole `str`.
- Wiring `History` into any other part of the editor.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN `History("a")` is created THE SYSTEM SHALL report `current == "a"`, `can_undo is False` and `can_redo is False`.
2. WHEN `record(state)` is called with a state different from `current` THE SYSTEM SHALL make `state` the `current` one, so that a following `undo()` returns the previous state and makes it `current` again.
3. WHEN `record(state)` is called with a state equal to `current` THE SYSTEM SHALL change nothing: `current`, the undo states and the redo states (and therefore `can_undo` and `can_redo`) stay as they were.
4. WHEN `undo()` is followed by `redo()` THE SYSTEM SHALL have `redo()` return the state that was `current` before the `undo()` and make it `current` again.
5. WHEN `record(state)` is called after an `undo()` with a state different from `current` THE SYSTEM SHALL discard every redo state, so that `can_redo` becomes `False`.
6. WHEN `undo()` is called with nothing to undo, or `redo()` is called with nothing to redo, THE SYSTEM SHALL raise `LookupError` and leave `current` unchanged.
7. WHEN `History("s0", limit=3)` has recorded `"s1"`, `"s2"`, `"s3"`, `"s4"` and `"s5"` in order THE SYSTEM SHALL keep only the 3 most recent undo steps: three successive `undo()` calls return `"s4"`, `"s3"` and `"s2"`, and a fourth `undo()` raises `LookupError`.
8. WHEN `History` is created with a `limit` below 1 THE SYSTEM SHALL raise `ValueError`, and WHEN `History` is created without a `limit` THE SYSTEM SHALL use a `limit` of 100.

## Constraints

- No ADR applies.

## Open questions

None.

## Test plan

- AC1 -> tests/acceptance/test_2_history.py::test_ac1_fresh_history
- AC1 unit -> tests/unit/test_history.py::test_fresh_history_has_current_and_nothing_to_undo_or_redo (the builder creates it)
- AC2 -> tests/acceptance/test_2_history.py::test_ac2_record_then_undo
- AC2 unit -> tests/unit/test_history.py::test_record_then_undo_restores_previous_state (the builder creates it)
- AC3 -> tests/acceptance/test_2_history.py::test_ac3_recording_the_current_state_changes_nothing
- AC3 unit -> tests/unit/test_history.py::test_record_equal_to_current_keeps_undo_and_redo_states (the builder creates it)
- AC4 -> tests/acceptance/test_2_history.py::test_ac4_undo_then_redo
- AC4 unit -> tests/unit/test_history.py::test_undo_then_redo_restores_state_before_undo (the builder creates it)
- AC5 -> tests/acceptance/test_2_history.py::test_ac5_record_after_undo_drops_redo
- AC5 unit -> tests/unit/test_history.py::test_record_different_state_after_undo_discards_redo (the builder creates it)
- AC6 -> tests/acceptance/test_2_history.py::test_ac6_nothing_to_undo_or_redo
- AC6 unit -> tests/unit/test_history.py::test_undo_or_redo_with_nothing_raises_lookup_error_and_keeps_current (the builder creates it)
- AC7 -> tests/acceptance/test_2_history.py::test_ac7_limit_keeps_the_most_recent_steps
- AC7 unit -> tests/unit/test_history.py::test_limit_keeps_only_most_recent_undo_steps (the builder creates it)
- AC8 -> tests/acceptance/test_2_history.py::test_ac8_limit_validation_and_default
- AC8 unit -> tests/unit/test_history.py::test_limit_below_one_raises_value_error_and_default_is_100 (the builder creates it)
