# 1 — Text buffer

risk: risk:high

## Outcome

The editor keeps the document in a `TextBuffer` (module `mdedit.buffer`) that edits text by
character offset and converts between character offsets and 1-based `(line, column)` positions.

## Scope

- mdedit/buffer.py
- tests/unit/test_buffer.py

## Non-goals

- Any change outside the two files in Scope.
- Undo history, rendering, search, or reading and writing files.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN `TextBuffer("ab").insert(1, "X")` is called THE SYSTEM SHALL make the buffer's `text` property equal `"aXb"`, and WHEN `TextBuffer()` is constructed with no argument THE SYSTEM SHALL start with `text` equal to `""`.
2. WHEN `delete(start, end)` is called with `0 <= start <= end <= len(text)` THE SYSTEM SHALL remove `text[start:end]` from the buffer and return the removed string.
3. WHEN `replace(start, end, s)` is called with `0 <= start <= end <= len(text)` THE SYSTEM SHALL put `s` in place of `text[start:end]` and return the replaced (previous) string.
4. WHEN `insert`, `delete` or `replace` receives an offset below 0 or above `len(text)`, or a range with `start > end`, THE SYSTEM SHALL raise `IndexError` and leave `text` unchanged.
5. WHEN `position_of(offset)` is called on the text `"ab\ncd"` THE SYSTEM SHALL return 1-based `(line, column)` tuples: `(1, 1)` for offset 0, `(1, 3)` for offset 2, `(2, 1)` for offset 3 and `(2, 3)` for offset 5; and WHEN the offset is below 0 or above `len(text)` THE SYSTEM SHALL raise `IndexError`.
6. WHEN `offset_of(line, column)` is called with a tuple that `position_of` returned THE SYSTEM SHALL return the original offset; and WHEN the line is outside `1..line_count` or the column is outside `1..len(line) + 1` THE SYSTEM SHALL raise `IndexError`.
7. WHEN `line_count` is read THE SYSTEM SHALL return the number of `"\n"` characters in `text` plus one (`1` for `""`, `2` for `"a\n"`); and WHEN `line(n)` is called THE SYSTEM SHALL return line `n` (1-based) without its newline, raising `IndexError` for `n` outside `1..line_count`.

## Constraints

- No ADR applies.

## Open questions

None.

## Test plan

- AC1 -> tests/acceptance/test_1_buffer.py::test_ac1_insert_and_empty_start
- AC1 unit -> tests/unit/test_buffer.py::test_insert_and_empty_start (the builder creates it)
- AC2 -> tests/acceptance/test_1_buffer.py::test_ac2_delete_returns_removed
- AC2 unit -> tests/unit/test_buffer.py::test_delete_returns_removed (the builder creates it)
- AC3 -> tests/acceptance/test_1_buffer.py::test_ac3_replace_returns_replaced
- AC3 unit -> tests/unit/test_buffer.py::test_replace_returns_replaced (the builder creates it)
- AC4 -> tests/acceptance/test_1_buffer.py::test_ac4_bad_offsets_raise_and_leave_text
- AC4 unit -> tests/unit/test_buffer.py::test_bad_offsets_raise_and_leave_text (the builder creates it)
- AC5 -> tests/acceptance/test_1_buffer.py::test_ac5_position_of
- AC5 unit -> tests/unit/test_buffer.py::test_position_of (the builder creates it)
- AC6 -> tests/acceptance/test_1_buffer.py::test_ac6_offset_of_round_trip_and_bounds
- AC6 unit -> tests/unit/test_buffer.py::test_offset_of_round_trip_and_bounds (the builder creates it)
- AC7 -> tests/acceptance/test_1_buffer.py::test_ac7_line_count_and_line
- AC7 unit -> tests/unit/test_buffer.py::test_line_count_and_line (the builder creates it)
