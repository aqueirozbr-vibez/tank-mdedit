"""Render the inline markdown of one block of text as safe HTML.

The supported subset is backslash escapes, code spans, ``*`` and ``_``
emphasis and strong emphasis, and inline links ``[label](url)``. The rules
follow CommonMark's inline algorithm for that subset. Everything else is text,
and every piece of text that reaches the output is HTML-escaped.
"""

import re
import unicodedata
from dataclasses import dataclass

__all__ = ["render_inline"]

# Characters a backslash makes literal. Inside a link destination the
# parentheses can be escaped as well, so a URL can hold an unbalanced one.
_ESCAPABLE = frozenset("\\`*_[]")
_URL_ESCAPABLE = _ESCAPABLE | frozenset("()")
_URL_ESCAPE = re.compile(r"\\([" + re.escape("".join(sorted(_URL_ESCAPABLE))) + "])")

# Characters that may start inline markup; everything between them is text.
_SPECIAL = re.compile(r"[\\`*_\[\]]")
_BACKTICK_RUN = re.compile(r"`+")

_SAFE_SCHEMES = frozenset({"http", "https", "mailto"})
# A URL scheme as the WHATWG URL parser reads it: an ASCII letter, then ASCII
# letters, digits, "+", "-" or ".", ended by a colon.
_SCHEME = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*:", re.ASCII)
# Before it reads the scheme, a browser strips C0 controls and spaces from both
# ends of a URL and removes every tab and newline inside it.
_C0_CONTROL_OR_SPACE = "".join(chr(code) for code in range(0x21))
_REMOVE_TAB_AND_NEWLINE = str.maketrans("", "", "\t\n\r")


def render_inline(text: str) -> str:
    """Render the inline markdown in ``text`` as HTML that is safe to embed."""
    return _InlineParser(text).parse()


@dataclass
class _Delimiter:
    """A run of ``*`` or ``_`` characters that may open or close emphasis."""

    char: str
    count: int  # characters of the run not yet used by emphasis
    length: int  # length of the whole run, for the rule of three
    can_open: bool
    can_close: bool


# Parsed inline content: rendered HTML, or a delimiter run that is paired once
# the content it belongs to (a link label or the whole text) is complete.
type _Token = str | _Delimiter


@dataclass
class _Opener:
    """A delimiter run waiting for a closer, and the HTML that follows it."""

    delimiter: _Delimiter
    parts: list[str]


class _InlineParser:
    """Scan one block of text left to right into tokens, then pair emphasis."""

    def __init__(self, text: str) -> None:
        self._text = text
        self._tokens: list[_Token] = []
        self._pending: list[str] = []  # literal text not yet escaped into a token
        self._brackets: list[int] = []  # token index of each "[" that may start a link
        self._first_active_bracket = 0  # brackets below this index may not start a link
        self._unclosed_runs: set[int] = set()  # backtick run lengths with no closer ahead
        self._destinations = _Destinations(text)

    def parse(self) -> str:
        text = self._text
        pos = 0
        while (match := _SPECIAL.search(text, pos)) is not None:
            start = match.start()
            self._pending.append(text[pos:start])
            char = text[start]
            if char == "\\":
                pos = self._backslash(start)
            elif char == "`":
                pos = self._code_span(start)
            elif char == "[":
                pos = self._open_bracket(start)
            elif char == "]":
                pos = self._close_bracket(start)
            else:
                pos = self._delimiter_run(start)
        self._pending.append(text[pos:])
        self._flush()
        return _render_emphasis(self._tokens)

    def _flush(self) -> None:
        literal = "".join(self._pending)
        self._pending.clear()
        if literal:
            self._tokens.append(_escape(literal))

    def _backslash(self, start: int) -> int:
        text = self._text
        if start + 1 < len(text) and text[start + 1] in _ESCAPABLE:
            self._pending.append(text[start + 1])
            return start + 2
        self._pending.append("\\")
        return start + 1

    def _code_span(self, start: int) -> int:
        text = self._text
        end = start
        while end < len(text) and text[end] == "`":
            end += 1
        length = end - start
        if length not in self._unclosed_runs:
            for closing in _BACKTICK_RUN.finditer(text, end):
                if closing.end() - closing.start() == length:
                    content = _code_content(text[end : closing.start()])
                    self._flush()
                    self._tokens.append(f"<code>{_escape(content)}</code>")
                    return closing.end()
            # No run of this length follows here, so none follows any later run.
            self._unclosed_runs.add(length)
        self._pending.append(text[start:end])
        return end

    def _open_bracket(self, start: int) -> int:
        self._flush()
        self._brackets.append(len(self._tokens))
        self._tokens.append("[")
        return start + 1

    def _close_bracket(self, start: int) -> int:
        if not self._brackets:
            self._pending.append("]")
            return start + 1
        index = self._brackets.pop()
        active = len(self._brackets) >= self._first_active_bracket
        self._first_active_bracket = min(self._first_active_bracket, len(self._brackets))
        destination = self._destinations.parse(start + 1) if active else None
        if destination is None:
            # The "[" stays in the tokens as literal text.
            self._pending.append("]")
            return start + 1
        url, end = destination
        self._flush()
        label = _render_emphasis(self._tokens[index + 1 :])
        del self._tokens[index:]
        if _is_safe_url(url):
            self._tokens.append(f'<a href="{_escape(url)}">{label}</a>')
        else:
            self._tokens.append(label)
        # Links may not contain links, so no earlier "[" can start one now.
        self._first_active_bracket = len(self._brackets)
        return end

    def _delimiter_run(self, start: int) -> int:
        text = self._text
        char = text[start]
        end = start
        while end < len(text) and text[end] == char:
            end += 1
        # The start and the end of the text count as whitespace.
        before = text[start - 1] if start > 0 else " "
        after = text[end] if end < len(text) else " "
        before_space, after_space = before.isspace(), after.isspace()
        before_punct, after_punct = _is_punctuation(before), _is_punctuation(after)
        left_flanking = not after_space and (not after_punct or before_space or before_punct)
        right_flanking = not before_space and (not before_punct or after_space or after_punct)
        if char == "*":
            can_open, can_close = left_flanking, right_flanking
        else:
            # An underscore inside a word, as in snake_case_name, is literal.
            can_open = left_flanking and (not right_flanking or before_punct)
            can_close = right_flanking and (not left_flanking or after_punct)
        if not (can_open or can_close):
            self._pending.append(text[start:end])
            return end
        self._flush()
        length = end - start
        self._tokens.append(_Delimiter(char, length, length, can_open, can_close))
        return end


