"""Unit tests for mdedit.server (spec 7 — editor HTTP API)."""

import http.client
import json
import logging
import socket
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from mdedit.blocks import render_blocks
from mdedit.inline import render_inline
from mdedit.search import replace_all
from mdedit.server import make_server
from mdedit.stats import char_count, outline, reading_minutes, word_count

JSON_TYPE = "application/json; charset=utf-8"


@contextmanager
def serving(document: Path | None) -> Iterator[ThreadingHTTPServer]:
    """Run a server for ``document`` in a background thread while the block runs."""
    server = make_server(document)
    thread = threading.Thread(
        target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
    )
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def address(server: ThreadingHTTPServer) -> tuple[str, int]:
    host, port = server.server_address[:2]
    assert isinstance(host, str)
    return host, port


def call(
    server: ThreadingHTTPServer,
    method: str,
    path: str,
    body: object = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, object]]:
    """Send one request and return the status and the decoded JSON object answered.

    ``body`` is sent as is when it is bytes, as JSON otherwise, and not at all when None.
    Every answer must be a JSON object with the JSON content type.
    """
    host, port = address(server)
    payload = body if body is None or isinstance(body, bytes) else json.dumps(body).encode()
    connection = http.client.HTTPConnection(host, port, timeout=10)
    try:
        connection.request(method, path, body=payload, headers=headers or {})
        response = connection.getresponse()
        data = response.read()
        assert response.getheader("Content-Type") == JSON_TYPE
        answer = json.loads(data)
        assert isinstance(answer, dict)
        return response.status, answer
    finally:
        connection.close()


def assert_error(answer: dict[str, object]) -> None:
    assert set(answer) == {"error"}
    message = answer["error"]
    assert isinstance(message, str)
    assert message
    assert "Traceback" not in message


# AC1


def test_make_server_binds_loopback_on_a_free_port_without_serving() -> None:
    server = make_server(None)
    other = make_server(None)
    try:
        assert isinstance(server, ThreadingHTTPServer)
        host, port = address(server)
        assert host == "127.0.0.1"
        assert server.socket.getsockname()[0] == "127.0.0.1"
        assert port > 0
        assert address(other)[1] != port

        with socket.create_connection((host, port), timeout=5) as client:
            client.sendall(b"GET /document HTTP/1.0\r\n\r\n")
            client.settimeout(0.3)
            # The socket listens, but nothing answers until the server is told to serve.
            with pytest.raises(TimeoutError):
                client.recv(1)

            server.handle_request()
            client.settimeout(5)
            received = b""
            while chunk := client.recv(4096):
                received += chunk
        assert received.startswith(b"HTTP/1.0 200")
    finally:
        server.server_close()
        other.server_close()


# AC2


def test_render_returns_html_stats_and_outline() -> None:
    text = (
        "# Title\n\nSome *emphasis* and [a link](http://example.test).\n\n"
        "## Part two ##\n\n```\n# not a heading\n```\n\n" + "word " * 401
    )
    with serving(None) as server:
        status, answer = call(server, "POST", "/render", {"text": text})

    assert status == 200
    assert answer == {
        "html": render_blocks(text, inline=render_inline),
        "words": word_count(text),
        "chars": char_count(text),
        "minutes": reading_minutes(text),
        "outline": [[level, title] for level, title in outline(text)],
    }
    assert answer["outline"] == [[1, "Title"], [2, "Part two"]]
    assert answer["minutes"] == 3
    html = answer["html"]
    assert isinstance(html, str)
    assert "<em>emphasis</em>" in html
    assert '<a href="http://example.test">a link</a>' in html


def test_render_of_empty_text_is_empty() -> None:
    with serving(None) as server:
        status, answer = call(server, "POST", "/render", {"text": ""})

    assert status == 200
    assert answer == {"html": "", "words": 0, "chars": 0, "minutes": 0, "outline": []}


# AC3


def test_document_reads_utf8_with_newlines_as_lf(tmp_path: Path) -> None:
    document = tmp_path / "notes.md"
    document.write_bytes("café — one\r\ntwo\rthree\n\r\n".encode())

    with serving(document) as server:
        status, answer = call(server, "GET", "/document")
        assert status == 200
        assert answer == {"path": str(document), "text": "café — one\ntwo\nthree\n\n"}

        # The file is read at the time of each request.
        document.write_bytes(b"changed\r\n")
        status, answer = call(server, "GET", "/document")
        assert status == 200
        assert answer == {"path": str(document), "text": "changed\n"}


