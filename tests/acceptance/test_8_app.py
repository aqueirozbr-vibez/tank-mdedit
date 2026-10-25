import re
import subprocess
import sys
import threading
import time
import urllib.request
from collections.abc import Iterator
from pathlib import Path

import pytest

from mdedit.server import make_server

ROOT = Path(__file__).resolve().parents[2]
IDS = [
    "editor",
    "preview",
    "status",
    "outline",
    "find",
    "replace-with",
    "replace-all",
    "undo",
    "redo",
    "save",
]
LINE = re.compile(r"^mdedit: serving (?P<file>.+) at http://127\.0\.0\.1:(?P<port>\d+)/$")


def fetch(url: str) -> tuple[int, str, str]:
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.status, response.headers["Content-Type"], response.read().decode("utf-8")


@pytest.fixture
def page(tmp_path: Path) -> Iterator[tuple[int, str, str]]:
    server = make_server(tmp_path / "doc.md")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield fetch(f"http://{host}:{port}/")
    finally:
        server.shutdown()
        server.server_close()


def test_ac1_page_has_every_control(page: tuple[int, str, str]) -> None:
    status, content_type, html = page
    assert status == 200 and content_type.startswith("text/html")
    assert "charset=utf-8" in content_type.lower()
    for element_id in IDS:
        assert re.search(rf'id="{element_id}"', html), element_id
    assert re.search(r'<textarea[^>]*id="editor"', html)


def test_ac2_page_is_self_contained(page: tuple[int, str, str]) -> None:
    html = page[2]
    assert not re.search(r"<script[^>]*\bsrc=", html, re.IGNORECASE)
    assert not re.search(r"<link[^>]*\bhref=", html, re.IGNORECASE)
    assert not re.search(r"""(src|href)=["']?(https?:)?//""", html, re.IGNORECASE)
    assert "@import" not in html


def test_ac3_page_calls_the_api(page: tuple[int, str, str]) -> None:
    html = page[2]
    for endpoint in ("/render", "/edit", "/undo", "/redo", "/replace", "/save", "/document"):
        assert endpoint in html, endpoint
    assert "addEventListener" in html and "setTimeout" in html


def test_ac4_command_line_serves_the_file(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("# Hi\n", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "mdedit", str(doc), "--port", "0", "--no-browser"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout is not None
        line = proc.stdout.readline().strip()
        match = LINE.match(line)
        assert match, line
        assert match["file"] == str(doc) and int(match["port"]) > 0
        deadline = time.monotonic() + 10
        while True:
            try:
                status, _, html = fetch(f"http://127.0.0.1:{match['port']}/")
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(0.2)
        assert status == 200 and 'id="editor"' in html
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_ac5_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mdedit", "--help"],
        check=False,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    for word in ("FILE", "--port", "--no-browser"):
        assert word in result.stdout, word
