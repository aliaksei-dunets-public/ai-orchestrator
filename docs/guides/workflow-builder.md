# Как собирать процессы с агентом

**Статус:** guide реализованного конструктора TASK-0036. Определения проверяются и экспортируются; команды ниже не выполняют тесты, не вызывают модели и не меняют Task Manager.

## Работа через skill

Проектный skill подключён в `.agents/skills/orchestrator-workflow-builder`. После обновления обнаружения навыков его можно выбрать как `$orchestrator-workflow-builder`. В текущей сессии агент также может прямо прочитать его SKILL.md. Каноническая переносимая копия лежит в `workflow-library/skills/orchestrator-workflow-builder`; инструкции хоста и пути подключения вне self-hosted проекта относятся к поставке.

Пример запроса: «Собери процесс: определить область тестов, выполнить проверки, разобрать результаты; если проверки прошли — проверить влияние на документацию и обновить её. Для разбора ошибок выбери expert, повторы тестов отключи. Покажи схему».

Агент подбирает блоки из каталога, уточняет недостающие контракты, создаёт TOML и проверяет его. Вы открываете HTML и изучаете конкретный узел или маршрут; по вашим поправкам агент меняет определение и повторно экспортирует схему.

## Проверенный пример

Команды выполняются из корня ядра с установленной `.venv`; ядро пока не поставляется wheel. Для внешнего проекта определения/overlay/выходы передавайте абсолютными путями, а `--library` направляйте на явно выбранные каталоги ядра и проекта.

```powershell
.venv\Scripts\python.exe -X utf8 -m orchestrator.workflow_builder catalog --library workflow-library
.venv\Scripts\python.exe -X utf8 -m orchestrator.workflow_builder validate workflow-library/workflows/testing-and-documentation.toml --library workflow-library --overlay workflow-library/examples/project-overlay.toml
.venv\Scripts\python.exe -X utf8 -m orchestrator.workflow_builder export workflow-library/workflows/testing-and-documentation.toml --library workflow-library --overlay workflow-library/examples/project-overlay.toml --json work/workflow-builder/process.json --html work/workflow-builder/process.html
```

Откройте [интерактивный пример](../../work/workflow-builder/process.html). Нажмите Testing, затем «Раскрыть подграф». Выберите `testing.run`, чтобы увидеть параметры, либо `testing.summary`, чтобы увидеть expert и его проектный binding. Клик по подписи перехода показывает outcomes и привязки артефактов. Поиск `testing.summary` находит внутренний узел с верхнего уровня. Инспектор открывается без сервера; HTML можно передать как самостоятельный файл.

Пример содержит определения agent/tool действий; эти действия при экспортировании не исполняются. Модели `current-host-model`/`project-selected-model` — описательные заполнители: для исполнения свяжите их с реальным host adapter по [guide TASK-0037](workflow-execution.md).

## Свой подграф

Скопируйте предметный пример как начало нового определения с новым ID. Подграф хранится в `components/*.toml`, kind=subgraph, и становится доступным через `ref`. Для самостоятельного просмотра подключите его к корневому kind=workflow с явными model_profiles и terminal_states.

Каждому экземпляру нужны совместимые inputs и переходы для всех outcomes из manifest. Внутренние узлы ссылаются на соседей; `exit:passed` возвращает исход наружу. Укажите exports в `[exits.passed]`. Библиотечный блок не должен знать имя узла родительского процесса.

Новый узел требует инструкции или capability, контрактов, исходов и объявленных эффектов. Для контракта используйте поддерживаемую схему из [контракта конструктора](../architecture/workflow-builder.md); полный JSON Schema не поддерживается. Каталог проекта добавляйте вторым `--library`, не перезаписывая ID библиотечных контрактов.

## Изменения проекта

Реальный поддерживаемый overlay:

```toml
schema_version = 1

[nodes."testing.run"]
operation = "patch"
[nodes."testing.run".config]
max_transient_retries = 0

[nodes."testing.summary"]
operation = "patch"
[nodes."testing.summary".execution]
model_profile = "expert"
```

Для replacement создайте и зарегистрируйте проектный блок с совместимыми портами/outcomes, затем укажите operation=replace и ref. Совместимость проверяется; прежние config/instruction не переносятся автоматически. Новый ID контракта требует явного изменения вызывающего определения.

Пример проектной библиотеки и replacement уже поставлен; проверьте его отдельно:

```powershell
.venv\Scripts\python.exe -X utf8 -m orchestrator.workflow_builder validate workflow-library/workflows/testing-and-documentation.toml --library workflow-library --library workflow-library/project-example --overlay workflow-library/examples/project-replacement.toml
```

Код выхода CLI: 0 при успехе, 2 при ошибке; результат/ошибка — JSON. В ошибке указаны code и location. `unavailable_artifact` означает, что на одном из допустимых путей источник ещё не произведён или не обязателен для исхода. Измените маршрут, требование результата или контракт; одного наличия стрелки недостаточно.

## Python API и связь с runtime

```python
from pathlib import Path
from orchestrator.workflow_builder import ComponentLibrary, WorkflowBuilder
from orchestrator import AgentGraphRuntime

library = ComponentLibrary(Path("workflow-library"))
resolved = WorkflowBuilder(library).load(
    Path("workflow-library/workflows/testing-and-documentation.toml"),
    overlay=Path("workflow-library/examples/project-overlay.toml"),
)
assert resolved.graph.entry_node == "testing.scope"
assert len(resolved.graph.nodes) == 5
runtime = AgentGraphRuntime()
run = runtime.create_run(resolved.graph, {}, **resolved.runtime_options)
assert run.current_node == "testing.scope"
print(resolved.digest)
```

Пример создаёт in-memory process, но не выполняет узел. Caller должен предоставить реальные входы, выполнить разрешённую работу, проверить payload через validate_outputs и подать NodeResult с актуальной revision. Для материализации входов/выходов подграфов используйте отдельный [WorkflowExecutor и snapshot binding](workflow-execution.md). Тест `test_compiled_graph_accepts_real_runtime_results_without_executor` демонстрирует структурный цикл с fixture payload; он не является фактическим тестированием целевого проекта.