def _render_emphasis(tokens: list[_Token]) -> str:
    """Pair the delimiter runs in ``tokens`` into emphasis and render the result.

    This is CommonMark's "process emphasis" procedure over a stack of potential
    openers: each closer pairs with the nearest compatible opener before it, and
    every delimiter character left unpaired is output as literal text.
    """
    base: list[str] = []
    openers: list[_Opener] = []
    # For each kind of closer, the stack height below which no opener pairs with it.
    floors: dict[tuple[str, bool, int], int] = {}
    for token in tokens:
        if isinstance(token, str):
            (openers[-1].parts if openers else base).append(token)
            continue
        if token.can_close:
            _close(token, openers, base, floors)
        if token.count:
            if token.can_open:
                openers.append(_Opener(token, []))
            else:
                (openers[-1].parts if openers else base).append(token.char * token.count)
    for opener in openers:
        base.append(opener.delimiter.char * opener.delimiter.count)
        base.extend(opener.parts)
    return "".join(base)


def _close(
    closer: _Delimiter,
    openers: list[_Opener],
    base: list[str],
    floors: dict[tuple[str, bool, int], int],
) -> None:
    """Pair ``closer`` with openers on the stack for as long as it has characters left."""
    kind = (closer.char, closer.can_open, closer.length % 3)
    while closer.count:
        floor = floors.get(kind, 0)
        index = len(openers) - 1
        while index >= floor and not _can_pair(openers[index].delimiter, closer):
            index -= 1
        if index < floor:
            floors[kind] = len(openers)
            return
        opener = openers[index]
        # Openers between the pair can no longer be paired: they become text.
        for inner in openers[index + 1 :]:
            opener.parts.append(inner.delimiter.char * inner.delimiter.count)
            opener.parts.extend(inner.parts)
        del openers[index + 1 :]
        used = 2 if opener.delimiter.count >= 2 and closer.count >= 2 else 1
        tag = "strong" if used == 2 else "em"
        opener.delimiter.count -= used
        closer.count -= used
        html = f"<{tag}>{''.join(opener.parts)}</{tag}>"
        if opener.delimiter.count:
            opener.parts = [html]
        else:
            openers.pop()
            (openers[-1].parts if openers else base).append(html)
        for key, height in floors.items():
            floors[key] = min(height, len(openers))


def _can_pair(opener: _Delimiter, closer: _Delimiter) -> bool:
    if opener.char != closer.char:
        return False
    # CommonMark's rule of three: if either run can both open and close, the
    # pair is rejected when the run lengths add up to a multiple of three,
    # unless both lengths are multiples of three.
    if opener.can_close or closer.can_open:
        both_multiples = opener.length % 3 == 0 and closer.length % 3 == 0
        return (opener.length + closer.length) % 3 != 0 or both_multiples
    return True


