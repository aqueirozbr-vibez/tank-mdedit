# 5 — Find and replace

risk: risk:high

## Outcome

The module `mdedit.search` provides
`find_all(text, query, *, case_sensitive=True, whole_word=False, regex=False)`,
which returns a `list[tuple[int, int]]` of `(start, end)` offsets for every match, and
`replace_all(text, query, replacement, *, case_sensitive=True, whole_word=False, regex=False)`,
which returns a `tuple[str, int]` holding the new text and the number of replacements made.

## Scope

- mdedit/search.py
- tests/unit/test_search.py

## Non-goals

- Any change outside the two files in Scope.
- Replacing one match at a time, or keeping a search position or cursor.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN `find_all("abcabc", "bc")` is called THE SYSTEM SHALL return `[(1, 3), (4, 6)]`.
2. WHEN matches would overlap THE SYSTEM SHALL return them left to right without overlap: `find_all("aaaa", "aa")` returns `[(0, 2), (2, 4)]`.
3. WHEN `case_sensitive=False` THE SYSTEM SHALL ignore case: `find_all("Hello hello", "HELLO", case_sensitive=False)` returns `[(0, 5), (6, 11)]`.
4. WHEN `whole_word=True` THE SYSTEM SHALL return only matches that have no letter, digit or underscore immediately before or after them: `find_all("cat concat cat.", "cat", whole_word=True)` returns `[(0, 3), (11, 14)]`.
5. WHEN `regex=True` THE SYSTEM SHALL treat `query` as a Python regular expression and skip zero-length matches: `find_all("a1 b22", r"\d+", regex=True)` returns `[(1, 2), (4, 6)]`.
6. WHEN `replace_all("abcabc", "bc", "X")` is called THE SYSTEM SHALL return `("aXaX", 2)`; with `regex=True` the replacement may use group references, so `replace_all("2026-10-25", r"(\d+)-(\d+)-(\d+)", r"\3/\2/\1", regex=True)` returns `("25/10/2026", 1)`; with `regex=False` the replacement is literal, so `replace_all("a", "a", r"\1")` returns `(r"\1", 1)`, that is, text made of the two characters backslash and `1`.
7. WHEN `query` is empty, or `regex=True` and `query` is not a valid regular expression, THE SYSTEM SHALL raise `ValueError` from both `find_all` and `replace_all`.
8. WHEN nothing matches THE SYSTEM SHALL return `[]` from `find_all`, and the unchanged text together with `0` from `replace_all`.

## Constraints

- No ADR applies.

## Open questions

None.

## Test plan

- AC1 -> tests/acceptance/test_5_search.py::test_ac1_basic
- AC1 unit -> tests/unit/test_search.py::test_find_all_basic
- AC2 -> tests/acceptance/test_5_search.py::test_ac2_no_overlap
- AC2 unit -> tests/unit/test_search.py::test_find_all_no_overlap
- AC3 -> tests/acceptance/test_5_search.py::test_ac3_case_insensitive
- AC3 unit -> tests/unit/test_search.py::test_find_all_case_insensitive
- AC4 -> tests/acceptance/test_5_search.py::test_ac4_whole_word
- AC4 unit -> tests/unit/test_search.py::test_find_all_whole_word
- AC5 -> tests/acceptance/test_5_search.py::test_ac5_regex_and_zero_length
- AC5 unit -> tests/unit/test_search.py::test_find_all_regex_skips_zero_length
- AC6 -> tests/acceptance/test_5_search.py::test_ac6_replace
- AC6 unit -> tests/unit/test_search.py::test_replace_all_literal_and_group_references
- AC7 -> tests/acceptance/test_5_search.py::test_ac7_bad_queries
- AC7 unit -> tests/unit/test_search.py::test_empty_or_invalid_query_raises_value_error
- AC8 -> tests/acceptance/test_5_search.py::test_ac8_nothing_matches
- AC8 unit -> tests/unit/test_search.py::test_nothing_matches
