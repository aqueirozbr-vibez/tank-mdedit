# 5 — find and replace

risk: risk:low

## Outcome

The editor finds and replaces text through
`find_all(text, query, *, case_sensitive=True, whole_word=False, regex=False)`
returning a `list[tuple[int, int]]` of `(start, end)` offsets, and
`replace_all(text, query, replacement, *, case_sensitive=True,
whole_word=False, regex=False)` returning `tuple[str, int]` (the new text and
the number of replacements), both in module `mdedit.search`.

## Scope

- mdedit/search.py
- tests/unit/test_search.py

## Non-goals

- Any change outside the two files in Scope.
- Replacing one match at a time, or a search position or cursor.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN `find_all("abcabc", "bc")` is called THE SYSTEM SHALL return
   `[(1, 3), (4, 6)]`.
2. WHEN matches would overlap THE SYSTEM SHALL return them left to right
   without overlap: `find_all("aaaa", "aa")` is `[(0, 2), (2, 4)]`.
3. WHEN `case_sensitive=False` THE SYSTEM SHALL ignore case:
   `find_all("Hello hello", "HELLO", case_sensitive=False)` is
   `[(0, 5), (6, 11)]`.
4. WHEN `whole_word=True` THE SYSTEM SHALL return only matches with no letter,
   digit or underscore immediately before or after them:
   `find_all("cat concat cat.", "cat", whole_word=True)` is `[(0, 3), (11, 14)]`.
5. WHEN `regex=True` THE SYSTEM SHALL treat `query` as a Python regular
   expression and skip zero-length matches:
   `find_all("a1 b22", r"\d+", regex=True)` is `[(1, 2), (4, 6)]`.
6. WHEN `replace_all("abcabc", "bc", "X")` is called THE SYSTEM SHALL return
   `("aXaX", 2)`; with `regex=True` the replacement may use group references,
   so `replace_all("2026-10-25", r"(\d+)-(\d+)-(\d+)", r"\3/\2/\1", regex=True)`
   is `("25/10/2026", 1)`; with `regex=False` the replacement is literal, so
   `replace_all("a", "a", r"\1")` is `("\1", 1)`.
7. WHEN `query` is empty, or `regex=True` and `query` is not a valid regular
   expression, THE SYSTEM SHALL raise `ValueError`.
8. WHEN nothing matches THE SYSTEM SHALL return `[]` from `find_all` and the
   unchanged text with `0` from `replace_all`.

## Constraints

Standard library only. The code passes `mypy --strict` and ruff with the
repository's settings.

## Open questions

None.

## Test plan

- AC1 to AC8 -> tests/acceptance/test_5_search.py
- AC1 to AC8 unit -> tests/unit/test_search.py