def test_document_without_document_or_missing_file_is_empty(tmp_path: Path) -> None:
    with serving(None) as server:
        status, answer = call(server, "GET", "/document")
    assert status == 200
    assert answer == {"path": None, "text": ""}

    document = tmp_path / "not-yet.md"
    with serving(document) as server:
        status, answer = call(server, "GET", "/document")
        assert status == 200
        assert answer == {"path": str(document), "text": ""}

        document.write_text("now here", encoding="utf-8")
        status, answer = call(server, "GET", "/document")
        assert status == 200
        assert answer == {"path": str(document), "text": "now here"}


def test_document_that_is_not_utf8_answers_json_error(tmp_path: Path) -> None:
    document = tmp_path / "notes.md"
    with serving(document) as server:
        document.write_bytes(b"\xff\xfe not utf-8")
        status, answer = call(server, "GET", "/document")

    assert status == 500
    assert_error(answer)


# AC4


def test_edit_records_history_from_document_text(tmp_path: Path) -> None:
    document = tmp_path / "notes.md"
    document.write_bytes(b"a\r\nb")

    with serving(document) as server:
        # The history starts from the text /document answers, so this is no change.
        status, answer = call(server, "POST", "/edit", {"text": "a\nb"})
        assert status == 200
        assert answer == {"can_undo": False, "can_redo": False}

        status, answer = call(server, "POST", "/edit", {"text": "a\nbc"})
        assert status == 200
        assert answer == {"can_undo": True, "can_redo": False}

        status, answer = call(server, "POST", "/undo")
        assert status == 200
        assert answer == {"text": "a\nb", "can_undo": False, "can_redo": True}

        status, answer = call(server, "POST", "/edit", {"text": "x"})
        assert status == 200
        assert answer == {"can_undo": True, "can_redo": False}

        # Editing never touches the file.
        assert document.read_bytes() == b"a\r\nb"


def test_history_of_missing_document_starts_empty(tmp_path: Path) -> None:
    with serving(tmp_path / "missing.md") as server:
        status, answer = call(server, "POST", "/edit", {"text": ""})
        assert status == 200
        assert answer == {"can_undo": False, "can_redo": False}


# AC5


def test_undo_and_redo_return_states_and_409_when_nothing_left() -> None:
    with serving(None) as server:
        for path in ("/undo", "/redo"):
            status, answer = call(server, "POST", path)
            assert status == 409
            assert_error(answer)

        call(server, "POST", "/edit", {"text": "one"})
        call(server, "POST", "/edit", {"text": "two"})

        status, answer = call(server, "POST", "/undo", b"any body at all")
        assert status == 200
        assert answer == {"text": "one", "can_undo": True, "can_redo": True}

        status, answer = call(server, "POST", "/undo", {"text": "ignored"})
        assert status == 200
        assert answer == {"text": "", "can_undo": False, "can_redo": True}

        status, answer = call(server, "POST", "/undo")
        assert status == 409
        assert_error(answer)

        # The refused undo left the history where it was.
        status, answer = call(server, "POST", "/redo", b"")
        assert status == 200
        assert answer == {"text": "one", "can_undo": True, "can_redo": True}

        status, answer = call(server, "POST", "/redo", b"[not json")
        assert status == 200
        assert answer == {"text": "two", "can_undo": True, "can_redo": False}

        status, answer = call(server, "POST", "/redo")
        assert status == 409
        assert_error(answer)

        status, answer = call(server, "POST", "/undo")
        assert status == 200
        assert answer == {"text": "one", "can_undo": True, "can_redo": True}


# AC6


