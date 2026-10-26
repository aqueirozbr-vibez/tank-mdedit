"""Unit tests for block-level markdown rendering in mdedit.blocks."""

from mdedit.blocks import render_blocks


class _Spy:
    """An inline renderer that records every text it receives."""

    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, text: str) -> str:
        self.calls.append(text)
        return f"<em>{text}</em>"


def test_example_document() -> None:
    assert render_blocks("# Title\n\nHello\nworld\n\n- a\n- b") == (
        "<h1>Title</h1>\n<p>Hello world</p>\n<ul>\n<li>a</li>\n<li>b</li>\n</ul>"
    )
    # Lines of a paragraph are stripped and joined by one space.
    assert render_blocks("  Hello  \n\t world \nagain") == "<p>Hello world again</p>"
    # Blank lines (empty or whitespace only) separate blocks and produce no output.
    assert render_blocks("one\n   \n\t\ntwo") == "<p>one</p>\n<p>two</p>"
    assert render_blocks("\n\none\n\n\n\ntwo\n\n") == "<p>one</p>\n<p>two</p>"
    # No trailing newline in the output.
    assert render_blocks("one\n") == "<p>one</p>"
    # A line that starts another block ends the paragraph.
    assert render_blocks("Hello\n# Title") == "<p>Hello</p>\n<h1>Title</h1>"
    assert render_blocks("Hello\n- a") == "<p>Hello</p>\n<ul>\n<li>a</li>\n</ul>"
    assert render_blocks("Hello\n* a") == "<p>Hello</p>\n<ul>\n<li>a</li>\n</ul>"
    assert render_blocks("Hello\n2. a") == '<p>Hello</p>\n<ol start="2">\n<li>a</li>\n</ol>'
    assert render_blocks("Hello\n```\ncode\n```") == "<p>Hello</p>\n<pre><code>code</code></pre>"
    assert render_blocks("Hello\n> quoted") == (
        "<p>Hello</p>\n<blockquote>\n<p>quoted</p>\n</blockquote>"
    )
    assert render_blocks("Hello\n---") == "<p>Hello</p>\n<hr>"
    assert render_blocks("Hello\n---\nworld") == "<p>Hello</p>\n<hr>\n<p>world</p>"
    # Windows and old Mac line endings split lines like "\n".
    assert render_blocks("# T\r\n\r\nHello\r\nworld\rnext") == (
        "<h1>T</h1>\n<p>Hello world next</p>"
    )


def test_headings() -> None:
    for level in range(1, 7):
        assert render_blocks("#" * level + " Title") == f"<h{level}>Title</h{level}>"
    # The text after the marker is stripped.
    assert render_blocks("###   spaced out   ") == "<h3>spaced out</h3>"
    # Seven '#' characters followed by text is a paragraph.
    assert render_blocks("####### seven") == "<p>####### seven</p>"
    # A '#' run not followed by a space is not a heading.
    assert render_blocks("#nospace") == "<p>#nospace</p>"
    # A heading is a single line; the next line starts a new block.
    assert render_blocks("# One\n## Two\nbody") == "<h1>One</h1>\n<h2>Two</h2>\n<p>body</p>"
    # Heading text is escaped by default.
    assert render_blocks("## a < b & c") == "<h2>a &lt; b &amp; c</h2>"


