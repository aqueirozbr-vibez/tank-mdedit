# mdedit

A small text editor with a live markdown preview in the browser, built by the
Tank Factory: each GitHub issue is planned into a spec, built, reviewed
and opened as a pull request, and a human merges it.

- **Issues** say what each task must achieve: outcome, scope, non-goals,
  acceptance criteria and the ids of the hidden acceptance tests.
- **`specs/`** is where the factory's planner writes one spec per issue.
- **The `holdout` branch** holds the acceptance tests. Humans write them; the
  factory runs them against each change, and its builders never see them.
- Standard library only. Python 3.12, ruff, mypy strict, pytest.

Once every task has merged, run the editor with:

```
python -m mdedit notes.md
```