class _Destinations:
    """Parse the ``(url)`` part of inline links in one text.

    The URL may be surrounded by whitespace, may not contain whitespace or
    control characters, and may contain parentheses only if they are balanced
    or escaped with a backslash. It therefore ends at the first whitespace or
    control character, or at the first ``)`` that takes the parenthesis depth
    below its starting value.

    Rescanning for every ``](`` would take quadratic time on text such as
    ``[](a[](a[](a``. Instead, the parenthesis depths of the whitespace-free
    segment a URL starts in are computed once, together with the next position
    where the depth drops below each position's own depth. Every later URL
    that starts in the same segment is then found in constant time. Calls
    arrive in increasing order of position, so keeping the last segment is
    enough. Reusing it is sound: a URL starts right after ``(`` or whitespace,
    never inside a run of backslashes, so every start reads the same escapes
    and sees the same depth differences.
    """

    def __init__(self, text: str) -> None:
        self._text = text
        self._start = 0  # the segment analysed last is text[_start:_end]
        self._end = -1
        self._depths: list[int] = []  # depth before each position, plus after the last
        self._drops: list[int] = []  # offset of the next lower depth, or len(_depths)

    def parse(self, start: int) -> tuple[str, int] | None:
        """Parse ``(url)`` at ``start`` and return the URL and the index after ``)``."""
        text = self._text
        if start >= len(text) or text[start] != "(":
            return None
        begin = _skip_whitespace(text, start + 1)
        if not self._start <= begin < self._end:
            self._analyse_segment(begin)
        offset = begin - self._start
        drop = self._drops[offset]
        if drop < len(self._depths):
            # The ")" just before the depth drops closes the destination.
            close = self._start + drop - 1
            return _unescape_url(text[begin:close]), close + 1
        if self._depths[-1] != self._depths[offset]:
            return None  # an unbalanced "(" before the segment ends
        after = _skip_whitespace(text, self._end)
        if after < len(text) and text[after] == ")":
            return _unescape_url(text[begin : self._end]), after + 1
        return None

    def _analyse_segment(self, begin: int) -> None:
        text = self._text
        depths: list[int] = []
        depth = 0
        pos = begin
        while pos < len(text) and not _ends_url(text[pos]):
            depths.append(depth)
            if text[pos] == "\\" and pos + 1 < len(text) and text[pos + 1] in _URL_ESCAPABLE:
                depths.append(depth)  # the escaped character does not change the depth
                pos += 2
                continue
            if text[pos] == "(":
                depth += 1
            elif text[pos] == ")":
                depth -= 1
            pos += 1
        depths.append(depth)
        drops = [len(depths)] * len(depths)
        lower: list[int] = []  # offsets after the current one, with increasing depth
        for offset in range(len(depths) - 1, -1, -1):
            while lower and depths[lower[-1]] >= depths[offset]:
                lower.pop()
            if lower:
                drops[offset] = lower[-1]
            lower.append(offset)
        self._start, self._end = begin, pos
        self._depths, self._drops = depths, drops


def _ends_url(char: str) -> bool:
    return char.isspace() or unicodedata.category(char) == "Cc"


def _unescape_url(raw: str) -> str:
    return _URL_ESCAPE.sub(r"\1", raw)


def _skip_whitespace(text: str, pos: int) -> int:
    while pos < len(text) and text[pos].isspace():
        pos += 1
    return pos


def _is_safe_url(url: str) -> bool:
    """Return whether ``url`` is relative or has an allowed scheme.

    The scheme is read the way a browser reads it, so a URL counts as relative
    only if the browser also resolves it as relative.
    """
    cleaned = url.strip(_C0_CONTROL_OR_SPACE).translate(_REMOVE_TAB_AND_NEWLINE)
    scheme = _SCHEME.match(cleaned)
    return scheme is None or scheme.group()[:-1].lower() in _SAFE_SCHEMES


def _code_content(raw: str) -> str:
    """Normalize code span content as CommonMark does.

    Line endings become spaces, and one space is stripped from each end when
    both ends have one and the content is not only spaces.
    """
    content = raw.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    if content.startswith(" ") and content.endswith(" ") and content.strip(" "):
        content = content[1:-1]
    return content


def _is_punctuation(char: str) -> bool:
    """Unicode punctuation or symbol, as CommonMark's flanking rules define it."""
    return unicodedata.category(char)[0] in "PS"


def _escape(text: str) -> str:
    """Escape the characters that are special in HTML text and quoted attributes."""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
