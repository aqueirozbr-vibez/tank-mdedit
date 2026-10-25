# 1 — text buffer

risk: risk:low

## Outcome

The editor keeps the document in a `TextBuffer` (module `mdedit.buffer`) that
edits text by character offset and converts between offsets and 1-based line
and column positions.

## Scope

- mdedit/buffer.py
- tests/unit/test_buffer.py

## Non-goals

- Any change outside the two files in Scope.
- Undo history, rendering, search, or reading and writing files.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN `TextBuffer("ab").insert(1, "X")` is called THE SYSTEM SHALL make the
   buffer's `text` property equal `"aXb"`; `TextBuffer()` SHALL start empty.
2. WHEN `delete(start, end)` is called with `0 <= start <= end <= len(text)`
   THE SYSTEM SHALL remove `text[start:end]` and return the removed string.
3. WHEN `replace(start, end, s)` is called with a valid range THE SYSTEM SHALL
   put `s` in place of `text[start:end]` and return the replaced string.
4. WHEN `insert`, `delete` or `replace` receives an offset below 0 or above
   `len(text)`, or a range with `start > end`, THE SYSTEM SHALL raise
   `IndexError` and leave `text` unchanged.
5. WHEN `position_of(offset)` is called on the text `"ab\ncd"` THE SYSTEM SHALL
   return 1-based `(line, column)` tuples: `(1, 1)` for offset 0, `(1, 3)` for
   offset 2, `(2, 1)` for offset 3 and `(2, 3)` for offset 5; an offset below 0
   or above `len(text)` SHALL raise `IndexError`.
6. WHEN `offset_of(line, column)` is called with a tuple that `position_of`
   returned THE SYSTEM SHALL return the original offset; a line outside
   `1..line_count` or a column outside `1..len(line) + 1` SHALL raise
   `IndexError`.
7. WHEN `line_count` is read THE SYSTEM SHALL return the number of `"\n"`
   characters plus one (`1` for `""`, `2` for `"a\n"`), and `line(n)` SHALL
   return line `n` (1-based) without its newline, raising `IndexError` outside
   `1..line_count`.

## Constraints

Standard library only. `"\n"` is the only line separator. The code passes
`mypy --strict` and ruff with the repository's settings.

## Open questions

None.

## Test plan

- AC1 to AC7 -> tests/acceptance/test_1_buffer.py
- AC1 to AC7 unit -> tests/unit/test_buffer.py