def test_replace_returns_text_and_count_and_400_on_value_error() -> None:
    text = "Cat cat category cat"
    cases: list[tuple[dict[str, object], tuple[str, int]]] = [
        ({"text": text, "query": "cat", "replacement": "dog"}, ("Cat dog dogegory dog", 3)),
        (
            {"text": text, "query": "cat", "replacement": "dog", "case_sensitive": False},
            ("dog dog dogegory dog", 4),
        ),
        (
            {"text": text, "query": "cat", "replacement": "dog", "whole_word": True},
            ("Cat dog category dog", 2),
        ),
        (
            {"text": "a1 b22", "query": r"([a-z])(\d+)", "replacement": r"\2\1", "regex": True},
            ("1a 22b", 2),
        ),
        (
            {"text": "a.c abc", "query": "a.c", "replacement": "x", "regex": False},
            ("x abc", 1),
        ),
        ({"text": text, "query": "CAT", "replacement": "x", "case_sensitive": True}, (text, 0)),
    ]
    with serving(None) as server:
        for request, expected in cases:
            status, answer = call(server, "POST", "/replace", request)
            assert status == 200
            assert answer == {"text": expected[0], "count": expected[1]}
            options = {
                name: bool(value)
                for name, value in request.items()
                if name in ("case_sensitive", "whole_word", "regex")
            }
            assert expected == replace_all(
                str(request["text"]), str(request["query"]), str(request["replacement"]), **options
            )

        for bad in (
            {"text": text, "query": "", "replacement": "x"},
            {"text": text, "query": "(", "replacement": "x", "regex": True},
            {"text": text, "query": "c(a)t", "replacement": r"\9", "regex": True},
        ):
            status, answer = call(server, "POST", "/replace", bad)
            assert status == 400
            assert_error(answer)

        # Neither kind of answer changed the session's history.
        status, answer = call(server, "POST", "/undo")
        assert status == 409
        status, answer = call(server, "POST", "/edit", {"text": ""})
        assert answer == {"can_undo": False, "can_redo": False}


# AC7


def test_save_writes_exact_utf8_bytes_and_409_without_document(tmp_path: Path) -> None:
    document = tmp_path / "new.md"
    text = "café\r\nline\rlast\n☃"

    with serving(document) as server:
        status, answer = call(server, "POST", "/save", {"text": text})
        assert status == 200
        assert answer == {"saved": True, "bytes": len(text.encode("utf-8"))}
        assert document.read_bytes() == text.encode("utf-8")

        status, answer = call(server, "POST", "/save", {"text": "short"})
        assert status == 200
        assert answer == {"saved": True, "bytes": 5}
        assert document.read_bytes() == b"short"

        status, answer = call(server, "POST", "/save", {"text": ""})
        assert status == 200
        assert answer == {"saved": True, "bytes": 0}
        assert document.read_bytes() == b""

    before = sorted(tmp_path.iterdir())
    with serving(None) as server:
        status, answer = call(server, "POST", "/save", {"text": "nowhere"})
    assert status == 409
    assert_error(answer)
    assert sorted(tmp_path.iterdir()) == before


def test_save_of_text_that_is_not_encodable_answers_400(tmp_path: Path) -> None:
    document = tmp_path / "notes.md"
    with serving(document) as server:
        status, answer = call(server, "POST", "/save", b'{"text": "lone \\ud800 surrogate"}')

    assert status == 400
    assert_error(answer)
    assert not document.exists()


# AC8


def test_bad_bodies_answer_400_and_unknown_paths_404_as_json(tmp_path: Path) -> None:
    document = tmp_path / "notes.md"
    document.write_bytes(b"keep")
    not_objects: list[object] = [
        None,
        b"",
        b"not json",
        b"\xff\xfe",
        b"[1, 2]",
        b'"text"',
        b"null",
        {},
        {"text": 1},
        {"text": None},
        {"text": ["a"]},
        {"other": "a"},
    ]
    replace_bodies: list[dict[str, object]] = [
        {"query": "a", "replacement": "b"},
        {"text": "a", "replacement": "b"},
        {"text": "a", "query": "a"},
        {"text": "a", "query": 1, "replacement": "b"},
        {"text": "a", "query": "a", "replacement": None},
        {"text": "a", "query": "a", "replacement": "b", "case_sensitive": "yes"},
        {"text": "a", "query": "a", "replacement": "b", "whole_word": 1},
        {"text": "a", "query": "a", "replacement": "b", "regex": None},
    ]

    with serving(document) as server:
        for path in ("/render", "/edit", "/replace", "/save"):
            for body in not_objects:
                status, answer = call(server, "POST", path, body)
                assert status == 400, (path, body)
                assert_error(answer)
        for body in replace_bodies:
            status, answer = call(server, "POST", "/replace", body)
            assert status == 400, body
            assert_error(answer)

        for method, path in (
            ("GET", "/"),
            ("GET", "/nope"),
            ("POST", "/nope"),
            ("GET", "/render"),
            ("GET", "/save"),
            ("GET", "/undo"),
            ("POST", "/document"),
            ("GET", "/document/"),
        ):
            body = {"text": "x"} if method == "POST" else None
            status, answer = call(server, method, path, body)
            assert status == 404, (method, path)
            assert_error(answer)

        # None of the refused requests reached the history or the file.
        status, answer = call(server, "POST", "/undo")
        assert status == 409
    assert document.read_bytes() == b"keep"


