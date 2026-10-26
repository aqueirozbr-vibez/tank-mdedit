# 3 — Inline markdown

risk: risk:high

## Outcome

The preview turns the inline markdown of one block of text into safe HTML
through `render_inline(text: str) -> str` in the module `mdedit.inline`.

## Scope

- mdedit/inline.py
- tests/unit/test_inline.py

## Non-goals

- Any change outside the two files in Scope.
- Block structure (headings, lists, code blocks), images, raw HTML passthrough, autolinks and reference-style links.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN the text contains `&`, `<`, `>` or `"` outside markup THE SYSTEM SHALL output `&amp;`, `&lt;`, `&gt;` and `&quot;` respectively, and SHALL otherwise return plain text unchanged.
2. WHEN the text contains `**word**` THE SYSTEM SHALL output `<strong>word</strong>`.
3. WHEN the text contains `*word*` or `_word_` THE SYSTEM SHALL output `<em>word</em>`, SHALL render `**a *b* c**` as `<strong>a <em>b</em> c</strong>`, and SHALL keep an underscore between two letters or digits (as in `snake_case_name`) literal.
4. WHEN the text contains `` `x < y` `` THE SYSTEM SHALL output `<code>x &lt; y</code>`, and SHALL NOT render any emphasis or link markup inside a code span.
5. WHEN the text contains `[label](https://example.com/a?b=1&c=2)` THE SYSTEM SHALL output `<a href="https://example.com/a?b=1&amp;c=2">label</a>`, with emphasis inside the label rendered.
6. WHEN a link's URL has a scheme other than `http`, `https` or `mailto` (compared case-insensitively, for example `javascript:` or `JavaScript:`) THE SYSTEM SHALL output only the label, escaped, with no `<a>` element; a URL without a scheme, such as `notes.md`, SHALL stay a link.
7. WHEN a markup character is preceded by a backslash (`\*`, `\_`, `` \` ``, `\[`, `\]`, or `\\` for the backslash itself) THE SYSTEM SHALL output the character literally and drop the backslash.
8. WHEN an opening marker has no closing marker (`**open`, `*open`, `` `open `` or `[open`) THE SYSTEM SHALL output the marker characters literally.

## Constraints

- No ADR applies.

## Open questions

None.

## Test plan

- AC1 -> tests/acceptance/test_3_inline.py::test_ac1_escaping
- AC1 unit -> tests/unit/test_inline.py::test_escapes_html_special_characters (the builder creates it)
- AC2 -> tests/acceptance/test_3_inline.py::test_ac2_strong
- AC2 unit -> tests/unit/test_inline.py::test_strong (the builder creates it)
- AC3 -> tests/acceptance/test_3_inline.py::test_ac3_emphasis_nesting_and_intraword_underscore
- AC3 unit -> tests/unit/test_inline.py::test_emphasis_nesting_and_intraword_underscore (the builder creates it)
- AC4 -> tests/acceptance/test_3_inline.py::test_ac4_code_span
- AC4 unit -> tests/unit/test_inline.py::test_code_span (the builder creates it)
- AC5 -> tests/acceptance/test_3_inline.py::test_ac5_link
- AC5 unit -> tests/unit/test_inline.py::test_link (the builder creates it)
- AC6 -> tests/acceptance/test_3_inline.py::test_ac6_unsafe_schemes
- AC6 unit -> tests/unit/test_inline.py::test_unsafe_schemes (the builder creates it)
- AC7 -> tests/acceptance/test_3_inline.py::test_ac7_backslash_escapes
- AC7 unit -> tests/unit/test_inline.py::test_backslash_escapes (the builder creates it)
- AC8 -> tests/acceptance/test_3_inline.py::test_ac8_unclosed_markers
- AC8 unit -> tests/unit/test_inline.py::test_unclosed_markers (the builder creates it)
