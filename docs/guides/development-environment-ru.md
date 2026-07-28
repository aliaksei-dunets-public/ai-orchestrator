---
language: ru
translation_of: docs/guides/development-environment.md
---

# Локальное Python-окружение

[English version](development-environment.md)

Проект требует Python 3.11 или новее и использует стандартную библиотеку
Python. Для разработки и проверок используется локальное виртуальное
окружение `.venv`, которое не добавляется в Git.

## Создание окружения

Из корня репозитория в PowerShell:

```powershell
py -3.12 -m venv .venv
```

Python 3.11+ также подходит. Если команда `py` недоступна, используйте
полный путь к установленному `python.exe` версии 3.11 или новее.

Проверка окружения:

```powershell
.\.venv\Scripts\python.exe --version
```

Команды можно выполнять через явный путь к интерпретатору без активации
окружения. Это устраняет зависимость от глобального `PATH`:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Установка локального пакета

Runtime-зависимости проекта отсутствуют. Если нужны console entry points
`orchestrator` и `orchestrator-task` или editable-install, установите build
зависимость и локальный пакет:

```powershell
.\.venv\Scripts\python.exe -m pip install "setuptools>=68"
.\.venv\Scripts\python.exe -m pip install --no-build-isolation -e .
```

Опция `--no-build-isolation` использует уже установленный `setuptools` и не
запускает дополнительную попытку скачать build-зависимости во временное
окружение.

## Проверки

Минимальная проверка перед работой:

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

`.venv/` добавлен в `.gitignore`; его содержимое не нужно коммитить.