def test_lists() -> None:
    assert render_blocks("- a\n- b") == "<ul>\n<li>a</li>\n<li>b</li>\n</ul>"
    assert render_blocks("* a\n* b") == "<ul>\n<li>a</li>\n<li>b</li>\n</ul>"
    # '-' and '*' items on consecutive lines form one list.
    assert render_blocks("- a\n* b\n- c") == "<ul>\n<li>a</li>\n<li>b</li>\n<li>c</li>\n</ul>"
    # Ordered lists starting at 1 have no start attribute.
    assert render_blocks("1. one\n2. two") == "<ol>\n<li>one</li>\n<li>two</li>\n</ol>"
    assert render_blocks("1. one\n1. again") == "<ol>\n<li>one</li>\n<li>again</li>\n</ol>"
    # Any other first number becomes the start attribute.
    assert render_blocks("3. c\n4. d") == '<ol start="3">\n<li>c</li>\n<li>d</li>\n</ol>'
    assert render_blocks("10. ten") == '<ol start="10">\n<li>ten</li>\n</ol>'
    assert render_blocks("0. zero") == '<ol start="0">\n<li>zero</li>\n</ol>'
    assert render_blocks("01. one") == "<ol>\n<li>one</li>\n</ol>"
    # An unordered and an ordered run are two lists.
    assert render_blocks("- a\n1. b") == "<ul>\n<li>a</li>\n</ul>\n<ol>\n<li>b</li>\n</ol>"
    # A blank line ends a list.
    assert render_blocks("- a\n\n- b") == "<ul>\n<li>a</li>\n</ul>\n<ul>\n<li>b</li>\n</ul>"
    # A plain line after an item ends the list and starts a paragraph.
    assert render_blocks("- a\ntext") == "<ul>\n<li>a</li>\n</ul>\n<p>text</p>"
    # A marker without the following space is not a list.
    assert render_blocks("-a") == "<p>-a</p>"
    assert render_blocks("*a*") == "<p>*a*</p>"
    assert render_blocks("1.a") == "<p>1.a</p>"
    # Item text is stripped and escaped by default.
    assert render_blocks("-   <b>  ") == "<ul>\n<li>&lt;b&gt;</li>\n</ul>"
    assert render_blocks("1. x & y") == "<ol>\n<li>x &amp; y</li>\n</ol>"
    # A long digit run is still a start number.
    digits = "9" * 5000
    assert render_blocks(digits + ". big") == f'<ol start="{digits}">\n<li>big</li>\n</ol>'


def test_fenced_code() -> None:
    assert render_blocks('```python\nif a < b:\n    print("hi")\n```') == (
        '<pre><code class="language-python">if a &lt; b:\n    print(&quot;hi&quot;)</code></pre>'
    )
    assert render_blocks("```\na & b\nit's\n```") == (
        "<pre><code>a &amp; b\nit&#x27;s</code></pre>"
    )
    # Blank lines and indentation inside the fence are kept.
    assert render_blocks("```\n  a\n\n  b\n```") == "<pre><code>  a\n\n  b</code></pre>"
    assert render_blocks("```\n```") == "<pre><code></code></pre>"
    # Block markers inside the fence are literal and inline is never called.
    spy = _Spy()
    assert render_blocks("```\n# not a heading\n- not an item\n> no quote\n```", spy) == (
        "<pre><code># not a heading\n- not an item\n&gt; no quote</code></pre>"
    )
    assert spy.calls == []
    # The content is escaped even when inline is given.
    assert render_blocks("```\n<x>\n```", inline=lambda s: s) == (
        "<pre><code>&lt;x&gt;</code></pre>"
    )
    # Text after the closing fence is rendered as blocks again.
    assert render_blocks("```\nx\n```\nafter") == "<pre><code>x</code></pre>\n<p>after</p>"
    # An unclosed fence runs to the end of the text.
    assert render_blocks("```js\nline 1\n\nline 3") == (
        '<pre><code class="language-js">line 1\n\nline 3</code></pre>'
    )
    assert render_blocks("```\n- a\n") == "<pre><code>- a</code></pre>"
    # More than one word after the backticks is not a fence, nor are four backticks.
    assert render_blocks("```two words") == "<p>```two words</p>"
    assert render_blocks("````") == "<p>````</p>"
    # Trailing whitespace on the fence lines is ignored.
    assert render_blocks("```py  \nx\n```  \ny") == (
        '<pre><code class="language-py">x</code></pre>\n<p>y</p>'
    )
    # The language word is escaped inside the class attribute.
    assert render_blocks('```a"<b>\nx\n```') == (
        '<pre><code class="language-a&quot;&lt;b&gt;">x</code></pre>'
    )


