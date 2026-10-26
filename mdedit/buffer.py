"""The editor's document: text edited by character offset.

Offsets are 0-based character indexes into the text and may equal ``len(text)``
(the position just past the last character). Positions are 1-based
``(line, column)`` tuples. Only ``"\n"`` separates lines, so a text with ``k``
newlines has ``k + 1`` lines, and a column may be one past the end of its line.
"""

__all__ = ["TextBuffer"]


class TextBuffer:
    """A mutable piece of text addressed by character offset or line and column."""

    def __init__(self, text: str = "") -> None:
        self._text = text

    @property
    def text(self) -> str:
        """The whole document."""
        return self._text

    @property
    def line_count(self) -> int:
        """The number of ``"\n"`` characters in the text plus one."""
        return self._text.count("\n") + 1

    def insert(self, offset: int, s: str) -> None:
        """Insert ``s`` before the character at ``offset``.

        Raises ``IndexError`` if ``offset`` is outside ``0..len(text)``.
        """
        self._check_offset(offset)
        self._text = self._text[:offset] + s + self._text[offset:]

    def delete(self, start: int, end: int) -> str:
        """Remove ``text[start:end]`` and return the removed string.

        Raises ``IndexError`` unless ``0 <= start <= end <= len(text)``.
        """
        return self.replace(start, end, "")

    def replace(self, start: int, end: int, s: str) -> str:
        """Put ``s`` in place of ``text[start:end]`` and return the previous string.

        Raises ``IndexError`` unless ``0 <= start <= end <= len(text)``.
        """
        self._check_range(start, end)
        removed = self._text[start:end]
        self._text = self._text[:start] + s + self._text[end:]
        return removed

    def position_of(self, offset: int) -> tuple[int, int]:
        """Return the 1-based ``(line, column)`` of ``offset``.

        Raises ``IndexError`` if ``offset`` is outside ``0..len(text)``.
        """
        self._check_offset(offset)
        line = self._text.count("\n", 0, offset) + 1
        line_start = self._text.rfind("\n", 0, offset) + 1
        return line, offset - line_start + 1

    def offset_of(self, line: int, column: int) -> int:
        """Return the offset of the 1-based ``(line, column)`` position.

        Raises ``IndexError`` if ``line`` is outside ``1..line_count`` or
        ``column`` is outside ``1..len(line) + 1``.
        """
        start, end = self._line_span(line)
        if not 1 <= column <= end - start + 1:
            raise IndexError(f"column {column} out of range 1..{end - start + 1} for line {line}")
        return start + column - 1

    def line(self, n: int) -> str:
        """Return line ``n`` (1-based) without its newline.

        Raises ``IndexError`` if ``n`` is outside ``1..line_count``.
        """
        start, end = self._line_span(n)
        return self._text[start:end]

    def _line_span(self, n: int) -> tuple[int, int]:
        """Return the ``(start, end)`` offsets of line ``n``, excluding its newline."""
        count = self.line_count
        if not 1 <= n <= count:
            raise IndexError(f"line {n} out of range 1..{count}")
        start = 0
        for _ in range(n - 1):
            start = self._text.index("\n", start) + 1
        end = self._text.find("\n", start)
        if end == -1:
            end = len(self._text)
        return start, end

    def _check_offset(self, offset: int) -> None:
        if not 0 <= offset <= len(self._text):
            raise IndexError(f"offset {offset} out of range 0..{len(self._text)}")

    def _check_range(self, start: int, end: int) -> None:
        self._check_offset(start)
        self._check_offset(end)
        if start > end:
            raise IndexError(f"range start {start} is after end {end}")
