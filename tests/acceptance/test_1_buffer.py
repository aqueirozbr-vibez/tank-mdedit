from collections.abc import Callable

import pytest

from mdedit.buffer import TextBuffer


def test_ac1_insert_and_empty_start() -> None:
    b = TextBuffer("ab")
    b.insert(1, "X")
    assert b.text == "aXb"
    assert TextBuffer().text == ""


def test_ac2_delete_returns_removed() -> None:
    b = TextBuffer("hello world")
    assert b.delete(5, 11) == " world"
    assert b.text == "hello"
    assert b.delete(2, 2) == "" and b.text == "hello"


def test_ac3_replace_returns_replaced() -> None:
    b = TextBuffer("hello world")
    assert b.replace(0, 5, "HELLO") == "hello"
    assert b.text == "HELLO world"


BAD_CALLS: list[Callable[[TextBuffer], object]] = [
    lambda b: b.insert(-1, "x"),
    lambda b: b.insert(4, "x"),
    lambda b: b.delete(-1, 1),
    lambda b: b.delete(0, 4),
    lambda b: b.delete(2, 1),
    lambda b: b.replace(0, 9, "x"),
    lambda b: b.replace(2, 1, "x"),
]


@pytest.mark.parametrize("call", BAD_CALLS)
def test_ac4_bad_offsets_raise_and_leave_text(call: Callable[[TextBuffer], object]) -> None:
    b = TextBuffer("abc")
    with pytest.raises(IndexError):
        call(b)
    assert b.text == "abc"


def test_ac5_position_of() -> None:
    b = TextBuffer("ab\ncd")
    assert b.position_of(0) == (1, 1)
    assert b.position_of(2) == (1, 3)
    assert b.position_of(3) == (2, 1)
    assert b.position_of(5) == (2, 3)
    with pytest.raises(IndexError):
        b.position_of(6)
    with pytest.raises(IndexError):
        b.position_of(-1)


def test_ac6_offset_of_round_trip_and_bounds() -> None:
    b = TextBuffer("ab\ncd\n\nxyz")
    for offset in range(len(b.text) + 1):
        line, column = b.position_of(offset)
        assert b.offset_of(line, column) == offset
    for bad in [(0, 1), (5, 1), (1, 0), (1, 4), (3, 2)]:
        with pytest.raises(IndexError):
            b.offset_of(*bad)


def test_ac7_line_count_and_line() -> None:
    assert TextBuffer("").line_count == 1
    assert TextBuffer("a\n").line_count == 2
    b = TextBuffer("one\ntwo\n")
    assert b.line_count == 3
    assert b.line(1) == "one" and b.line(2) == "two" and b.line(3) == ""
    for bad in (0, 4):
        with pytest.raises(IndexError):
            b.line(bad)
