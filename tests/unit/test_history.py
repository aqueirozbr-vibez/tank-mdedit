"""Unit tests for mdedit.history.History (spec 2 — undo history)."""

import pytest

from mdedit.history import History


def test_fresh_history_has_current_and_nothing_to_undo_or_redo() -> None:
    history = History("a")

    assert history.current == "a"
    assert history.can_undo is False
    assert history.can_redo is False


def test_record_then_undo_restores_previous_state() -> None:
    history = History("a")

    history.record("ab")

    assert history.current == "ab"
    assert history.can_undo is True
    assert history.can_redo is False

    assert history.undo() == "a"
    assert history.current == "a"
    assert history.can_undo is False


def test_record_then_undo_walks_back_through_several_states() -> None:
    history = History("")
    for state in ("h", "he", "hel"):
        history.record(state)

    assert history.undo() == "he"
    assert history.undo() == "h"
    assert history.undo() == ""
    assert history.current == ""
    assert history.can_undo is False


def test_record_equal_to_current_keeps_undo_and_redo_states() -> None:
    history = History("a")
    history.record("b")
    history.record("c")
    assert history.undo() == "b"

    history.record("b")

    assert history.current == "b"
    assert history.can_undo is True
    assert history.can_redo is True
    # The redo state survives and the undo states are untouched.
    assert history.redo() == "c"
    assert history.undo() == "b"
    assert history.undo() == "a"
    assert history.can_undo is False


def test_record_equal_to_current_on_fresh_history_adds_no_undo_step() -> None:
    history = History("a")

    history.record("a")

    assert history.current == "a"
    assert history.can_undo is False
    assert history.can_redo is False


def test_undo_then_redo_restores_state_before_undo() -> None:
    history = History("a")
    history.record("b")
    history.record("c")

    assert history.undo() == "b"
    assert history.can_redo is True
    assert history.redo() == "c"
    assert history.current == "c"
    assert history.can_redo is False
    assert history.can_undo is True


def test_multiple_undos_then_redos_replay_in_order() -> None:
    history = History("a")
    history.record("b")
    history.record("c")

    assert history.undo() == "b"
    assert history.undo() == "a"
    assert history.redo() == "b"
    assert history.redo() == "c"
    assert history.current == "c"
    assert history.can_redo is False


def test_record_different_state_after_undo_discards_redo() -> None:
    history = History("a")
    history.record("b")
    history.record("c")
    history.undo()
    history.undo()
    assert history.can_redo is True

    history.record("x")

    assert history.current == "x"
    assert history.can_redo is False
    with pytest.raises(LookupError):
        history.redo()
    assert history.current == "x"
    assert history.undo() == "a"


def test_undo_or_redo_with_nothing_raises_lookup_error_and_keeps_current() -> None:
    history = History("a")

    with pytest.raises(LookupError):
        history.undo()
    assert history.current == "a"

    with pytest.raises(LookupError):
        history.redo()
    assert history.current == "a"

    history.record("b")
    with pytest.raises(LookupError):
        history.redo()
    assert history.current == "b"

    history.undo()
    with pytest.raises(LookupError):
        history.undo()
    assert history.current == "a"
    assert history.can_redo is True


def test_limit_keeps_only_most_recent_undo_steps() -> None:
    history = History("s0", limit=3)
    for state in ("s1", "s2", "s3", "s4", "s5"):
        history.record(state)

    assert history.undo() == "s4"
    assert history.undo() == "s3"
    assert history.undo() == "s2"
    assert history.can_undo is False
    with pytest.raises(LookupError):
        history.undo()
    assert history.current == "s2"

    # The steps undone remain redoable.
    assert history.redo() == "s3"
    assert history.redo() == "s4"
    assert history.redo() == "s5"
    assert history.can_redo is False


def test_limit_of_one_keeps_a_single_undo_step() -> None:
    history = History("a", limit=1)
    history.record("b")
    history.record("c")

    assert history.undo() == "b"
    with pytest.raises(LookupError):
        history.undo()


def test_limit_below_one_raises_value_error_and_default_is_100() -> None:
    for limit in (0, -1, -100):
        with pytest.raises(ValueError):
            History("a", limit=limit)

    history = History("s0")
    assert history.limit == 100
    for index in range(1, 102):
        history.record(f"s{index}")

    undone = [history.undo() for _ in range(100)]

    assert undone == [f"s{index}" for index in range(100, 0, -1)]
    assert history.can_undo is False
    with pytest.raises(LookupError):
        history.undo()
    assert history.current == "s1"


def test_explicit_limit_is_reported() -> None:
    assert History("a", limit=3).limit == 3
