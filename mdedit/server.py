"""The editor's local HTTP API: JSON over the standard library's ``http.server``.

``make_server`` returns a server for one document that is bound but not yet serving;
the caller runs ``serve_forever``. Requests and answers are JSON objects, and every
answer, errors included, is sent as ``application/json; charset=utf-8``. An error
answer is ``{"error": message}``.

- ``GET /document`` answers ``{"path", "text"}``: the document's path and its text as
  UTF-8 with every line ending read as ``"\\n"``.
- ``POST /render`` takes ``{"text"}`` and answers ``{"html", "words", "chars",
  "minutes", "outline"}``.
- ``POST /edit`` takes ``{"text"}``, records it in the undo history and answers
  ``{"can_undo", "can_redo"}``.
- ``POST /undo`` and ``POST /redo`` ignore their body and answer ``{"text",
  "can_undo", "can_redo"}``, or 409 when there is nothing to undo or redo.
- ``POST /replace`` takes ``{"text", "query", "replacement"}`` and the optional
  booleans ``case_sensitive``, ``whole_word`` and ``regex``, and answers ``{"text",
  "count"}``, or 400 for a query or replacement ``replace_all`` rejects.
- ``POST /save`` takes ``{"text"}``, writes it to the document as UTF-8 and answers
  ``{"saved", "bytes"}``, or 409 without a document.

A body that is not a JSON object with the fields a route needs is answered with 400,
and any other method and path with 404. So that a web page on another site cannot use
the user's browser to read or overwrite the document, a request whose ``Origin`` is not
the server's own, or whose ``Host`` is not one of the server's names, gets 403.
"""

import json
import logging
import re
import socket
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from mdedit.blocks import render_blocks
from mdedit.history import History
from mdedit.inline import render_inline
from mdedit.search import replace_all
from mdedit.stats import char_count, outline, reading_minutes, word_count

__all__ = ["MAX_BODY_BYTES", "make_server"]

MAX_BODY_BYTES = 64 * 1024 * 1024
"""The largest request body the server reads; a larger one is answered with 413."""

_logger = logging.getLogger(__name__)

_CONTENT_TYPE = "application/json; charset=utf-8"
_REPLACE_OPTIONS = ("case_sensitive", "whole_word", "regex")

# Host names that always mean this machine, and the addresses that bind every
# interface (a server bound to those answers whatever name it is reached by).
_LOOPBACK_NAMES = frozenset({"localhost", "127.0.0.1"})
_ANY_ADDRESS = frozenset({"", "0.0.0.0"})

_CONTENT_LENGTH = re.compile(r"[0-9]{1,18}")
# A chunk-size line of a chunked body: hex digits, optional extensions, line end.
_CHUNK_SIZE = re.compile(rb"([0-9A-Fa-f]{1,16})[ \t]*(?:;[^\r\n]*)?\r?\n")
_LINE_ENDS = (b"\r\n", b"\n")
_MAX_LINE = 65536
_MAX_TRAILERS = 100

# How long, and for how many bytes, a closing connection reads what the client still
# sends, so that closing it does not reset the connection (see _Handler.finish).
_LINGER_SECONDS = 2.0
_LINGER_BYTES = 1024 * 1024

type _Answer = tuple[int, dict[str, object]]


