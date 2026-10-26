"""Unit tests for mdedit.stats (spec 6, document statistics)."""

import pytest

from mdedit.stats import char_count, outline, reading_minutes, word_count


def test_word_count_joins_apostrophes_and_hyphens() -> None:
    sample = "# Hello, *world*!\n\nIt's a well-known [link](https://x.org/a-b)."
    assert word_count(sample) == 6
    assert word_count("well-known") == 1
    assert word_count("It's") == 1
    assert word_count("rock'n'roll state-of-the-art") == 2
    # An apostrophe or hyphen not between two letters/digits does not join.
    assert word_count("a - b") == 2
    assert word_count("a--b") == 2
    assert word_count("'quoted' -dash-") == 2
    # Digits are word characters too; other punctuation separates.
    assert word_count("route 66, v2.0") == 4
    # Markdown punctuation on its own is not a word.
    assert word_count("# * - > --- ``` | ** __") == 0
    assert word_count("") == 0
    assert word_count("   \n\t ") == 0
    # Non-ASCII letters count.
    assert word_count("café naïve") == 2


def test_word_count_counts_link_label_not_url() -> None:
    assert word_count("[link](https://x.org/a-b)") == 1
    assert word_count("see [the docs](https://example.com/path/to/page) now") == 4
    # A title inside the parentheses belongs to the link target, not the label.
    assert word_count('[label](https://x.org "some title here")') == 1
    # URLs with balanced parentheses are still excluded.
    assert word_count("[Foo](https://en.wikipedia.org/wiki/Foo_(bar))") == 1
    # Images: the alt text is the label.
    assert word_count("![a cat](cat.png)") == 2
    # A link whose label is an image.
    assert word_count("[![logo image](logo.png)](https://x.org)") == 2
    # Several links on one line.
    assert word_count("[one](a/b/c) and [two](d/e/f)") == 3
    # A bracket that is not followed by a parenthesised target is plain text.
    assert word_count("[x] done (really)") == 3
    # A label may hold balanced brackets; the target is still excluded.
    assert word_count("[see [1] here](https://x.org/a-b)") == 3
    assert word_count("[a] [b](https://x.org/c-d)") == 2


def test_fenced_code_ignored_by_word_count_and_outline() -> None:
    text = "intro words\n```\nlots of code here\n# not a heading\n```\noutro\n"
    assert word_count(text) == 3
    assert outline(text) == []
    # The info string on the opening fence is not prose either.
    assert word_count("```python\nprint('hi')\n```") == 0
    # Several fenced blocks, with headings between them.
    text2 = "# One\n```\n# skip\n```\n## Two\n```sh\n## skip too\necho hi\n```\n### Three"
    assert outline(text2) == [(1, "One"), (2, "Two"), (3, "Three")]
    assert word_count(text2) == 3
    assert outline("# A\n```\n# not\n```\n## B ##") == [(1, "A"), (2, "B")]


def test_char_count_with_and_without_spaces() -> None:
    assert char_count("a b\nc") == 4
    assert char_count("a b\nc", spaces=False) == 3
    assert char_count("") == 0
    assert char_count("", spaces=False) == 0
    assert char_count("\n\n") == 0
    # Tabs and other whitespace count unless spaces=False.
    assert char_count("a\tb c") == 5
    assert char_count("a\tb c\u00a0d", spaces=False) == 4
    # Windows line endings are newlines too.
    assert char_count("ab\r\ncd") == 4
    # Non-ASCII characters count once each.
    assert char_count("café") == 4


def test_reading_minutes_rounds_up_and_rejects_low_wpm() -> None:
    assert reading_minutes("") == 0
    assert reading_minutes("# --- *") == 0
    assert reading_minutes("word") == 1
    assert reading_minutes(" ".join(["word"] * 200)) == 1
    assert reading_minutes(" ".join(["word"] * 201)) == 2
    assert reading_minutes(" ".join(["word"] * 10), wpm=3) == 4
    assert reading_minutes(" ".join(["word"] * 9), wpm=3) == 3
    assert reading_minutes("one two", wpm=1) == 2
    with pytest.raises(ValueError):
        reading_minutes("some words", wpm=0)
    with pytest.raises(ValueError):
        reading_minutes("some words", wpm=-5)
    with pytest.raises(ValueError):
        reading_minutes("", wpm=0)


def test_outline_levels_and_stripped_titles() -> None:
    assert outline("# A\n```\n# not\n```\n## B ##") == [(1, "A"), (2, "B")]
    text = "# One\n## Two\n### Three\n#### Four\n##### Five\n###### Six\n####### Seven"
    assert outline(text) == [
        (1, "One"),
        (2, "Two"),
        (3, "Three"),
        (4, "Four"),
        (5, "Five"),
        (6, "Six"),
    ]
    # A space must follow the hashes.
    assert outline("#NoSpace\n##\nplain text\n") == []
    # Surrounding whitespace and trailing hashes are stripped.
    assert outline("##   Spaced title   \n# Closed #####   ") == [
        (2, "Spaced title"),
        (1, "Closed"),
    ]
    # Order is preserved and body text is ignored.
    assert outline("text\n## Later\nmore\n# Earlier level\n") == [
        (2, "Later"),
        (1, "Earlier level"),
    ]
    assert outline("") == []
    # Windows and old Mac line endings separate lines.
    assert outline("# A\r\n## B\r### C\r\n") == [(1, "A"), (2, "B"), (3, "C")]
    # Only \n and \r end a line, matching char_count: a form feed or a Unicode
    # line separator stays inside the heading line.
    assert outline("# A\x0cB\n## C\u2028D") == [(1, "A\x0cB"), (2, "C\u2028D")]
