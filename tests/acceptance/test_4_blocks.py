from mdedit.blocks import render_blocks


def test_ac1_example() -> None:
    text = "# Title\n\nHello\nworld\n\n- a\n- b"
    assert render_blocks(text) == (
        "<h1>Title</h1>\n<p>Hello world</p>\n<ul>\n<li>a</li>\n<li>b</li>\n</ul>"
    )


def test_ac2_headings() -> None:
    assert render_blocks("###### Six") == "<h6>Six</h6>"
    assert render_blocks("## Two  ") == "<h2>Two</h2>"
    assert render_blocks("####### seven") == "<p>####### seven</p>"


def test_ac3_lists() -> None:
    assert render_blocks("* x\n* y") == "<ul>\n<li>x</li>\n<li>y</li>\n</ul>"
    assert render_blocks("1. a\n2. b") == "<ol>\n<li>a</li>\n<li>b</li>\n</ol>"
    assert render_blocks("3. c\n4. d") == '<ol start="3">\n<li>c</li>\n<li>d</li>\n</ol>'


def test_ac4_fenced_code() -> None:
    text = "```py\nif a < b:\n    **x**\n```"
    assert render_blocks(text) == (
        '<pre><code class="language-py">if a &lt; b:\n    **x**</code></pre>'
    )
    assert render_blocks("```\nraw\n```") == "<pre><code>raw</code></pre>"
    assert render_blocks("```\nnever\nclosed") == "<pre><code>never\nclosed</code></pre>"
    seen: list[str] = []

    def spy(s: str) -> str:
        seen.append(s)
        return s

    render_blocks("```\ncode\n```", inline=spy)
    assert seen == []


def test_ac5_blockquote() -> None:
    assert render_blocks("> a\n> b") == "<blockquote>\n<p>a b</p>\n</blockquote>"
    assert render_blocks("> # H") == "<blockquote>\n<h1>H</h1>\n</blockquote>"


def test_ac6_rule() -> None:
    assert render_blocks("---") == "<hr>"
    assert render_blocks("a\n\n-----\n\nb") == "<p>a</p>\n<hr>\n<p>b</p>"


def test_ac7_inline_hook_and_empty() -> None:
    def shout(s: str) -> str:
        return f"[{s.upper()}]"

    out = render_blocks("# h\n\np\n\n- i\n\n> q", inline=shout)
    assert out == (
        "<h1>[H]</h1>\n<p>[P]</p>\n<ul>\n<li>[I]</li>\n</ul>\n"
        "<blockquote>\n<p>[Q]</p>\n</blockquote>"
    )
    assert render_blocks("<b>") == "<p>&lt;b&gt;</p>"
    assert render_blocks("") == "" and render_blocks("\n  \n\n") == ""
