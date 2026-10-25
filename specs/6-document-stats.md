# 6 — document statistics

risk: risk:low

## Outcome

The editor's status bar shows document statistics computed in module
`mdedit.stats`: `word_count(text) -> int`, `char_count(text, *, spaces=True)
-> int`, `reading_minutes(text, *, wpm=200) -> int` and
`outline(text) -> list[tuple[int, str]]`.

## Scope

- mdedit/stats.py
- tests/unit/test_stats.py

## Non-goals

- Any change outside the two files in Scope.
- Rendering, sentence or paragraph counts, and languages without spaces
  between words.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN `word_count` is called THE SYSTEM SHALL count runs of letters or
   digits, where an apostrophe or hyphen between two such characters joins
   them into one word; markdown punctuation is not a word, and
   `word_count("# Hello, *world*!\n\nIt's a well-known [link](https://x.org/a-b).")`
   is `6`.
2. WHEN the text contains a link `[label](url)` THE SYSTEM SHALL count the
   words of the label and not those of the URL.
3. WHEN the text contains a fenced code block (lines between two lines that
   start with three backticks) THE SYSTEM SHALL count none of its words in
   `word_count` or its headings in `outline`.
4. WHEN `char_count(text)` is called THE SYSTEM SHALL count every character
   except newlines, so `char_count("a b\nc")` is `4`; with `spaces=False` it
   SHALL also leave out every other whitespace character, so the same text
   gives `3`.
5. WHEN `reading_minutes(text)` is called THE SYSTEM SHALL return
   `ceil(word_count(text) / wpm)`, which is `0` for text without words and `2`
   for 201 words at the default 200; a `wpm` below 1 SHALL raise `ValueError`.
6. WHEN `outline(text)` is called THE SYSTEM SHALL return `(level, title)` for
   every line of 1 to 6 `#` characters followed by a space, in order, with the
   title stripped of surrounding whitespace and of trailing `#` characters:
   `outline("# A\n```\n# not\n```\n## B ##")` is `[(1, "A"), (2, "B")]`.

## Constraints

Standard library only. The code passes `mypy --strict` and ruff with the
repository's settings.

## Open questions

None.

## Test plan

- AC1 to AC6 -> tests/acceptance/test_6_stats.py
- AC1 to AC6 unit -> tests/unit/test_stats.py
