# 6 — Document statistics

risk: risk:high

## Outcome

Module `mdedit.stats` provides the document statistics the editor's status bar will show: `word_count(text) -> int`, `char_count(text, *, spaces=True) -> int`, `reading_minutes(text, *, wpm=200) -> int` and `outline(text) -> list[tuple[int, str]]`, each behaving as the acceptance criteria below state.

## Scope

- mdedit/stats.py
- tests/unit/test_stats.py

## Non-goals

- Any change outside the two files in Scope (this includes wiring the functions into the status bar or any other editor module).
- Rendering, sentence or paragraph counts, and languages without spaces between words.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN `word_count` is called THE SYSTEM SHALL count runs of letters or digits, where an apostrophe or hyphen between two such characters joins them into one word; markdown punctuation is not a word, and `word_count("# Hello, *world*!\n\nIt's a well-known [link](https://x.org/a-b).")` is `6`.
2. WHEN the text contains a link `[label](url)` THE SYSTEM SHALL count the words of the label and not those of the URL.
3. WHEN the text contains a fenced code block (lines between two lines that start with three backticks) THE SYSTEM SHALL count none of its words in `word_count` or its headings in `outline`.
4. WHEN `char_count(text)` is called THE SYSTEM SHALL count every character except newlines, so `char_count("a b\nc")` is `4`; with `spaces=False` it SHALL also leave out every other whitespace character, so the same text gives `3`.
5. WHEN `reading_minutes(text)` is called THE SYSTEM SHALL return `ceil(word_count(text) / wpm)`, which is `0` for text without words and `2` for 201 words at the default 200; a `wpm` below 1 SHALL raise `ValueError`.
6. WHEN `outline(text)` is called THE SYSTEM SHALL return `(level, title)` for every line of 1 to 6 `#` characters followed by a space, in order, with the title stripped of surrounding whitespace and of trailing `#` characters: `` outline("# A\n```\n# not\n```\n## B ##") `` is `[(1, "A"), (2, "B")]`.

## Constraints

No ADR applies.

## Open questions

None.

## Test plan

- AC1 -> tests/acceptance/test_6_stats.py::test_ac1_words
- AC1 unit -> tests/unit/test_stats.py::test_word_count_joins_apostrophes_and_hyphens (the builder creates it)
- AC2 -> tests/acceptance/test_6_stats.py::test_ac2_link_label_only
- AC2 unit -> tests/unit/test_stats.py::test_word_count_counts_link_label_not_url (the builder creates it)
- AC3 -> tests/acceptance/test_6_stats.py::test_ac3_fenced_code_ignored
- AC3 unit -> tests/unit/test_stats.py::test_fenced_code_ignored_by_word_count_and_outline (the builder creates it)
- AC4 -> tests/acceptance/test_6_stats.py::test_ac4_chars
- AC4 unit -> tests/unit/test_stats.py::test_char_count_with_and_without_spaces (the builder creates it)
- AC5 -> tests/acceptance/test_6_stats.py::test_ac5_reading_minutes
- AC5 unit -> tests/unit/test_stats.py::test_reading_minutes_rounds_up_and_rejects_low_wpm (the builder creates it)
- AC6 -> tests/acceptance/test_6_stats.py::test_ac6_outline
- AC6 unit -> tests/unit/test_stats.py::test_outline_levels_and_stripped_titles (the builder creates it)
