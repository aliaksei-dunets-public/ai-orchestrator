---
language: en
translation_of: docs/guides/development-environment-ru.md
---

# Local Python environment

The project requires Python 3.11 or newer and uses the standard library for
runtime paths. Development and validation use the repository-local `.venv`,
which is not committed.

## Create the environment

From the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
```

Python 3.11+ is also supported. Verify the interpreter explicitly:

```powershell
.\.venv\Scripts\python.exe --version
```

Commands may use the explicit interpreter without activation:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Install the local package

Runtime dependencies are not required. To install console entry points or an
editable package:

```powershell
.\.venv\Scripts\python.exe -m pip install "setuptools>=68"
.\.venv\Scripts\python.exe -m pip install --no-build-isolation -e .
```

`--no-build-isolation` reuses the installed build dependency and avoids a
second build-environment download.

## Checks

Run the minimum validation before work:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

`.venv/` is ignored by Git and must not be committed.
