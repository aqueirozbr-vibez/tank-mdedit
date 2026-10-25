import json
import threading
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from mdedit.blocks import render_blocks
from mdedit.inline import render_inline
from mdedit.server import make_server
from mdedit.stats import char_count, reading_minutes, word_count

INITIAL = "# Notes\n\nfirst draft\n"


class Running:
    def __init__(self, document: Path | None) -> None:
        self.server = make_server(document)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address[:2]
        self.host = str(host)
        self.port = int(port)
        self.base = f"http://{self.host}:{self.port}"

    def raw(self, method: str, path: str, data: bytes | None = None) -> tuple[int, str, str]:
        request = urllib.request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return response.status, response.headers["Content-Type"], response.read().decode()
        except urllib.error.HTTPError as error:
            return error.code, error.headers["Content-Type"], error.read().decode()

    def call(self, method: str, path: str, body: object = None) -> tuple[int, Any]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        status, _, text = self.raw(method, path, data)
        return status, json.loads(text)

    def close(self) -> None:
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def doc(tmp_path: Path) -> Path:
    path = tmp_path / "notes.md"
    path.write_text(INITIAL, encoding="utf-8", newline="\n")
    return path


@pytest.fixture
def app(doc: Path) -> Iterator[Running]:
    running = Running(doc)
    yield running
    running.close()


def test_ac1_binds_loopback_on_a_free_port(app: Running) -> None:
    assert app.host == "127.0.0.1" and app.port > 0


def test_ac2_render(app: Running) -> None:
    text = "# T\n\nHello *world*, it's [here](notes.md)."
    status, content_type, body = app.raw("POST", "/render", json.dumps({"text": text}).encode())
    assert status == 200 and content_type.startswith("application/json")
    data = json.loads(body)
    assert data == {
        "html": render_blocks(text, inline=render_inline),
        "words": word_count(text),
        "chars": char_count(text),
        "minutes": reading_minutes(text),
        "outline": [[1, "T"]],
    }


def test_ac3_document(app: Running, doc: Path, tmp_path: Path) -> None:
    assert app.call("GET", "/document") == (200, {"path": str(doc), "text": INITIAL})
    empty = Running(None)
    missing = Running(tmp_path / "new.md")
    try:
        assert empty.call("GET", "/document") == (200, {"path": None, "text": ""})
        assert missing.call("GET", "/document") == (
            200,
            {"path": str(tmp_path / "new.md"), "text": ""},
        )
    finally:
        empty.close()
        missing.close()


def test_ac4_edit_records_history(app: Running) -> None:
    assert app.call("POST", "/edit", {"text": "a"}) == (200, {"can_undo": True, "can_redo": False})


def test_ac5_undo_and_redo(app: Running) -> None:
    app.call("POST", "/edit", {"text": "a"})
    assert app.call("POST", "/undo") == (
        200,
        {"text": INITIAL, "can_undo": False, "can_redo": True},
    )
    assert app.call("POST", "/redo") == (200, {"text": "a", "can_undo": True, "can_redo": False})
    status, body = app.call("POST", "/redo")
    assert status == 409 and isinstance(body["error"], str)
    app.call("POST", "/undo")
    status, body = app.call("POST", "/undo")
    assert status == 409 and isinstance(body["error"], str)


def test_ac6_replace(app: Running) -> None:
    assert app.call("POST", "/replace", {"text": "abcabc", "query": "bc", "replacement": "X"}) == (
        200,
        {"text": "aXaX", "count": 2},
    )
    assert app.call(
        "POST",
        "/replace",
        {
            "text": "cat concat",
            "query": "CAT",
            "replacement": "dog",
            "case_sensitive": False,
            "whole_word": True,
        },
    ) == (200, {"text": "dog concat", "count": 1})
    status, body = app.call(
        "POST", "/replace", {"text": "abc", "query": "(", "replacement": "x", "regex": True}
    )
    assert status == 400 and isinstance(body["error"], str)


def test_ac7_save(app: Running, doc: Path, tmp_path: Path) -> None:
    text = "é\nline two\n"
    assert app.call("POST", "/save", {"text": text}) == (
        200,
        {"saved": True, "bytes": len(text.encode("utf-8"))},
    )
    assert doc.read_bytes() == text.encode("utf-8")
    nowhere = Running(None)
    try:
        status, body = nowhere.call("POST", "/save", {"text": "x"})
        assert status == 409 and isinstance(body["error"], str)
    finally:
        nowhere.close()


def test_ac8_bad_requests(app: Running) -> None:
    status, _, text = app.raw("POST", "/render", b"not json")
    assert status == 400 and isinstance(json.loads(text)["error"], str)
    for bad in ([1, 2], {"text": 5}, {}):
        status, body = app.call("POST", "/render", bad)
        assert status == 400 and isinstance(body["error"], str)
    status, body = app.call("GET", "/nope")
    assert status == 404 and isinstance(body["error"], str)
