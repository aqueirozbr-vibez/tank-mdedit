# 4 — block markdown

risk: risk:low

## Outcome

The preview turns a markdown document into HTML blocks through
`render_blocks(text: str, inline: Callable[[str], str] | None = None) -> str`
(module `mdedit.blocks`). The text inside headings, paragraphs, list items
and quotes goes through `inline`; when `inline` is `None` it is escaped with
`html.escape(text, quote=True)`.

## Scope

- mdedit/blocks.py
- tests/unit/test_blocks.py

## Non-goals

- Any change outside the two files in Scope.
- Inline markup: this module must not import `mdedit.inline`; the caller
  passes the inline renderer.
- Nested lists, setext headings, tables, indented code blocks and raw HTML.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN `render_blocks("# Title\n\nHello\nworld\n\n- a\n- b")` is called THE
   SYSTEM SHALL return
   `"<h1>Title</h1>\n<p>Hello world</p>\n<ul>\n<li>a</li>\n<li>b</li>\n</ul>"`:
   blocks are joined by `"\n"`, there is no trailing newline, and the lines
   of a paragraph are stripped and joined by one space.
2. WHEN a line starts with 1 to 6 `#` characters followed by a space THE
   SYSTEM SHALL output `<hN>` with the stripped text; a line of 7 `#`
   characters followed by text is a paragraph.
3. WHEN consecutive lines start with `- ` or `* ` THE SYSTEM SHALL output one
   `<ul>` with one `<li>` per line; consecutive lines starting with digits,
   `.` and a space SHALL output one `<ol>`, with `<ol start="N">` when the
   first number N is not 1.
4. WHEN a line is three backticks optionally followed by a language word THE
   SYSTEM SHALL output the lines up to the closing three-backtick line as
   `<pre><code class="language-WORD">...</code></pre>` (or `<pre><code>` with
   no language), with the content escaped, its lines joined by `"\n"`, and
   never passed to `inline`; an unclosed fence runs to the end of the text.
5. WHEN consecutive lines start with `>` THE SYSTEM SHALL strip `>` and one
   following space and output `<blockquote>\n` + the stripped lines rendered
   as blocks + `\n</blockquote>`.
6. WHEN a line consists of three or more `-` characters and nothing else THE
   SYSTEM SHALL output `<hr>`.
7. WHEN `inline` is given THE SYSTEM SHALL call it for heading, paragraph,
   list item and quote text and insert its result unescaped; the empty text
   and text of only blank lines SHALL return `""`.

## Constraints

Standard library only. The code passes `mypy --strict` and ruff with the
repository's settings.

## Open questions

None.

## Test plan

- AC1 to AC7 -> tests/acceptance/test_4_blocks.py
- AC1 to AC7 unit -> tests/unit/test_blocks.py
