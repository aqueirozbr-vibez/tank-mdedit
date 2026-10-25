import pytest

from mdedit.search import find_all, replace_all


def test_ac1_basic() -> None:
    assert find_all("abcabc", "bc") == [(1, 3), (4, 6)]


def test_ac2_no_overlap() -> None:
    assert find_all("aaaa", "aa") == [(0, 2), (2, 4)]


def test_ac3_case_insensitive() -> None:
    assert find_all("Hello hello", "HELLO", case_sensitive=False) == [(0, 5), (6, 11)]
    assert find_all("Hello hello", "HELLO") == []


def test_ac4_whole_word() -> None:
    assert find_all("cat concat cat.", "cat", whole_word=True) == [(0, 3), (11, 14)]
    assert find_all("cat_cat cat", "cat", whole_word=True) == [(8, 11)]


def test_ac5_regex_and_zero_length() -> None:
    assert find_all("a1 b22", r"\d+", regex=True) == [(1, 2), (4, 6)]
    assert find_all("abc", r"x*", regex=True) == []


def test_ac6_replace() -> None:
    assert replace_all("abcabc", "bc", "X") == ("aXaX", 2)
    assert replace_all("2026-10-25", r"(\d+)-(\d+)-(\d+)", r"\3/\2/\1", regex=True) == (
        "25/10/2026",
        1,
    )
    assert replace_all("a", "a", r"\1") == ("\\1", 1)
    assert replace_all("A a", "a", "b", case_sensitive=False) == ("b b", 2)


def test_ac7_bad_queries() -> None:
    with pytest.raises(ValueError):
        find_all("abc", "")
    with pytest.raises(ValueError):
        replace_all("abc", "", "x")
    with pytest.raises(ValueError):
        find_all("abc", "(", regex=True)


def test_ac8_nothing_matches() -> None:
    assert find_all("abc", "z") == []
    assert replace_all("abc", "z", "y") == ("abc", 0)
