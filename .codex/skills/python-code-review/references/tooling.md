# Review Tooling Reference

Use repository-native commands whenever possible. Inspect `pyproject.toml`,
`tox.ini`, `noxfile.py`, `Makefile`, `Justfile`, CI workflows, and package-manager
configuration before choosing commands.

## Principles

1. Do not install or upgrade dependencies without explicit permission.
2. Do not rewrite files during review. Use check-only modes.
3. Prefer targeted checks before full-suite checks.
4. Record skipped checks and why they could not be run.
5. Distinguish pre-existing failures from regressions introduced by the scope.
6. Tool output is evidence to investigate, not an automatically valid finding.

## Environment and Project Discovery

Useful read-only inspection:

```bash
python --version
python -m pip --version
find . -maxdepth 2 -type f \
  \( -name 'pyproject.toml' -o -name 'tox.ini' -o -name 'noxfile.py' \
     -o -name 'setup.cfg' -o -name 'requirements*.txt' \
     -o -name 'Pipfile' -o -name 'poetry.lock' -o -name 'uv.lock' \) -print
```

Use the project's documented environment runner, for example `uv run`,
`poetry run`, `pipenv run`, `tox`, `nox`, or an existing virtual environment.
Do not guess that a particular package manager is authoritative.

## Tests

Examples, only when supported:

```bash
pytest path/to/test_file.py -q
pytest path/to/test_file.py::test_name -q
pytest -q
python -m unittest
nox -s tests
tox -e py
```

For changed-code review, start with focused tests and expand based on blast
radius. Preserve raw failures needed to distinguish environment problems from
code regressions.

## Lint and Formatting Checks

Examples:

```bash
ruff check .
ruff format --check .
black --check .
isort --check-only .
flake8
pylint package_name
```

Do not manually report every formatting error. Summarize tool status and report
only semantic or systemic issues that require reviewer judgment.

## Static Typing

Examples:

```bash
mypy package_name tests
pyright
basedpyright
```

Evaluate whether failures are in reviewed code, pre-existing, configuration-
related, or evidence of a real runtime contract mismatch.

## Security and Dependencies

Use only tools already available or configured:

```bash
bandit -r package_name
pip-audit
safety check
semgrep --config auto
```

Inspect lockfile changes manually for unexpected sources, packages, versions,
or weakened hashes. Do not claim a dependency is safe only because a scanner
found no known vulnerability.

## Coverage

Examples:

```bash
pytest --cov=package_name --cov-report=term-missing
coverage run -m pytest
coverage report -m
```

Coverage is useful for locating unexercised changed behavior. It is not a
quality score and does not prove assertions are meaningful.

## Complexity, Dead Code, and Performance

Use only when the review question warrants it:

```bash
vulture package_name
radon cc package_name
python -m cProfile script.py
pytest --durations=20
```

Treat dead-code and complexity reports as hypotheses. Dynamic imports,
framework registration, dependency injection, and plugin systems frequently
produce false positives.

## Git Review Commands

Read-only examples:

```bash
git status --short
git diff --check
git diff --stat <base>...<head>
git diff --name-status <base>...<head>
git diff --find-renames <base>...<head>
git show <sha>:path/to/file.py
git log --oneline --decorate <base>..<head>
git blame -L <start>,<end> path/to/file.py
```

Never use `git reset`, `git checkout` on the active tree, `git clean`, commit,
stash, rebase, or other state-changing commands during review.

## Evidence Recording

For every command record:

```text
Command:
Scope:
Exit status:
Result:
Relevance to verdict:
Limitations:
```