def test_blockquote() -> None:
    assert render_blocks("> hello\n> world") == "<blockquote>\n<p>hello world</p>\n</blockquote>"
    # '>' without a following space works too.
    assert render_blocks(">hello\n>world") == "<blockquote>\n<p>hello world</p>\n</blockquote>"
    # The inner lines are rendered as blocks by the same rules.
    assert render_blocks("> # Title\n>\n> - a\n> - b") == (
        "<blockquote>\n<h1>Title</h1>\n<ul>\n<li>a</li>\n<li>b</li>\n</ul>\n</blockquote>"
    )
    # Only one space after '>' is stripped.
    assert render_blocks("> ```\n>   x\n> ```") == (
        "<blockquote>\n<pre><code>  x</code></pre>\n</blockquote>"
    )
    # Quotes nest.
    assert render_blocks("> > deep") == (
        "<blockquote>\n<blockquote>\n<p>deep</p>\n</blockquote>\n</blockquote>"
    )
    # A line not starting with '>' ends the quote.
    assert render_blocks("> q\np") == "<blockquote>\n<p>q</p>\n</blockquote>\n<p>p</p>"
    assert render_blocks("> q\n\n> r") == (
        "<blockquote>\n<p>q</p>\n</blockquote>\n<blockquote>\n<p>r</p>\n</blockquote>"
    )
    # Quoted text is escaped by default and goes through inline when given.
    assert render_blocks("> a & b") == "<blockquote>\n<p>a &amp; b</p>\n</blockquote>"
    assert render_blocks("> *x*", inline=lambda s: f"[{s}]") == (
        "<blockquote>\n<p>[*x*]</p>\n</blockquote>"
    )
    # A quote with no content keeps the "<blockquote>\n" + inner + "\n</blockquote>" shape.
    assert render_blocks(">") == "<blockquote>\n\n</blockquote>"


def test_rule() -> None:
    assert render_blocks("---") == "<hr>"
    assert render_blocks("----------") == "<hr>"
    assert render_blocks("a\n\n---\n\nb") == "<p>a</p>\n<hr>\n<p>b</p>"
    # Fewer than three '-' characters is a paragraph.
    assert render_blocks("--") == "<p>--</p>"
    assert render_blocks("-") == "<p>-</p>"
    # Anything else on the line makes it not a rule.
    assert render_blocks("---x") == "<p>---x</p>"
    assert render_blocks("--- x") == "<p>--- x</p>"
    # Trailing whitespace after the dashes is ignored.
    assert render_blocks("---  ") == "<hr>"


def test_inline_hook_and_empty() -> None:
    spy = _Spy()
    result = render_blocks(
        "# Head <1>\n\npara & one\npara two\n\n- item\n1. first\n\n> quoted\n\n---", spy
    )
    assert result == (
        "<h1><em>Head <1></em></h1>\n"
        "<p><em>para & one para two</em></p>\n"
        "<ul>\n<li><em>item</em></li>\n</ul>\n"
        "<ol>\n<li><em>first</em></li>\n</ol>\n"
        "<blockquote>\n<p><em>quoted</em></p>\n</blockquote>\n"
        "<hr>"
    )
    # Unescaped text, one call per heading, paragraph, item and quoted block.
    assert spy.calls == ["Head <1>", "para & one para two", "item", "first", "quoted"]
    # Inside quotes, every inner block's text goes through inline, nested quotes too.
    quote_spy = _Spy()
    assert render_blocks("> ## H\n> - x\n> - y\n> > deep & low", quote_spy) == (
        "<blockquote>\n<h2><em>H</em></h2>\n<ul>\n<li><em>x</em></li>\n<li><em>y</em></li>\n"
        "</ul>\n<blockquote>\n<p><em>deep & low</em></p>\n</blockquote>\n</blockquote>"
    )
    assert quote_spy.calls == ["H", "x", "y", "deep & low"]
    # Without inline the text is escaped with html.escape(text, quote=True).
    assert render_blocks('<a href="x">Tom & Jerry\'s</a>') == (
        "<p>&lt;a href=&quot;x&quot;&gt;Tom &amp; Jerry&#x27;s&lt;/a&gt;</p>"
    )
    # Empty text and text of only blank lines render as "".
    assert render_blocks("") == ""
    assert render_blocks("\n  \n\t\n") == ""
    empty_spy = _Spy()
    assert render_blocks("", empty_spy) == ""
    assert render_blocks(" \n\n ", empty_spy) == ""
    assert empty_spy.calls == []