class _Refusal(Exception):
    """A request answered with an error ``status`` and ``{"error": message}``."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def make_server(
    document: Path | None, host: str = "127.0.0.1", port: int = 0
) -> ThreadingHTTPServer:
    """Return a server for the editor's API on ``host:port``, bound but not yet serving.

    Call ``serve_forever`` to answer requests and ``server_close`` when done. With
    ``port=0`` the system picks a free port, which ``server.server_address`` holds. The
    session's undo history starts from the text ``GET /document`` would answer now.

    Raises ``OSError`` if the document cannot be read or the address cannot be bound,
    and ``UnicodeDecodeError`` if the document is not UTF-8.
    """
    return _EditorServer((host, port), _Session(document))


def _read_document(document: Path | None) -> str:
    """Return the document's text as ``GET /document`` answers it.

    The file is decoded as UTF-8 and every ``"\\r\\n"`` and lone ``"\\r"`` becomes
    ``"\\n"``. Without a document, or before its file exists, the text is ``""``.
    """
    if document is None:
        return ""
    try:
        with open(document, "rb") as file:
            raw = file.read()
    except FileNotFoundError:
        return ""
    return raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


class _Session:
    """The document one server edits and its undo history.

    ``lock`` serialises every use of the history and of the document's file across
    the server's request threads.
    """

    def __init__(self, document: Path | None) -> None:
        self.document = document
        self.history = History(_read_document(document))
        self.lock = threading.Lock()


# Routes. Each takes the session and the raw request body and returns the answer.


def _render(session: _Session, body: bytes) -> _Answer:
    text = _string(_json_object(body), "text")
    return 200, {
        "html": render_blocks(text, inline=render_inline),
        "words": word_count(text),
        "chars": char_count(text),
        "minutes": reading_minutes(text),
        "outline": [[level, title] for level, title in outline(text)],
    }


def _document(session: _Session, body: bytes) -> _Answer:
    path = None if session.document is None else str(session.document)
    try:
        with session.lock:
            text = _read_document(session.document)
    except (OSError, UnicodeDecodeError) as exc:
        raise _Refusal(500, f"cannot read {path}: {exc}") from None
    return 200, {"path": path, "text": text}


def _edit(session: _Session, body: bytes) -> _Answer:
    text = _string(_json_object(body), "text")
    with session.lock:
        session.history.record(text)
        return 200, {"can_undo": session.history.can_undo, "can_redo": session.history.can_redo}


def _undo(session: _Session, body: bytes) -> _Answer:
    return _step(session, History.undo)


def _redo(session: _Session, body: bytes) -> _Answer:
    return _step(session, History.redo)


def _step(session: _Session, move: Callable[[History], str]) -> _Answer:
    """Move the history back or forward; 409 leaves it as it was when it cannot move."""
    with session.lock:
        history = session.history
        try:
            text = move(history)
        except LookupError as exc:
            raise _Refusal(409, str(exc)) from None
        return 200, {"text": text, "can_undo": history.can_undo, "can_redo": history.can_redo}


def _replace(session: _Session, body: bytes) -> _Answer:
    request = _json_object(body)
    text = _string(request, "text")
    query = _string(request, "query")
    replacement = _string(request, "replacement")
    # Absent options are left out so that replace_all's own defaults apply.
    options = {name: _boolean(request, name) for name in _REPLACE_OPTIONS if name in request}
    try:
        new_text, count = replace_all(text, query, replacement, **options)
    except ValueError as exc:
        raise _Refusal(400, str(exc)) from None
    return 200, {"text": new_text, "count": count}


def _save(session: _Session, body: bytes) -> _Answer:
    text = _string(_json_object(body), "text")
    if session.document is None:
        raise _Refusal(409, "there is no document to save to")
    try:
        data = text.encode("utf-8")
    except UnicodeEncodeError:
        raise _Refusal(400, '"text" is not valid Unicode: it holds a lone surrogate') from None
    with session.lock:
        try:
            # Binary mode writes the bytes exactly, with no newline translation.
            with open(session.document, "wb") as file:
                file.write(data)
        except OSError as exc:
            raise _Refusal(500, f"cannot save {session.document}: {exc}") from None
    return 200, {"saved": True, "bytes": len(data)}


_ROUTES: dict[tuple[str, str], Callable[[_Session, bytes], _Answer]] = {
    ("GET", "/document"): _document,
    ("POST", "/render"): _render,
    ("POST", "/edit"): _edit,
    ("POST", "/undo"): _undo,
    ("POST", "/redo"): _redo,
    ("POST", "/replace"): _replace,
    ("POST", "/save"): _save,
}


def _json_object(body: bytes) -> dict[str, Any]:
    try:
        value = json.loads(body.decode("utf-8"))
    except (ValueError, RecursionError) as exc:
        raise _Refusal(400, f"the request body is not valid JSON: {exc}") from None
    if not isinstance(value, dict):
        raise _Refusal(400, "the request body must be a JSON object")
    return value


def _string(request: dict[str, Any], name: str) -> str:
    value = request.get(name)
    if not isinstance(value, str):
        raise _Refusal(400, f'"{name}" must be a string')
    return value


def _boolean(request: dict[str, Any], name: str) -> bool:
    value = request[name]
    if not isinstance(value, bool):
        raise _Refusal(400, f'"{name}" must be true or false')
    return value


def _host_name(host: str) -> str:
    """Return the lower-case name in a ``Host`` header, without its port."""
    host = host.strip().lower()
    if host.startswith("["):
        return host.partition("]")[0] + "]"
    return host.partition(":")[0]


class _EditorServer(ThreadingHTTPServer):
    """A ``ThreadingHTTPServer`` that holds one editing session."""

    def __init__(self, address: tuple[str, int], session: _Session) -> None:
        self.session = session
        super().__init__(address, _Handler)
        host = address[0]
        bound = str(self.server_address[0])
        # The names a request may address this server by; None accepts any name.
        self.host_names: frozenset[str] | None = (
            None if host in _ANY_ADDRESS else _LOOPBACK_NAMES | {host.lower(), bound.lower()}
        )


class _Handler(BaseHTTPRequestHandler):
    """Answer the requests of one connection with JSON."""

    server: _EditorServer

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def send_error(self, code: int, message: str | None = None, explain: str | None = None) -> None:
        """Answer the errors ``http.server`` finds itself, such as a malformed request, as JSON."""
        self.close_connection = True
        if message is None:
            message = self.responses.get(code, ("Error", ""))[0]
        self._send_json(code, {"error": message})

    def log_request(self, code: int | str = "-", size: int | str = "-") -> None:
        """Log nothing for a request answered; the page sends one on every keystroke."""

    def finish(self) -> None:
        """End the answer, then read what the client still sends before the socket closes.

        Closing a socket that holds unread request bytes resets the connection, and the
        client can then lose the answer before it reads it. That happens whenever a
        request is refused before its body is read (a malformed request, an unsupported
        method). So the server ends its side first, which the client sees as the end of
        the answer, and reads until the client closes, for a bounded time and size.
        """
        super().finish()
        connection: socket.socket = self.connection
        deadline = time.monotonic() + _LINGER_SECONDS
        received = 0
        try:
            connection.shutdown(socket.SHUT_WR)
            while received < _LINGER_BYTES and (left := deadline - time.monotonic()) > 0:
                connection.settimeout(left)
                data = connection.recv(65536)
                if not data:
                    break
                received += len(data)
        except OSError:
            pass  # The client has gone or kept sending too long; close the socket anyway.

    def _handle(self) -> None:
        try:
            body = self._read_body()
            self._check_origin()
            route = _ROUTES.get((self.command, self.path.partition("?")[0]))
            if route is None:
                raise _Refusal(404, f"no such route: {self.command} {self.path}")
            status, answer = route(self.server.session, body)
        except _Refusal as refusal:
            status, answer = refusal.status, {"error": refusal.message}
        except Exception:
            # The traceback goes to the server's log; the client gets a JSON error.
            _logger.exception("%s %s failed", self.command, self.path)
            status, answer = 500, {"error": "internal server error"}
        self._send_json(status, answer)

    def _read_body(self) -> bytes:
        """Read the whole request body, whether or not the route uses it."""
        encoding = self.headers.get("Transfer-Encoding")
        if encoding is not None:
            if encoding.strip().lower() != "chunked":
                raise self._framing_error(501, f"unsupported Transfer-Encoding {encoding!r}")
            return self._read_chunked()
        length = self.headers.get("Content-Length")
        if length is None:
            return b""
        if not _CONTENT_LENGTH.fullmatch(length.strip()):
            raise self._framing_error(400, f"invalid Content-Length {length!r}")
        size = int(length)
        if size > MAX_BODY_BYTES:
            raise self._framing_error(413, f"the request body exceeds {MAX_BODY_BYTES} bytes")
        body = self.rfile.read(size)
        if len(body) < size:
            raise self._framing_error(400, "the request body is shorter than its Content-Length")
        return body

    def _read_chunked(self) -> bytes:
        chunks: list[bytes] = []
        total = 0
        while True:
            line = _CHUNK_SIZE.fullmatch(self.rfile.readline(_MAX_LINE))
            if line is None:
                raise self._framing_error(400, "malformed chunked request body")
            size = int(line.group(1), 16)
            if size == 0:
                break
            total += size
            if total > MAX_BODY_BYTES:
                raise self._framing_error(413, f"the request body exceeds {MAX_BODY_BYTES} bytes")
            chunk = self.rfile.read(size)
            if len(chunk) < size or self.rfile.readline(_MAX_LINE) not in _LINE_ENDS:
                raise self._framing_error(400, "malformed chunked request body")
            chunks.append(chunk)
        # Skip the trailer fields, up to the empty line that ends the body.
        for _ in range(_MAX_TRAILERS):
            if self.rfile.readline(_MAX_LINE) in (*_LINE_ENDS, b""):
                return b"".join(chunks)
        raise self._framing_error(400, "too many trailer fields in the chunked request body")

    def _framing_error(self, status: int, message: str) -> _Refusal:
        """Refuse a body that could not be read whole; the connection cannot be reused."""
        self.close_connection = True
        return _Refusal(status, message)

    def _check_origin(self) -> None:
        """Refuse requests that a web page on another site makes through the browser.

        A browser names the page's origin in ``Origin`` and the server it believes it
        talks to in ``Host``. Only this server's own origin may send requests, which
        stops a page elsewhere from posting to ``/save``, and only this server's names
        may be in ``Host``, which stops a page whose name was rebound to the loopback
        address from reading ``/document``. A client that sends neither header is not
        a browser acting for a page.
        """
        host = self.headers.get("Host")
        names = self.server.host_names
        if host is not None and names is not None and _host_name(host) not in names:
            raise _Refusal(403, f"requests for host {host!r} are not answered")
        origin = self.headers.get("Origin")
        if origin is not None and (
            host is None or origin.strip().lower() != f"http://{host.strip().lower()}"
        ):
            raise _Refusal(403, f"requests from origin {origin!r} are not answered")

    def _send_json(self, status: int, answer: dict[str, object]) -> None:
        # json.dumps escapes every non-ASCII character, so the body is valid UTF-8 even
        # for text that holds a lone surrogate.
        data = json.dumps(answer).encode("ascii")
        try:
            self.send_response(status)
            self.send_header("Content-Type", _CONTENT_TYPE)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)
        except ConnectionError:
            # The client went away before reading the answer.
            self.close_connection = True
