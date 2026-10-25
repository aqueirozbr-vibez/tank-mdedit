import pytest

from mdedit.history import History


def test_ac1_fresh_history() -> None:
    h = History("a")
    assert h.current == "a" and h.can_undo is False and h.can_redo is False


def test_ac2_record_then_undo() -> None:
    h = History("a")
    h.record("b")
    assert h.current == "b" and h.can_undo is True
    assert h.undo() == "a" and h.current == "a"


def test_ac3_recording_the_current_state_changes_nothing() -> None:
    h = History("a")
    h.record("b")
    h.undo()
    h.record("a")
    assert h.can_redo is True and h.current == "a"
    assert h.redo() == "b"


def test_ac4_undo_then_redo() -> None:
    h = History("a")
    h.record("b")
    h.record("c")
    assert h.undo() == "b"
    assert h.redo() == "c" and h.current == "c" and h.can_redo is False


def test_ac5_record_after_undo_drops_redo() -> None:
    h = History("a")
    h.record("b")
    h.undo()
    h.record("z")
    assert h.can_redo is False and h.current == "z"
    with pytest.raises(LookupError):
        h.redo()


def test_ac6_nothing_to_undo_or_redo() -> None:
    h = History("a")
    with pytest.raises(LookupError):
        h.undo()
    with pytest.raises(LookupError):
        h.redo()
    assert h.current == "a"


def test_ac7_limit_keeps_the_most_recent_steps() -> None:
    h = History("s0", limit=3)
    for n in range(1, 6):
        h.record(f"s{n}")
    assert [h.undo(), h.undo(), h.undo()] == ["s4", "s3", "s2"]
    with pytest.raises(LookupError):
        h.undo()
    assert h.current == "s2"


def test_ac8_limit_validation_and_default() -> None:
    with pytest.raises(ValueError):
        History("a", limit=0)
    h = History("s0")
    for n in range(1, 151):
        h.record(f"s{n}")
    undone = 0
    while h.can_undo:
        h.undo()
        undone += 1
    assert undone == 100
