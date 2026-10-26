"""Unit tests for mdedit.search: find_all and replace_all."""

import pytest

from mdedit.search import find_all, replace_all


def test_find_all_basic() -> None:
    assert find_all("abcabc", "bc") == [(1, 3), (4, 6)]
    assert find_all("abc", "abc") == [(0, 3)]
    assert find_all("x.y.z", ".") == [(1, 2), (3, 4)]
    assert find_all("a+b", "a+b") == [(0, 3)]


def test_find_all_no_overlap() -> None:
    assert find_all("aaaa", "aa") == [(0, 2), (2, 4)]
    assert find_all("aaa", "aa") == [(0, 2)]
    assert find_all("aaaaa", "aa", regex=True) == [(0, 2), (2, 4)]
    assert replace_all("aaaa", "aa", "b") == ("bb", 2)


def test_find_all_case_insensitive() -> None:
    assert find_all("Hello hello", "HELLO", case_sensitive=False) == [(0, 5), (6, 11)]
    assert find_all("Hello hello", "HELLO") == []
    assert find_all("Hello hello", "hello") == [(6, 11)]
    assert find_all("ABC abc", "[a-c]+", case_sensitive=False, regex=True) == [(0, 3), (4, 7)]
    assert replace_all("Cat cat", "CAT", "dog", case_sensitive=False) == ("dog dog", 2)


def test_find_all_whole_word() -> None:
    assert find_all("cat concat cat.", "cat", whole_word=True) == [(0, 3), (11, 14)]
    assert find_all("cat_ 1cat cat2", "cat", whole_word=True) == []
    assert find_all("café cat", "caf", whole_word=True) == []
    # Boundaries are checked on the match edges, so queries may start or end with punctuation.
    assert find_all("a cat. b", "cat.", whole_word=True) == [(2, 6)]
    # A match skipped for its boundaries does not hide a later whole-word match.
    assert find_all("xa a a", "a a", whole_word=True) == [(3, 6)]
    assert find_all("CAT cat", "cat", whole_word=True, case_sensitive=False) == [(0, 3), (4, 7)]
    assert find_all("12a 34 5", r"\d+", whole_word=True, regex=True) == [(4, 6), (7, 8)]
    assert find_all("cat dog catdog", "cat|dog", whole_word=True, regex=True) == [(0, 3), (4, 7)]
    assert replace_all("cat concat", "cat", "dog", whole_word=True) == ("dog concat", 1)


def test_find_all_whole_word_with_inline_regex_flags() -> None:
    assert find_all("Cat concat", "(?i)cat", whole_word=True, regex=True) == [(0, 3)]
    # The ASCII flag does not shrink the definition of a word character.
    assert find_all("éx x", "(?a)x", whole_word=True, regex=True) == [(3, 4)]
    # A verbose pattern ending in a comment still gets its closing boundary.
    assert find_all("cat concat", "(?x) cat  # animal", whole_word=True, regex=True) == [(0, 3)]
    assert find_all("Cat cat", "(?x) # c\n (?i) cat", whole_word=True, regex=True) == [
        (0, 3),
        (4, 7),
    ]


def test_find_all_regex_skips_zero_length() -> None:
    assert find_all("a1 b22", r"\d+", regex=True) == [(1, 2), (4, 6)]
    assert find_all("a1 b22", r"\d*", regex=True) == [(1, 2), (4, 6)]
    assert find_all("abc", r"\b", regex=True) == []
    assert find_all("aa", r"a*?", regex=True) == [(0, 1), (1, 2)]
    assert replace_all("a1 b22", r"\d*", "#", regex=True) == ("a# b#", 2)
    assert replace_all("abc", r"x*", "#", regex=True) == ("abc", 0)


def test_replace_all_literal_and_group_references() -> None:
    assert replace_all("abcabc", "bc", "X") == ("aXaX", 2)
    assert replace_all("2026-10-25", r"(\d+)-(\d+)-(\d+)", r"\3/\2/\1", regex=True) == (
        "25/10/2026",
        1,
    )
    assert replace_all("a", "a", r"\1") == ("\\1", 1)
    assert replace_all("a.b", ".", r"\g<0>\n") == ("a\\g<0>\\nb", 1)
    assert replace_all("a1b2", r"(?P<d>\d)", r"<\g<d>>", regex=True) == ("a<1>b<2>", 2)
    assert replace_all("abab", "ab", "") == ("", 2)
    assert replace_all("ab", "b", "bb") == ("abb", 1)


def test_replace_all_invalid_replacement_template_raises_value_error() -> None:
    with pytest.raises(ValueError):
        replace_all("abc", "(b)", r"\2", regex=True)
    with pytest.raises(ValueError):
        replace_all("abc", "(b)", r"\g<missing>", regex=True)
    with pytest.raises(ValueError):
        replace_all("abc", "b", "\\", regex=True)


@pytest.mark.parametrize("regex", [False, True])
def test_empty_or_invalid_query_raises_value_error(regex: bool) -> None:
    with pytest.raises(ValueError):
        find_all("abc", "", regex=regex)
    with pytest.raises(ValueError):
        replace_all("abc", "", "x", regex=regex)
    with pytest.raises(ValueError):
        find_all("", "", regex=regex, whole_word=True)
    if regex:
        for bad in ["(", "[a-", "*a", "a)", "\\", "a{99999999999999}"]:
            with pytest.raises(ValueError):
                find_all("abc", bad, regex=True)
            with pytest.raises(ValueError):
                replace_all("abc", bad, "x", regex=True)
            with pytest.raises(ValueError):
                find_all("abc", bad, regex=True, whole_word=True, case_sensitive=False)
    else:
        # Without regex=True these are ordinary literal queries.
        assert find_all("a(b[c*", "(") == [(1, 2)]
        assert find_all("a(b[c*", "[") == [(3, 4)]
        assert find_all("a(b[c*", "*") == [(5, 6)]


def test_nothing_matches() -> None:
    assert find_all("abc", "x") == []
    assert find_all("", "x") == []
    assert find_all("abc", "x+", regex=True) == []
    assert find_all("concat", "cat", whole_word=True) == []
    assert replace_all("abc", "x", "y") == ("abc", 0)
    assert replace_all("", "x", "y") == ("", 0)
    assert replace_all("abc", "x+", r"\1", regex=True) == ("abc", 0)
    assert replace_all("concat", "cat", "dog", whole_word=True) == ("concat", 0)
