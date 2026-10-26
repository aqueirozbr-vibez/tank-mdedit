"""Find and replace over a whole text.

Both functions scan the text left to right and never report overlapping matches.
Offsets are ``(start, end)`` indices into the original text, suitable for slicing.
Zero-length matches, which only a regular expression can produce, are skipped.
"""

import re

__all__ = ["find_all", "replace_all"]

# A word character is a letter, digit or underscore. ``(?u:...)`` pins the Unicode
# meaning of ``\w`` so an inline ``(?a)`` in a user pattern cannot narrow it.
_WORD_CHAR = r"(?u:\w)"
_NO_WORD_BEFORE = rf"(?<!{_WORD_CHAR})"
_NO_WORD_AFTER = rf"(?!{_WORD_CHAR})"

# Global inline flags such as ``(?i)`` must stay at the very start of a pattern, so they
# are split off before the pattern is wrapped for whole-word matching. In verbose mode
# whitespace and comments may sit between them; those are ignored by the parser anyway.
_LEADING_FLAGS = re.compile(r"(?:\(\?[aiLmsux]+\))*")
_LEADING_FLAGS_VERBOSE = re.compile(r"(?:\(\?[aiLmsux]+\)|[ \t\n\r\v\f]+|#[^\n]*\n?)*")


def find_all(
    text: str,
    query: str,
    *,
    case_sensitive: bool = True,
    whole_word: bool = False,
    regex: bool = False,
) -> list[tuple[int, int]]:
    """Return the ``(start, end)`` offsets of every non-overlapping match of ``query``.

    Raises ``ValueError`` if ``query`` is empty, or if ``regex`` is true and ``query``
    is not a valid regular expression.
    """
    pattern = _compile(query, case_sensitive=case_sensitive, whole_word=whole_word, regex=regex)
    return [match.span() for match in _matches(pattern, text)]


def replace_all(
    text: str,
    query: str,
    replacement: str,
    *,
    case_sensitive: bool = True,
    whole_word: bool = False,
    regex: bool = False,
) -> tuple[str, int]:
    """Replace every match of ``query`` and return the new text and the replacement count.

    With ``regex`` true, ``replacement`` is a template that may use group references such
    as ``\\1`` or ``\\g<name>``; otherwise it is inserted literally.

    Raises ``ValueError`` if ``query`` is empty, if ``regex`` is true and ``query`` is not
    a valid regular expression, or if a match is found and ``replacement`` is not a valid
    template for it.
    """
    pattern = _compile(query, case_sensitive=case_sensitive, whole_word=whole_word, regex=regex)
    pieces: list[str] = []
    position = 0
    count = 0
    for match in _matches(pattern, text):
        pieces.append(text[position : match.start()])
        pieces.append(_expand(match, replacement) if regex else replacement)
        position = match.end()
        count += 1
    if count == 0:
        return text, 0
    pieces.append(text[position:])
    return "".join(pieces), count


def _compile(query: str, *, case_sensitive: bool, whole_word: bool, regex: bool) -> re.Pattern[str]:
    """Build the compiled pattern for a query, raising ``ValueError`` for a bad query."""
    if not query:
        raise ValueError("query must not be empty")
    flags = 0 if case_sensitive else re.IGNORECASE
    source = query if regex else re.escape(query)
    try:
        pattern = re.compile(source, flags)
        if whole_word:
            pattern = re.compile(_whole_word_source(source, pattern.flags), flags)
    except (re.error, OverflowError) as exc:
        raise ValueError(f"invalid regular expression {query!r}: {exc}") from exc
    return pattern


def _whole_word_source(source: str, compiled_flags: int) -> str:
    """Wrap a valid pattern so it only matches with no word character on either side."""
    verbose = bool(compiled_flags & re.VERBOSE)
    leading = (_LEADING_FLAGS_VERBOSE if verbose else _LEADING_FLAGS).match(source)
    split = leading.end() if leading else 0
    prefix, body = source[:split], source[split:]
    # In verbose mode a trailing comment would swallow the closing parenthesis.
    closing = "\n)" if verbose else ")"
    return f"{prefix}{_NO_WORD_BEFORE}(?:{body}{closing}{_NO_WORD_AFTER}"


def _matches(pattern: re.Pattern[str], text: str) -> list[re.Match[str]]:
    """Return the non-overlapping, non-empty matches of ``pattern`` in ``text``."""
    return [match for match in pattern.finditer(text) if match.end() > match.start()]


def _expand(match: re.Match[str], replacement: str) -> str:
    """Expand a regex replacement template, raising ``ValueError`` if it is invalid."""
    try:
        return match.expand(replacement)
    except (re.error, IndexError) as exc:
        raise ValueError(f"invalid replacement {replacement!r}: {exc}") from exc
