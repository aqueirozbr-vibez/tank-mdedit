"""Unit tests for mdedit.buffer.TextBuffer."""

from collections.abc import Callable

import pytest

from mdedit.buffer import TextBuffer


def test_insert_and_empty_start() -> None:
    buf = TextBuffer("ab")
    buf.insert(1, "X")
    assert buf.text == "aXb"

    empty = TextBuffer()
    assert empty.text == ""

    # Inserting at both ends, including into an empty buffer.
    empty.insert(0, "mid")
    empty.insert(0, "<")
    empty.insert(len(empty.text), ">")
    assert empty.text == "<mid>"

    # Inserting an empty string is a no-op.
    empty.insert(2, "")
    assert empty.text == "<mid>"


def test_delete_returns_removed() -> None:
    buf = TextBuffer("hello world")
    assert buf.delete(5, 11) == " world"
    assert buf.text == "hello"

    assert buf.delete(0, 1) == "h"
    assert buf.text == "ello"

    # An empty range removes nothing.
    assert buf.delete(2, 2) == ""
    assert buf.text == "ello"

    # Deleting everything leaves an empty buffer.
    assert buf.delete(0, len(buf.text)) == "ello"
    assert buf.text == ""

    multi = TextBuffer("ab\ncd")
    assert multi.delete(1, 4) == "b\nc"
    assert multi.text == "ad"


def test_replace_returns_replaced() -> None:
    buf = TextBuffer("hello world")
    assert buf.replace(6, 11, "there") == "world"
    assert buf.text == "hello there"

    # Replacement may be longer or shorter than the range.
    assert buf.replace(0, 5, "hi") == "hello"
    assert buf.text == "hi there"
    assert buf.replace(0, 2, "greetings") == "hi"
    assert buf.text == "greetings there"

    # An empty range is an insertion.
    assert buf.replace(9, 9, ",") == ""
    assert buf.text == "greetings, there"

    # An empty replacement is a deletion.
    assert buf.replace(9, 10, "") == ","
    assert buf.text == "greetings there"

    empty = TextBuffer()
    assert empty.replace(0, 0, "x") == ""
    assert empty.text == "x"


BadCall = Callable[[TextBuffer], object]


@pytest.mark.parametrize(
    "call",
    [
        pytest.param(lambda b: b.insert(-1, "X"), id="insert-negative"),
        pytest.param(lambda b: b.insert(6, "X"), id="insert-past-end"),
        pytest.param(lambda b: b.delete(-1, 2), id="delete-negative-start"),
        pytest.param(lambda b: b.delete(0, 6), id="delete-end-past-end"),
        pytest.param(lambda b: b.delete(6, 6), id="delete-start-past-end"),
        pytest.param(lambda b: b.delete(-2, -1), id="delete-both-negative"),
        pytest.param(lambda b: b.delete(3, 2), id="delete-start-after-end"),
        pytest.param(lambda b: b.replace(-1, 2, "X"), id="replace-negative-start"),
        pytest.param(lambda b: b.replace(0, 6, "X"), id="replace-end-past-end"),
        pytest.param(lambda b: b.replace(6, 6, "X"), id="replace-start-past-end"),
        pytest.param(lambda b: b.replace(4, 1, "X"), id="replace-start-after-end"),
    ],
)
def test_bad_offsets_raise_and_leave_text(call: BadCall) -> None:
    buf = TextBuffer("ab\ncd")
    with pytest.raises(IndexError):
        call(buf)
    assert buf.text == "ab\ncd"


def test_bad_offsets_on_empty_buffer() -> None:
    buf = TextBuffer()
    with pytest.raises(IndexError):
        buf.insert(1, "X")
    with pytest.raises(IndexError):
        buf.delete(0, 1)
    with pytest.raises(IndexError):
        buf.replace(1, 1, "X")
    assert buf.text == ""


def test_position_of() -> None:
    buf = TextBuffer("ab\ncd")
    assert buf.position_of(0) == (1, 1)
    assert buf.position_of(1) == (1, 2)
    assert buf.position_of(2) == (1, 3)
    assert buf.position_of(3) == (2, 1)
    assert buf.position_of(4) == (2, 2)
    assert buf.position_of(5) == (2, 3)

    with pytest.raises(IndexError):
        buf.position_of(-1)
    with pytest.raises(IndexError):
        buf.position_of(6)

    assert TextBuffer().position_of(0) == (1, 1)

    # Consecutive and trailing newlines produce empty lines.
    blank = TextBuffer("a\n\nb\n")
    assert blank.position_of(2) == (2, 1)
    assert blank.position_of(3) == (3, 1)
    assert blank.position_of(4) == (3, 2)
    assert blank.position_of(5) == (4, 1)


ROUND_TRIP_TEXTS = ["", "ab\ncd", "a\n\nb\n", "\n", "one\ntwo\nthree"]


def test_offset_of_round_trip_and_bounds() -> None:
    for text in ROUND_TRIP_TEXTS:
        buf = TextBuffer(text)
        for offset in range(len(text) + 1):
            line, column = buf.position_of(offset)
            assert buf.offset_of(line, column) == offset

    buf = TextBuffer("ab\ncd")
    assert buf.offset_of(1, 1) == 0
    assert buf.offset_of(1, 3) == 2
    assert buf.offset_of(2, 1) == 3
    assert buf.offset_of(2, 3) == 5

    for line, column in [(0, 1), (3, 1), (-1, 1), (1, 0), (1, 4), (2, 0), (2, 4), (1, -1)]:
        with pytest.raises(IndexError):
            buf.offset_of(line, column)

    empty = TextBuffer()
    assert empty.offset_of(1, 1) == 0
    with pytest.raises(IndexError):
        empty.offset_of(1, 2)
    with pytest.raises(IndexError):
        empty.offset_of(2, 1)


def test_line_count_and_line() -> None:
    assert TextBuffer().line_count == 1
    assert TextBuffer("a").line_count == 1
    assert TextBuffer("a\n").line_count == 2
    assert TextBuffer("ab\ncd").line_count == 2
    assert TextBuffer("\n\n").line_count == 3

    buf = TextBuffer("ab\ncd\n")
    assert buf.line(1) == "ab"
    assert buf.line(2) == "cd"
    assert buf.line(3) == ""
    for n in (0, -1, 4):
        with pytest.raises(IndexError):
            buf.line(n)

    empty = TextBuffer()
    assert empty.line(1) == ""
    with pytest.raises(IndexError):
        empty.line(2)

    # Only "\n" separates lines; a "\r" stays part of the line.
    crlf = TextBuffer("a\r\nb")
    assert crlf.line_count == 2
    assert crlf.line(1) == "a\r"

    # line_count and line follow edits.
    buf.insert(0, "x\n")
    assert buf.line_count == 4
    assert buf.line(1) == "x"
    assert buf.line(2) == "ab"
    buf.delete(0, len(buf.text))
    assert buf.line_count == 1
