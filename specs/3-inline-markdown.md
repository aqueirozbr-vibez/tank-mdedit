# 3 — inline markdown

risk: risk:low

## Outcome

The preview turns the inline markdown of one block of text into safe HTML
through `render_inline(text: str) -> str` (module `mdedit.inline`).

## Scope

- mdedit/inline.py
- tests/unit/test_inline.py

## Non-goals

- Any change outside the two files in Scope.
- Block structure (headings, lists, code blocks), images, raw HTML
  passthrough, autolinks and reference-style links.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN the text contains `&`, `<`, `>` or `"` outside markup THE SYSTEM SHALL
   output `&amp;`, `&lt;`, `&gt;` and `&quot;`; plain text is otherwise
   returned unchanged.
2. WHEN the text contains `**word**` THE SYSTEM SHALL output
   `<strong>word</strong>`.
3. WHEN the text contains `*word*` or `_word_` THE SYSTEM SHALL output
   `<em>word</em>`, and `**a *b* c**` SHALL render as
   `<strong>a <em>b</em> c</strong>`; an underscore between two letters or
   digits, as in `snake_case_name`, SHALL stay literal.
4. WHEN the text contains `` `x < y` `` THE SYSTEM SHALL output
   `<code>x &lt; y</code>`, and no emphasis or link markup inside a code span
   SHALL be rendered.
5. WHEN the text contains `[label](https://example.com/a?b=1&c=2)` THE SYSTEM
   SHALL output `<a href="https://example.com/a?b=1&amp;c=2">label</a>`, with
   emphasis inside the label rendered.
6. WHEN a link's URL has a scheme other than `http`, `https` or `mailto`
   (compared case-insensitively, for example `javascript:` or `JavaScript:`)
   THE SYSTEM SHALL output only the label, escaped, with no `<a>` element; a
   URL without a scheme, such as `notes.md`, stays a link.
7. WHEN a markup character is preceded by a backslash (`\*`, `\_`, `` \` ``,
   `\[`, `\]` or `\`) THE SYSTEM SHALL output the character literally and drop
   the backslash.
8. WHEN an opening marker has no closing marker (`**open`, `*open`, `` `open ``
   or `[open`) THE SYSTEM SHALL output the marker characters literally.

## Constraints

Standard library only. The code passes `mypy --strict` and ruff with the
repository's settings.

## Open questions

None.

## Test plan

- AC1 to AC8 -> tests/acceptance/test_3_inline.py
- AC1 to AC8 unit -> tests/unit/test_inline.py