def test_errors_raised_by_http_server_answer_json_too() -> None:
    with serving(None) as server:
        status, answer = call(server, "PUT", "/document", b"x")
        assert status == 501
        assert_error(answer)

        host, port = address(server)
        with socket.create_connection((host, port), timeout=5) as client:
            client.sendall(b"GET /document extra HTTP/1.1\r\n\r\n")
            received = b""
            while chunk := client.recv(4096):
                received += chunk

    head, _, body = received.partition(b"\r\n\r\n")
    assert head.startswith(b"HTTP/1.0 400")
    assert b"Content-Type: " + JSON_TYPE.encode() in head
    assert_error(json.loads(body))


def test_unexpected_failure_answers_json_500_and_logs_the_traceback(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def broken(text: str) -> int:
        raise RuntimeError("secret detail")

    monkeypatch.setattr("mdedit.server.word_count", broken)
    with caplog.at_level(logging.ERROR, logger="mdedit.server"), serving(None) as server:
        status, answer = call(server, "POST", "/render", {"text": "hi"})

    assert status == 500
    assert_error(answer)
    assert "secret detail" not in str(answer["error"])
    assert any(record.exc_info for record in caplog.records)


def test_malformed_content_length_answers_400() -> None:
    with serving(None) as server:
        host, port = address(server)
        with socket.create_connection((host, port), timeout=5) as client:
            client.sendall(b"POST /render HTTP/1.1\r\nContent-Length: -2\r\n\r\n{}")
            received = b""
            while chunk := client.recv(4096):
                received += chunk

    head, _, body = received.partition(b"\r\n\r\n")
    assert head.startswith(b"HTTP/1.0 400")
    assert_error(json.loads(body))


def test_query_strings_do_not_change_the_route() -> None:
    with serving(None) as server:
        status, answer = call(server, "GET", "/document?fresh=1")
    assert status == 200
    assert answer == {"path": None, "text": ""}


def test_chunked_request_body_is_read() -> None:
    def chunks() -> Iterable[bytes]:
        yield b'{"text": '
        yield b'"# Hi"}'

    with serving(None) as server:
        host, port = address(server)
        connection = http.client.HTTPConnection(host, port, timeout=10)
        try:
            connection.request("POST", "/render", body=chunks(), encode_chunked=True)
            response = connection.getresponse()
            status, answer = response.status, json.loads(response.read())
        finally:
            connection.close()

    assert status == 200
    assert answer["outline"] == [[1, "Hi"]]


def test_requests_from_other_sites_are_refused(tmp_path: Path) -> None:
    document = tmp_path / "notes.md"
    document.write_bytes(b"mine")

    with serving(document) as server:
        host, port = address(server)
        # A page on another site posting to the editor (cross-site request forgery).
        status, answer = call(
            server, "POST", "/save", {"text": "pwned"}, {"Origin": "http://evil.test"}
        )
        assert status == 403
        assert_error(answer)

        # A page whose own name was rebound to the loopback address (DNS rebinding).
        status, answer = call(server, "GET", "/document", None, {"Host": f"evil.test:{port}"})
        assert status == 403
        assert_error(answer)

        # The editor's own page is served from this origin.
        for name in (host, "localhost"):
            status, answer = call(
                server,
                "GET",
                "/document",
                None,
                {"Host": f"{name}:{port}", "Origin": f"http://{name}:{port}"},
            )
            assert status == 200
            assert answer == {"path": str(document), "text": "mine"}

    assert document.read_bytes() == b"mine"
