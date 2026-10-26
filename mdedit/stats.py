"""Document statistics for the editor's status bar.

Standard library only. Every function takes the raw markdown text of the
document and returns a plain value:

- ``word_count``: words of prose, ignoring markdown punctuation, link targets
  and fenced code blocks.
- ``char_count``: characters other than newlines, optionally without any
  whitespace.
- ``reading_minutes``: whole minutes needed to read the words, rounded up.
- ``outline``: the ATX headings ``(level, title)`` outside fenced code blocks.
"""

import re

__all__ = ["char_count", "outline", "reading_minutes", "word_count"]

_FENCE = "```"

# A word is a run of letters or digits; an apostrophe or hyphen (ASCII or the
# typographic forms) between two such characters joins them into one word.
# ``[^\W_]`` is a Unicode letter or digit: ``\w`` without the underscore.
_WORD_RE = re.compile(r"[^\W_]+(?:['\u2019\-\u2010\u2011][^\W_]+)*")

# An inline link or image ``[label](target)``. The label may contain one level
# of balanced brackets (``[see [1]](url)``); nested constructs such as
# ``[![alt](img)](url)`` resolve from the outside in as the substitution
# repeats. The target may contain one level of balanced parentheses and never
# crosses a line break.
_LINK_RE = re.compile(r"\[((?:[^\[\]]|\[[^\[\]]*\])*)\]\((?:[^()\n]|\([^()\n]*\))*\)")

# An ATX heading: 1 to 6 ``#`` at the start of the line followed by a space.
_HEADING_RE = re.compile(r"#{1,6} ")

# A line ends at ``\r\n``, ``\r`` or ``\n``: the same characters ``char_count``
# treats as newlines. Other separators such as a form feed stay inside a line.
_LINE_BREAK_RE = re.compile(r"\r\n|\r|\n")

_NEWLINES = frozenset("\r\n")


def _prose_lines(text: str) -> list[str]:
    """Return the lines of ``text`` that are outside fenced code blocks.

    A fenced code block is a line starting with three backticks, the lines
    after it and the next line starting with three backticks. Both fence lines
    are dropped with the block. An opening fence with no closing fence after it
    does not form a block and stays an ordinary line.
    """
    lines = _LINE_BREAK_RE.split(text)
    kept: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith(_FENCE):
            close = next(
                (j for j in range(i + 1, len(lines)) if lines[j].startswith(_FENCE)),
                None,
            )
            if close is not None:
                i = close + 1
                continue
        kept.append(lines[i])
        i += 1
    return kept


def _replace_links(text: str) -> str:
    """Replace every ``[label](target)`` in ``text`` with its label."""
    while True:
        replaced = _LINK_RE.sub(r"\1", text)
        if replaced == text:
            return text
        text = replaced


def word_count(text: str) -> int:
    """Return the number of words of prose in the markdown ``text``.

    A word is a run of letters or digits; an apostrophe or hyphen between two
    such characters joins them into one word. Markdown punctuation is not a
    word, only the label of a link counts (not its target), and fenced code
    blocks count nothing.
    """
    prose = _replace_links("\n".join(_prose_lines(text)))
    return sum(1 for _ in _WORD_RE.finditer(prose))


def char_count(text: str, *, spaces: bool = True) -> int:
    """Return the number of characters in ``text`` other than newlines.

    With ``spaces=False`` every other whitespace character is left out too.
    A carriage return is part of a line ending and never counts.
    """
    if spaces:
        return sum(1 for ch in text if ch not in _NEWLINES)
    return sum(1 for ch in text if not ch.isspace())


def reading_minutes(text: str, *, wpm: int = 200) -> int:
    """Return ``ceil(word_count(text) / wpm)``, the minutes needed to read.

    Raises ``ValueError`` when ``wpm`` is below 1.
    """
    if wpm < 1:
        raise ValueError(f"wpm must be at least 1, got {wpm!r}")
    return -(-word_count(text) // wpm)


def outline(text: str) -> list[tuple[int, str]]:
    """Return ``(level, title)`` for each heading in ``text``, in order.

    A heading is a line of 1 to 6 ``#`` characters followed by a space,
    outside fenced code blocks. The title is stripped of surrounding
    whitespace and of trailing ``#`` characters.
    """
    headings: list[tuple[int, str]] = []
    for line in _prose_lines(text):
        match = _HEADING_RE.match(line)
        if match is None:
            continue
        level = match.end() - 1
        title = line[match.end() :].strip().rstrip("#").strip()
        headings.append((level, title))
    return headings
