"""Undo and redo through a bounded history of whole-document snapshots."""

from collections import deque

DEFAULT_LIMIT = 100


class History:
    """A linear undo/redo history of whole-document snapshots.

    ``current`` is the present state. Recording a state that differs from
    ``current`` pushes ``current`` onto the undo states, makes the new state
    ``current`` and discards every redo state. At most ``limit`` undo steps are
    kept; the oldest is dropped when a new one would exceed it.
    """

    def __init__(self, initial: str, limit: int = DEFAULT_LIMIT) -> None:
        if limit < 1:
            raise ValueError(f"limit must be at least 1, got {limit}")
        self._limit = limit
        self._current = initial
        self._undo: deque[str] = deque(maxlen=limit)
        self._redo: list[str] = []

    @property
    def current(self) -> str:
        """The present state."""
        return self._current

    @property
    def limit(self) -> int:
        """The maximum number of undo steps kept."""
        return self._limit

    @property
    def can_undo(self) -> bool:
        """Whether there is a state to undo to."""
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        """Whether there is a state to redo to."""
        return bool(self._redo)

    def record(self, state: str) -> None:
        """Make ``state`` current; a state equal to ``current`` changes nothing."""
        if state == self._current:
            return
        self._undo.append(self._current)
        self._redo.clear()
        self._current = state

    def undo(self) -> str:
        """Step back to the previous state, make it current and return it.

        Raises ``LookupError`` when there is nothing to undo.
        """
        if not self._undo:
            raise LookupError("nothing to undo")
        self._redo.append(self._current)
        self._current = self._undo.pop()
        return self._current

    def redo(self) -> str:
        """Step forward to the state last undone, make it current and return it.

        Raises ``LookupError`` when there is nothing to redo.
        """
        if not self._redo:
            raise LookupError("nothing to redo")
        self._undo.append(self._current)
        self._current = self._redo.pop()
        return self._current
