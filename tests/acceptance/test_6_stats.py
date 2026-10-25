import pytest

from mdedit.stats import char_count, outline, reading_minutes, word_count


def test_ac1_words() -> None:
    assert word_count("# Hello, *world*!\n\nIt's a well-known [link](https://x.org/a-b).") == 6
    assert word_count("- * > # ---") == 0
    assert word_count("route 66 rocks") == 3


def test_ac2_link_label_only() -> None:
    assert word_count("[two words](https://example.com/three-more-words)") == 2


def test_ac3_fenced_code_ignored() -> None:
    text = "intro\n```\nlots of code words here\n# not a heading\n```\nend"
    assert word_count(text) == 2
    assert outline(text) == []


def test_ac4_chars() -> None:
    assert char_count("a b\nc") == 4
    assert char_count("a b\nc", spaces=False) == 3
    assert char_count("a\tb", spaces=False) == 2


def test_ac5_reading_minutes() -> None:
    assert reading_minutes("") == 0
    assert reading_minutes(" ".join(["w"] * 201)) == 2
    assert reading_minutes(" ".join(["w"] * 200)) == 1
    assert reading_minutes("a b c", wpm=2) == 2
    with pytest.raises(ValueError):
        reading_minutes("a", wpm=0)


def test_ac6_outline() -> None:
    assert outline("# A\n```\n# not\n```\n## B ##") == [(1, "A"), (2, "B")]
    assert outline("###### Six\n####### seven\n#nospace") == [(6, "Six")]
