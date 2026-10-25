# mdedit holdout

The acceptance tests for each issue, written by humans. The factory copies
`tests/acceptance/` into a change only to run the full suite; its builders work
from `main` and never see this branch. Each issue lists the test ids it must pass.
