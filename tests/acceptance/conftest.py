"""Holdout collection rule for parallel tasks.

Each ``test_<n>_*.py`` holds the acceptance tests of issue n. The factory copies this whole
folder into a task's worktree for the full suite, and several issues are in flight at once,
each on its own ``agent/<n>`` branch made from ``main``.

- The task's own file (``n`` from the branch name) always runs: a missing or misnamed module
  fails the suite, as it must.
- Another issue's file runs once that issue's module exists on this branch (it merged). Until
  then it is left out, so a task's full suite does not fail on modules no one has built yet.
"""

import importlib.util
import re
import subprocess
from pathlib import Path

ISSUE_FILE = re.compile(r"^test_(\d+)_")
BRANCH = re.compile(r"^agent/(\d+)$")
MODULE = {
    1: "mdedit.buffer",
    2: "mdedit.history",
    3: "mdedit.inline",
    4: "mdedit.blocks",
    5: "mdedit.search",
    6: "mdedit.stats",
    7: "mdedit.server",
    8: "mdedit.page",
}


def _own_issue(root: Path) -> int | None:
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None
    match = BRANCH.match(branch)
    return int(match.group(1)) if match else None


def _built(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except ModuleNotFoundError:
        return False


def pytest_ignore_collect(collection_path: Path) -> bool | None:
    match = ISSUE_FILE.match(collection_path.name)
    if match is None or collection_path.suffix != ".py":
        return None
    issue = int(match.group(1))
    if issue == _own_issue(collection_path.parent):
        return None
    module = MODULE.get(issue)
    if module is None or _built(module):
        return None
    return True
