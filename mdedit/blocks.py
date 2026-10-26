"""Block-level markdown rendering for the preview.

``render_blocks`` turns a markdown document into HTML blocks: headings,
paragraphs, unordered and ordered lists, fenced code, blockquotes and
horizontal rules. Inline markup is not handled here; the caller passes an
inline renderer, and without one the text is HTML-escaped.
"""

import html
import re
from collections.abc import Callable

__all__ = ["render_blocks"]

_HEADING = re.compile(r"(#{1,6}) (.*)")
_UNORDERED_ITEM = re.compile(r"[-*] (.*)")
_ORDERED_ITEM = re.compile(r"([0-9]+)\. (.*)")
# Matched against the line without trailing whitespace.
_FENCE = re.compile(r"``` *([^\s`]*)")
_RULE = re.compile(r"-{3,}")

_CLOSING_FENCE = "```"


def render_blocks(text: str, inline: Callable[[str], str] | None = None) -> str:
    """Render the markdown ``text`` as HTML blocks joined by ``"\n"``.

    The text of headings, paragraphs, list items and quoted blocks goes through
    ``inline``; when ``inline`` is ``None`` it is escaped with
    ``html.escape(text, quote=True)``. Fenced code is always escaped and never
    passed to ``inline``.
    """
    render_inline = inline if inline is not None else _escape
    return "\n".join(_render_lines(_split_lines(text), render_inline))


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def _split_lines(text: str) -> list[str]:
    """Split ``text`` on ``\n``, ``\r\n`` and ``\r``; a final line break ends a line."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if lines[-1] == "":
        lines.pop()
    return lines


def _is_blank(line: str) -> bool:
    return line.strip() == ""


def _starts_block(line: str) -> bool:
    """Whether ``line`` starts a heading, list, fenced code, blockquote or rule."""
    trimmed = line.rstrip()
    return bool(
        _HEADING.match(line)
        or _UNORDERED_ITEM.match(line)
        or _ORDERED_ITEM.match(line)
        or _FENCE.fullmatch(trimmed)
        or line.startswith(">")
        or _RULE.fullmatch(trimmed)
    )


def _render_lines(lines: list[str], inline: Callable[[str], str]) -> list[str]:
    """Render ``lines`` and return one HTML string per block."""
    blocks: list[str] = []
    count = len(lines)
    i = 0
    while i < count:
        line = lines[i]
        trimmed = line.rstrip()

        if _is_blank(line):
            i += 1
            continue

        if heading := _HEADING.match(line):
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{inline(heading.group(2).strip())}</h{level}>")
            i += 1
            continue

        if fence := _FENCE.fullmatch(trimmed):
            i += 1
            code: list[str] = []
            while i < count and lines[i].rstrip() != _CLOSING_FENCE:
                code.append(lines[i])
                i += 1
            i += 1  # Skip the closing fence; an unclosed fence ran to the end.
            language = fence.group(1)
            attribute = f' class="language-{_escape(language)}"' if language else ""
            content = _escape("\n".join(code))
            blocks.append(f"<pre><code{attribute}>{content}</code></pre>")
            continue

        if _RULE.fullmatch(trimmed):
            blocks.append("<hr>")
            i += 1
            continue

        if line.startswith(">"):
            quoted: list[str] = []
            while i < count and lines[i].startswith(">"):
                quoted.append(lines[i][1:].removeprefix(" "))
                i += 1
            inner = "\n".join(_render_lines(quoted, inline))
            blocks.append(f"<blockquote>\n{inner}\n</blockquote>")
            continue

        if _UNORDERED_ITEM.match(line):
            items: list[str] = []
            while i < count and (item := _UNORDERED_ITEM.match(lines[i])):
                items.append(f"<li>{inline(item.group(1).strip())}</li>")
                i += 1
            blocks.append("\n".join(["<ul>", *items, "</ul>"]))
            continue

        if first := _ORDERED_ITEM.match(line):
            # Compare digit strings rather than ints so that no digit run is too long.
            start = first.group(1).lstrip("0") or "0"
            opening = "<ol>" if start == "1" else f'<ol start="{start}">'
            items = []
            while i < count and (item := _ORDERED_ITEM.match(lines[i])):
                items.append(f"<li>{inline(item.group(2).strip())}</li>")
                i += 1
            blocks.append("\n".join([opening, *items, "</ol>"]))
            continue

        paragraph = [line.strip()]
        i += 1
        while i < count and not _is_blank(lines[i]) and not _starts_block(lines[i]):
            paragraph.append(lines[i].strip())
            i += 1
        blocks.append(f"<p>{inline(' '.join(paragraph))}</p>")

    return blocks
