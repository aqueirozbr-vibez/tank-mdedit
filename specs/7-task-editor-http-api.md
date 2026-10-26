# 7 — Editor HTTP API

risk: risk:high

## Outcome

Module `mdedit.server` gives the editor's browser page a local HTTP API built on mdedit's buffer, history, inline, blocks, search and stats modules: `make_server(document: Path | None, host: str = "127.0.0.1", port: int = 0) -> http.server.ThreadingHTTPServer` returns a server that is not yet serving. Requests and answers are JSON, every answer (errors included) carries `Content-Type: application/json; charset=utf-8`, and one server edits one document whose undo history (`mdedit.history.History`) starts from the document's text.

## Scope

- mdedit/server.py
- tests/unit/test_server.py

## Non-goals

- The HTML page and the command line (the next task).
- Any change to the other mdedit modules.
- Third-party packages; the standard library's `http.server` is enough.
- Any file under tests/acceptance/ (the holdout, written by humans).

## Acceptance criteria

1. WHEN `make_server` is called with the default host THE SYSTEM SHALL return a `ThreadingHTTPServer` that is bound to `127.0.0.1` only and not yet serving, and `port=0` SHALL pick a free port, readable from `server.server_address`.
2. WHEN `POST /render` receives `{"text": T}` THE SYSTEM SHALL answer 200 with `{"html": render_blocks(T, inline=render_inline), "words": word_count(T), "chars": char_count(T), "minutes": reading_minutes(T), "outline": [[level, title], ...]}`, where `outline` is `outline(T)` with each `(level, title)` pair as a two-element JSON array.
3. WHEN `GET /document` is called THE SYSTEM SHALL answer 200 with `{"path": str(document), "text": contents}`, where `path` is `null` without a document and `text` is the file's contents at the time of the request decoded as UTF-8, with every `"\r\n"` and lone `"\r"` read as `"\n"`, or `""` when there is no document or the file does not exist yet.
4. WHEN `POST /edit` receives `{"text": T}` THE SYSTEM SHALL record T with `History.record` in the session's `mdedit.history.History`, which was created from the text `GET /document` would have answered when `make_server` was called (so recording a T equal to the current state adds no undo step), and answer 200 with `{"can_undo": bool, "can_redo": bool}` read from that history after recording.
5. WHEN `POST /undo` or `POST /redo` is called, with any body or none, THE SYSTEM SHALL step the session's history back or forward and answer 200 with `{"text": state, "can_undo": bool, "can_redo": bool}`, where `state` is the history's new current state, or answer 409 with `{"error": message}` and leave the history unchanged when there is nothing to undo or redo.
6. WHEN `POST /replace` receives `{"text", "query", "replacement"}` and the optional booleans `case_sensitive`, `whole_word` and `regex` (absent ones take `replace_all`'s defaults: `true`, `false`, `false`) THE SYSTEM SHALL answer 200 with `{"text": new_text, "count": n}` from `replace_all`, and 400 with `{"error": message}` when `replace_all` raises `ValueError`, without changing the session's history in either case.
7. WHEN `POST /save` receives `{"text": T}` THE SYSTEM SHALL write T to the document exactly, so that the file's bytes are `T.encode("utf-8")` with no newline translation (creating the file when it does not exist yet), and answer 200 with `{"saved": true, "bytes": len(T.encode("utf-8"))}`; without a document it SHALL answer 409 with `{"error": message}` and write nothing.
8. WHEN a request body to `/render`, `/edit`, `/replace` or `/save` is not a JSON object with the required string fields (or `/replace` carries `case_sensitive`, `whole_word` or `regex` that is not a boolean) THE SYSTEM SHALL answer 400, and an unknown path (any GET or POST whose method and path are not one of the routes above) 404, each with `{"error": message}` and never a traceback.

## Constraints

No ADR applies.

## Open questions

None.

## Test plan

- AC1 -> tests/acceptance/test_7_server.py::test_ac1_binds_loopback_on_a_free_port
- AC1 unit -> tests/unit/test_server.py::test_make_server_binds_loopback_on_a_free_port_without_serving (the builder creates it)
- AC2 -> tests/acceptance/test_7_server.py::test_ac2_render
- AC2 unit -> tests/unit/test_server.py::test_render_returns_html_stats_and_outline (the builder creates it)
- AC3 -> tests/acceptance/test_7_server.py::test_ac3_document
- AC3 unit -> tests/unit/test_server.py::test_document_reads_utf8_with_newlines_as_lf (the builder creates it)
- AC3 unit -> tests/unit/test_server.py::test_document_without_document_or_missing_file_is_empty (the builder creates it)
- AC4 -> tests/acceptance/test_7_server.py::test_ac4_edit_records_history
- AC4 unit -> tests/unit/test_server.py::test_edit_records_history_from_document_text (the builder creates it)
- AC5 -> tests/acceptance/test_7_server.py::test_ac5_undo_and_redo
- AC5 unit -> tests/unit/test_server.py::test_undo_and_redo_return_states_and_409_when_nothing_left (the builder creates it)
- AC6 -> tests/acceptance/test_7_server.py::test_ac6_replace
- AC6 unit -> tests/unit/test_server.py::test_replace_returns_text_and_count_and_400_on_value_error (the builder creates it)
- AC7 -> tests/acceptance/test_7_server.py::test_ac7_save
- AC7 unit -> tests/unit/test_server.py::test_save_writes_exact_utf8_bytes_and_409_without_document (the builder creates it)
- AC8 -> tests/acceptance/test_7_server.py::test_ac8_bad_requests
- AC8 unit -> tests/unit/test_server.py::test_bad_bodies_answer_400_and_unknown_paths_404_as_json (the builder creates it)
