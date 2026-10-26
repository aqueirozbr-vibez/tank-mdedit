# 4 — Block markdown

risk: risk:high

## Outcome

The preview turns a markdown document into HTML blocks through
`render_blocks(text: str, inline: Callable[[str], str] | None = None) -> str`
in module `mdedit.blocks`. It renders headings, paragraphs, unordered and
ordered lists, fenced code, blockquotes and horizontal rules. The text inside
headings, paragraphs, list items and quotes goes through `inline`; when
`inline` is `None` that text is escaped with `html.escape(text, quote=True)`.

## Scope

- mdedit/blocks.py
- tests/unit/test_blocks.py

## Non-goals

- Any change outside the two files in Scope.
- Inline markup: `mdedit/blocks.py` must not import `mdedit.inline`; the caller passes the inline renderer.
- Nested lists, setext headings, tables, indented code blocks and raw HTML.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN `render_blocks("# Title\n\nHello\nworld\n\n- a\n- b")` is called THE SYSTEM SHALL return `"<h1>Title</h1>\n<p>Hello world</p>\n<ul>\n<li>a</li>\n<li>b</li>\n</ul>"`: blocks are joined by `"\n"`, there is no trailing newline, blank lines (empty or whitespace only) separate blocks and produce no output, and the lines of a paragraph are stripped and joined by one space. A paragraph is a run of consecutive non-blank lines; a line that starts a heading, list, fenced code block, blockquote or rule under criteria 2 to 6 ends the paragraph and starts that block.
2. WHEN a line starts with 1 to 6 `#` characters followed by a space THE SYSTEM SHALL output `<hN>` with the stripped text after them and `</hN>`, N being the number of `#` characters; a line of 7 `#` characters followed by text is a paragraph.
3. WHEN consecutive lines start with `- ` or `* ` THE SYSTEM SHALL output one `<ul>` with one `<li>` per line holding the text after the marker; consecutive lines starting with digits, `.` and a space SHALL output one `<ol>`, with `<ol start="N">` when the first number N is not 1. The opening tag, each `<li>...</li>` and the closing tag are each on their own line, joined by `"\n"`, as in criterion 1.
4. WHEN a line is three backtick characters optionally followed by a language word THE SYSTEM SHALL output the lines up to the closing three-backtick line as `<pre><code class="language-WORD">...</code></pre>` (or `<pre><code>...</code></pre>` with no language), with the content escaped with `html.escape(..., quote=True)` whether or not `inline` is given, its lines joined by `"\n"`, the fence lines themselves not output, and the content never passed to `inline`; an unclosed fence runs to the end of the text.
5. WHEN consecutive lines start with `>` THE SYSTEM SHALL strip `>` and one following space from each line and output `"<blockquote>\n"` + the stripped lines rendered as blocks by the same rules and with the same `inline` + `"\n</blockquote>"`.
6. WHEN a line consists of three or more `-` characters and nothing else THE SYSTEM SHALL output `<hr>`.
7. WHEN `inline` is given THE SYSTEM SHALL call it with the unescaped text of each heading, each paragraph (its joined text, one call per paragraph), each list item and the blocks inside each quote, and insert its result unescaped; the empty text and text of only blank lines SHALL return `""`.

## Constraints

- No ADR applies.
- The public signature is exactly `render_blocks(text: str, inline: Callable[[str], str] | None = None) -> str` in `mdedit.blocks`.
- `mdedit.blocks` does not import `mdedit.inline`.

## Open questions

None.

## Test plan

- AC1 -> tests/acceptance/test_4_blocks.py::test_ac1_example
- AC1 unit -> tests/unit/test_blocks.py::test_example_document (the builder creates it; also covers a paragraph ended by a heading, list, fence, quote or rule line)
- AC2 -> tests/acceptance/test_4_blocks.py::test_ac2_headings
- AC2 unit -> tests/unit/test_blocks.py::test_headings (the builder creates it; levels 1 to 6, seven `#` is a paragraph)
- AC3 -> tests/acceptance/test_4_blocks.py::test_ac3_lists
- AC3 unit -> tests/unit/test_blocks.py::test_lists (the builder creates it; `-` and `*` items, `<ol>` from 1, `<ol start="N">` otherwise)
- AC4 -> tests/acceptance/test_4_blocks.py::test_ac4_fenced_code
- AC4 unit -> tests/unit/test_blocks.py::test_fenced_code (the builder creates it; with and without language, escaping, `inline` not called, unclosed fence)
- AC5 -> tests/acceptance/test_4_blocks.py::test_ac5_blockquote
- AC5 unit -> tests/unit/test_blocks.py::test_blockquote (the builder creates it; inner blocks rendered, `>` with and without a following space)
- AC6 -> tests/acceptance/test_4_blocks.py::test_ac6_rule
- AC6 unit -> tests/unit/test_blocks.py::test_rule (the builder creates it; three and more `-`, fewer than three is a paragraph)
- AC7 -> tests/acceptance/test_4_blocks.py::test_ac7_inline_hook_and_empty
- AC7 unit -> tests/unit/test_blocks.py::test_inline_hook_and_empty (the builder creates it; result inserted unescaped, default escaping of `<`, `&`, `"` and `'`, empty and blank-only text)
