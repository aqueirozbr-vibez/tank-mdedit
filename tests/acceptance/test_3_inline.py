from mdedit.inline import render_inline


def test_ac1_escaping() -> None:
    assert render_inline('a & b < c > d "e"') == "a &amp; b &lt; c &gt; d &quot;e&quot;"
    assert render_inline("plain text") == "plain text"


def test_ac2_strong() -> None:
    assert render_inline("a **word** b") == "a <strong>word</strong> b"


def test_ac3_emphasis_nesting_and_intraword_underscore() -> None:
    assert render_inline("*word*") == "<em>word</em>"
    assert render_inline("_word_") == "<em>word</em>"
    assert render_inline("**a *b* c**") == "<strong>a <em>b</em> c</strong>"
    assert render_inline("snake_case_name") == "snake_case_name"


def test_ac4_code_span() -> None:
    assert render_inline("`x < y`") == "<code>x &lt; y</code>"
    assert render_inline("`*a* [b](c)`") == "<code>*a* [b](c)</code>"


def test_ac5_link() -> None:
    assert (
        render_inline("[label](https://example.com/a?b=1&c=2)")
        == '<a href="https://example.com/a?b=1&amp;c=2">label</a>'
    )
    assert render_inline("[*x*](notes.md)") == '<a href="notes.md"><em>x</em></a>'


def test_ac6_unsafe_schemes() -> None:
    assert render_inline("[click](javascript:void)") == "click"
    assert render_inline("[click](JavaScript:void)") == "click"
    assert render_inline("[mail](mailto:a@b.c)") == '<a href="mailto:a@b.c">mail</a>'
    assert render_inline("[n](notes.md)") == '<a href="notes.md">n</a>'


def test_ac7_backslash_escapes() -> None:
    assert render_inline(r"\*not em\*") == "*not em*"
    assert render_inline(r"\_x\_") == "_x_"
    assert render_inline(r"\`x\`") == "`x`"
    assert render_inline(r"\[a\](b)") == "[a](b)"
    assert render_inline("a\\\\b") == "a\\b"


def test_ac8_unclosed_markers() -> None:
    assert render_inline("**open") == "**open"
    assert render_inline("*open") == "*open"
    assert render_inline("`open") == "`open"
    assert render_inline("[open") == "[open"
