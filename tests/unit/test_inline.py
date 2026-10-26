"""Unit tests for mdedit.inline.render_inline."""

import pytest

from mdedit.inline import render_inline


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("", ""),
        ("plain text, nothing to do.", "plain text, nothing to do."),
        ("it's 50% off (today) #1 - ok!", "it's 50% off (today) #1 - ok!"),
        ("line one\nline two", "line one\nline two"),
        ("a & b", "a &amp; b"),
        ("<script>alert(1)</script>", "&lt;script&gt;alert(1)&lt;/script&gt;"),
        ("1 < 2 > 0", "1 &lt; 2 &gt; 0"),
        ('say "hi"', "say &quot;hi&quot;"),
        ("&amp; stays escaped", "&amp;amp; stays escaped"),
        ("a * b _ c ] d", "a * b _ c ] d"),
        ("C:\\Users\\me", "C:\\Users\\me"),
    ],
)
def test_escapes_html_special_characters(source: str, expected: str) -> None:
    assert render_inline(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("**word**", "<strong>word</strong>"),
        ("a **b c** d", "a <strong>b c</strong> d"),
        ("__word__", "<strong>word</strong>"),
        ("**a & <b>**", "<strong>a &amp; &lt;b&gt;</strong>"),
        ("**one** and **two**", "<strong>one</strong> and <strong>two</strong>"),
        ("** not strong**", "** not strong**"),
        ("(**word**).", "(<strong>word</strong>)."),
    ],
)
def test_strong(source: str, expected: str) -> None:
    assert render_inline(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("*word*", "<em>word</em>"),
        ("_word_", "<em>word</em>"),
        ("a *b* c _d_ e", "a <em>b</em> c <em>d</em> e"),
        ("**a *b* c**", "<strong>a <em>b</em> c</strong>"),
        ("*a **b** c*", "<em>a <strong>b</strong> c</em>"),
        ("__a _b_ c__", "<strong>a <em>b</em> c</strong>"),
        ("***both***", "<em><strong>both</strong></em>"),
        ("*foo**bar**baz*", "<em>foo<strong>bar</strong>baz</em>"),
        ("snake_case_name", "snake_case_name"),
        ("1_000_000", "1_000_000"),
        ("_a snake_case word_", "<em>a snake_case word</em>"),
        ("*snake_case_name*", "<em>snake_case_name</em>"),
        ("_foo_bar_", "<em>foo_bar</em>"),
        ("a * b * c", "a * b * c"),
        ("*a & b*", "<em>a &amp; b</em>"),
    ],
)
def test_emphasis_nesting_and_intraword_underscore(source: str, expected: str) -> None:
    assert render_inline(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("`x < y`", "<code>x &lt; y</code>"),
        ('`"a" & <b>`', "<code>&quot;a&quot; &amp; &lt;b&gt;</code>"),
        ("`*a* _b_ **c**`", "<code>*a* _b_ **c**</code>"),
        ("`[label](https://example.com)`", "<code>[label](https://example.com)</code>"),
        ("`a\\*b`", "<code>a\\*b</code>"),
        ("use `x` and `y`", "use <code>x</code> and <code>y</code>"),
        ("``a ` b``", "<code>a ` b</code>"),
        ("`` `tick` ``", "<code>`tick`</code>"),
        ("*a `*` b*", "<em>a <code>*</code> b</em>"),
        ("[`code` link](notes.md)", '<a href="notes.md"><code>code</code> link</a>'),
    ],
)
def test_code_span(source: str, expected: str) -> None:
    assert render_inline(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "[label](https://example.com/a?b=1&c=2)",
            '<a href="https://example.com/a?b=1&amp;c=2">label</a>',
        ),
        ("see [the notes](notes.md).", 'see <a href="notes.md">the notes</a>.'),
        (
            "[*em* and **strong**](https://example.com)",
            '<a href="https://example.com"><em>em</em> and <strong>strong</strong></a>',
        ),
        ("[a <b> & c](x.md)", '<a href="x.md">a &lt;b&gt; &amp; c</a>'),
        ('[q](x"onmouseover="y)', '<a href="x&quot;onmouseover=&quot;y">q</a>'),
        (
            "[w](https://en.wikipedia.org/wiki/A_(b))",
            '<a href="https://en.wikipedia.org/wiki/A_(b)">w</a>',
        ),
        ("[m](mailto:me@example.com)", '<a href="mailto:me@example.com">m</a>'),
        ("[e]()", '<a href="">e</a>'),
        ("[s]( notes.md )", '<a href="notes.md">s</a>'),
        ("*see [a](b.md)*", '<em>see <a href="b.md">a</a></em>'),
        ("[a](b.md) and [c](d.md)", '<a href="b.md">a</a> and <a href="d.md">c</a>'),
        ("[a [b] c](d.md)", '<a href="d.md">a [b] c</a>'),
        ("[a [b](c.md) d](e.md)", '[a <a href="c.md">b</a> d](e.md)'),
        ("*[a*](b.md)", '*<a href="b.md">a*</a>'),
        ("[label]", "[label]"),
        ("[label] (x.md)", "[label] (x.md)"),
        ("[label](has space)", "[label](has space)"),
        ("[x](a(b)c)", '<a href="a(b)c">x</a>'),
        ("[x](a(b)", "[x](a(b)"),
        ("[](a[](a)", '[](a<a href="a"></a>'),
    ],
)
def test_link(source: str, expected: str) -> None:
    assert render_inline(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("[click](javascript:alert(1))", "click"),
        ("[click](JavaScript:alert(1))", "click"),
        ("[click](JAVASCRIPT:alert(1))", "click"),
        ("[click]( javascript:alert(1) )", "click"),
        ("[click](vbscript:msgbox(1))", "click"),
        ("[click](data:text/html;base64,PHNjcmlwdD4=)", "click"),
        ("[click](file:///etc/passwd)", "click"),
        ("[<img src=x>](javascript:alert(1))", "&lt;img src=x&gt;"),
        ("[*click* & go](javascript:alert(1))", "<em>click</em> &amp; go"),
        ("a [b](javascript:c) d", "a b d"),
        # A control character or whitespace cannot hide a scheme: it ends the
        # destination, so there is no link at all.
        ("[x](\x01javascript:alert(1))", "[x](\x01javascript:alert(1))"),
        ("[x](java\tscript:alert(1))", "[x](java\tscript:alert(1))"),
        ("[x](java\nscript:alert(1))", "[x](java\nscript:alert(1))"),
        # Without a valid scheme a browser resolves these as relative URLs.
        ("[x](\\javascript:alert(1))", '<a href="\\javascript:alert(1)">x</a>'),
        ("[x](javascript\\:alert(1))", '<a href="javascript\\:alert(1)">x</a>'),
        ("[x](&#106;avascript:alert(1))", '<a href="&amp;#106;avascript:alert(1)">x</a>'),
        ("[n](notes.md)", '<a href="notes.md">n</a>'),
        ("[n](/docs/a:b)", '<a href="/docs/a:b">n</a>'),
        ("[n](#section)", '<a href="#section">n</a>'),
        ("[n](HTTPS://EXAMPLE.COM)", '<a href="HTTPS://EXAMPLE.COM">n</a>'),
        ("[n](Http://example.com)", '<a href="Http://example.com">n</a>'),
        ("[n](MailTo:me@example.com)", '<a href="MailTo:me@example.com">n</a>'),
    ],
)
def test_unsafe_schemes(source: str, expected: str) -> None:
    assert render_inline(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("\\*not em\\*", "*not em*"),
        ("\\_not em\\_", "_not em_"),
        ("\\`not code\\`", "`not code`"),
        ("\\[not link\\](x.md)", "[not link](x.md)"),
        ("a\\\\b", "a\\b"),
        ("\\\\*em*", "\\<em>em</em>"),
        ("**a\\*\\*", "**a**"),
        ("*a\\*b*", "<em>a*b</em>"),
        ("[a\\]b](x.md)", '<a href="x.md">a]b</a>'),
        ("[a](x\\)y.md)", '<a href="x)y.md">a</a>'),
        ("\\a and \\<", "\\a and \\&lt;"),
        ("trailing \\", "trailing \\"),
    ],
)
def test_backslash_escapes(source: str, expected: str) -> None:
    assert render_inline(source) == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("**open", "**open"),
        ("*open", "*open"),
        ("_open", "_open"),
        ("`open", "`open"),
        ("[open", "[open"),
        ("``open`", "``open`"),
        ("[open](", "[open]("),
        ("[open](x.md", "[open](x.md"),
        ("[open <b>", "[open &lt;b&gt;"),
        ("**open *em*", "**open <em>em</em>"),
        ("**a*", "*<em>a</em>"),
        ("*a**", "<em>a</em>*"),
        ("`a` `b", "<code>a</code> `b"),
        ("[a](b.md) [c", '<a href="b.md">a</a> [c'),
        ("[](a" * 3, "[](a[](a[](a"),
    ],
)
def test_unclosed_markers(source: str, expected: str) -> None:
    assert render_inline(source) == expected
