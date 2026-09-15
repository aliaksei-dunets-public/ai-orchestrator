"""Read-only local task journal. No task mutation is exposed through HTTP."""

from __future__ import annotations

import argparse
import html
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit

from .task_manager import TASK_ID, TaskError, TaskManagerService


STATUS_LABELS = {
    "created": "Создана", "preparing": "Подготовка", "ready": "Готова",
    "active": "В работе", "awaiting_input": "Ждёт ответа", "blocked": "Заблокирована",
    "awaiting_acceptance": "Приёмка", "completed": "Завершена", "cancelled": "Отменена",
}
EVENT_LABELS = {
    "task_created": "Задача создана", "preparation_started": "Подготовка начата",
    "definition_refined": "Определение уточнено", "metadata_updated": "Метаданные обновлены",
    "artifact_attached": "Артефакт привязан", "status_changed": "Статус изменён",
    "task_claimed": "Исполнитель закреплён", "claim_renewed": "Закрепление продлено",
    "claim_released": "Закрепление освобождено", "claim_recovered": "Закрепление восстановлено",
    "workflow_run_linked": "Запуск графа связан", "blocker_added": "Блокер добавлен",
    "blocker_resolved": "Блокер разрешён", "user_decision_recorded": "Решение пользователя",
    "task_completed": "Задача завершена", "task_cancelled": "Задача отменена",
    "external_link_registered": "Внешняя ссылка зарегистрирована",
}

STYLE = """
:root{--paper:#f4f1e9;--ink:#192329;--muted:#627078;--line:#d7d5ce;--accent:#d9563c;--deep:#122c32;--soft:#fffdfa}
*{box-sizing:border-box}html{font-size:16px}body{margin:0;background:var(--paper);color:var(--ink);font-family:'Trebuchet MS',Verdana,sans-serif}
a{color:inherit}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:3px solid var(--accent);outline-offset:2px}
.frame{max-width:1460px;margin:auto;padding:0 34px 72px}.mast{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid var(--ink);padding:26px 0 21px;gap:20px}
.brand{font-family:Georgia,serif;font-size:1.34rem;font-weight:700;letter-spacing:-.04em;text-decoration:none}.brand-mark{display:inline-block;background:var(--accent);height:13px;width:13px;transform:rotate(45deg);margin-right:14px}
.mast-note,.eyebrow,.meta,.table-head,.event-time,.small{font-size:.72rem;letter-spacing:.12em;text-transform:uppercase;font-weight:700;color:var(--muted)}
.hero{display:grid;grid-template-columns:1.5fr 1fr;gap:32px;padding:54px 0 46px;align-items:end}.hero h1{font-family:Georgia,serif;font-size:clamp(3.4rem,7vw,7rem);line-height:.9;letter-spacing:-.07em;margin:13px 0 0;font-weight:500}.hero p{max-width:380px;line-height:1.6;color:var(--muted);margin:0 0 4px auto}
.eyebrow{color:var(--accent)}.stats{display:grid;grid-template-columns:repeat(4,1fr);border:1px solid var(--line);background:var(--soft)}.stat{padding:22px 24px;border-right:1px solid var(--line)}.stat:last-child{border-right:0}.stat strong{display:block;font-family:Georgia,serif;font-size:2.7rem;font-weight:500;letter-spacing:-.06em;margin-top:8px}
.section-top{display:flex;align-items:end;justify-content:space-between;gap:20px;margin:45px 0 17px}.section-top h2{font-family:Georgia,serif;font-size:2rem;letter-spacing:-.045em;margin:0}.count{color:var(--muted);font-size:.85rem}
.filters{display:flex;gap:9px;margin-bottom:16px}.filters input,.filters select{border:1px solid var(--line);background:var(--soft);padding:13px 14px;color:var(--ink);font:inherit}.filters input{flex:1}.filters button{border:0;background:var(--deep);color:#fff;padding:0 23px;font-weight:700;cursor:pointer}.filters button:hover{background:var(--accent)}
.task-table{background:var(--soft);border-top:2px solid var(--ink)}.task-row{display:grid;grid-template-columns:130px minmax(240px,1fr) 170px 145px 115px;align-items:center;gap:16px;padding:19px 21px;border-bottom:1px solid var(--line);text-decoration:none;transition:background .16s,transform .16s}.task-row:hover{background:#f9eae2;transform:translateX(3px)}.task-row .title{font-family:Georgia,serif;font-size:1.21rem;letter-spacing:-.025em}.task-row .id{font-family:Consolas,monospace;font-size:.83rem;color:var(--muted)}
.badge{display:inline-block;padding:7px 9px;border-radius:2px;background:#dfe7e3;color:#284d45;font-size:.68rem;font-weight:800;letter-spacing:.07em;text-transform:uppercase;white-space:nowrap}.badge[data-status='blocked'],.badge[data-status='cancelled']{background:#f1d8d2;color:#8c3427}.badge[data-status='active']{background:#d8e4ec;color:#244f68}.badge[data-status='ready']{background:#e4ebd5;color:#3c6234}.badge[data-status='completed']{background:#e7e5dd;color:#54605b}.badge[data-status='awaiting_input'],.badge[data-status='awaiting_acceptance']{background:#f8ead0;color:#79551d}
.empty{padding:42px 24px;color:var(--muted)}.back{display:inline-block;margin:37px 0 20px;text-decoration:none;font-size:.82rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)}.detail-title{font-family:Georgia,serif;font-size:clamp(2.6rem,5vw,5rem);line-height:1;letter-spacing:-.06em;margin:13px 0 20px;font-weight:500}.detail-intro{display:flex;gap:14px;align-items:center;margin-bottom:36px}.detail-grid{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(290px,.9fr);gap:25px}.panel{background:var(--soft);border:1px solid var(--line);padding:27px 30px;margin-bottom:22px}.panel h2{font-family:Georgia,serif;font-size:1.6rem;font-weight:500;letter-spacing:-.04em;margin:0 0 20px}.panel p{line-height:1.65;margin:0 0 17px}.panel ul{padding-left:20px;line-height:1.65}.kv{display:grid;grid-template-columns:145px 1fr;gap:10px;border-bottom:1px solid var(--line);padding:11px 0;font-size:.87rem}.kv:last-child{border-bottom:0}.kv span:first-child{color:var(--muted)}.doc-link{display:block;border-top:1px solid var(--line);padding:13px 0;text-decoration:none;font-weight:700}.doc-link:hover{color:var(--accent)}.event{position:relative;padding:0 0 22px 23px;border-left:1px solid var(--line);margin-left:5px}.event:before{content:'';position:absolute;width:9px;height:9px;border-radius:50%;background:var(--accent);left:-5px;top:3px}.event:last-child{padding-bottom:0}.event strong{display:block;font-size:.9rem;margin-bottom:4px}.event-time{letter-spacing:.04em;text-transform:none}.document{white-space:pre-wrap;overflow-wrap:anywhere;font-family:Consolas,monospace;font-size:.88rem;line-height:1.7;margin:0}
.pager{display:flex;justify-content:space-between;margin-top:14px;min-height:36px}.pager a{font-size:.77rem;letter-spacing:.07em;text-transform:uppercase;font-weight:800;text-decoration:none;border-bottom:1px solid var(--accent);padding:6px 0;color:var(--deep)}.pager a:hover{color:var(--accent)}
footer{border-top:1px solid var(--line);padding-top:20px;margin-top:46px;color:var(--muted);font-size:.78rem}
@media(max-width:900px){.task-row{grid-template-columns:105px 1fr 135px}.task-row .meta:nth-last-child(-n+2){display:none}.detail-grid{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}.stat:nth-child(2){border-right:0}.stat:nth-child(-n+2){border-bottom:1px solid var(--line)}}
@media(max-width:600px){.frame{padding:0 18px 48px}.mast-note{display:none}.hero{grid-template-columns:1fr;gap:20px;padding:40px 0 32px}.hero p{margin:0}.filters{flex-wrap:wrap}.filters input{flex-basis:100%}.filters select{flex:1}.task-row{grid-template-columns:1fr auto;gap:8px;padding:16px}.task-row .id{grid-column:1}.task-row .title{grid-column:1;grid-row:2}.task-row .badge{grid-column:2;grid-row:1/3}.task-row .meta{display:none}.panel{padding:22px}.kv{grid-template-columns:1fr;gap:2px}}
"""


def _h(value: object) -> str:
    return html.escape(str(value), quote=True)


def _shell(title: str, content: str) -> str:
    return (
        "<!doctype html><html lang='ru'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{_h(title)} · Orchestrator</title><style>{STYLE}</style></head><body>"
        "<div class='frame'><header class='mast'><a class='brand' href='/'><span class='brand-mark'></span>Orchestrator</a>"
        "<span class='mast-note'>Локальный журнал задач · только чтение</span></header>"
        f"<main>{content}</main><footer>Источник данных: Task Manager Service · SQLite · Локальный доступ</footer></div></body></html>"
    )


def render_index(service: TaskManagerService, *, query: str = "", status: str = "", page: int = 1,
                 cursor: str | None = None, include_archived: bool = False) -> str:
    all_tasks = service.list_tasks(limit=None, include_archived=include_archived)
    selected = {status} if status in STATUS_LABELS else None
    if cursor is not None:
        filtered = service.list_tasks(statuses=selected, query=query, limit=51, cursor=cursor,
                                      include_archived=include_archived)
        tasks = filtered[:50]
        has_next = len(filtered) > 50
        start = 0
    else:
        filtered = service.list_tasks(statuses=selected, query=query, limit=None,
                                      include_archived=include_archived)
        page = max(1, min(page, max(1, (len(filtered) + 49) // 50)))
        start = (page - 1) * 50
        tasks = filtered[start:start + 50]
        has_next = start + 50 < len(filtered)
    counts = {
        "Всего": len(all_tasks),
        "В работе": sum(task["status"] == "active" for task in all_tasks),
        "Готовы": sum(task["status"] == "ready" for task in all_tasks),
        "Нужны действия": sum(task["status"] in {"blocked", "awaiting_input", "awaiting_acceptance"} for task in all_tasks),
    }
    stat_html = "".join(f"<div class='stat'><span class='small'>{_h(label)}</span><strong>{value}</strong></div>" for label, value in counts.items())
    options = "<option value=''>Все статусы</option>" + "".join(
        f"<option value='{_h(key)}'{' selected' if key == status else ''}>{_h(label)}</option>"
        for key, label in STATUS_LABELS.items()
    )
    rows = "".join(
        f"<a class='task-row' href='/task/{_h(task['id'])}'>"
        f"<span class='id'>{_h(task['id'])}</span>"
        f"<span class='title'>{_h(task['title'])}</span>"
        f"<span class='badge' data-status='{_h(task['status'])}'>{_h(STATUS_LABELS.get(task['status'], task['status']))}</span>"
        f"<span class='meta'>{_h(task['type'])}</span><span class='meta'>v{_h(task['version'])}</span></a>"
        for task in tasks
    ) or "<div class='empty'>Здесь пока нет задач с выбранными условиями.</div>"
    pager = "<nav class='pager' aria-label='Страницы задач'>"
    if page > 1:
        pager_params = {'q': query, 'status': status, 'page': page - 1}
        if include_archived:
            pager_params['archived'] = '1'
        pager += f"<a href='/?{_h(urlencode(pager_params))}'>← Предыдущая</a>"
    if has_next and tasks:
        params = {'q': query, 'status': status, 'cursor': tasks[-1]['id']} if cursor is not None else {'q': query, 'status': status, 'page': page + 1}
        if include_archived:
            params['archived'] = '1'
        pager += f"<a href='/?{_h(urlencode(params))}'>Следующая →</a>"
    pager += "</nav>"
    body = (
        "<section class='hero'><div><span class='eyebrow'>Операционный обзор / задачи</span>"
        "<h1>Ход работы</h1></div><p>Единая картина подготовленных, активных и ожидающих решений задач. "
        "Каждая строка ведёт к доказательствам и истории, а не к скрытому состоянию чата.</p></section>"
        f"<section class='stats' aria-label='Сводка'>{stat_html}</section>"
        f"<div class='section-top'><h2>Реестр задач</h2><span class='count'>Показано {len(tasks)} из {len(filtered)} · всего {len(all_tasks)}</span></div>"
        f"<form class='filters' method='get' action='/'><input aria-label='Поиск задач' name='q' "
        f"placeholder='Поиск по ID, названию или цели' value='{_h(query)}'>"
        f"<select aria-label='Статус задачи' name='status'>{options}</select>"
        f"<label class='small'><input type='checkbox' name='archived' value='1'{' checked' if include_archived else ''}> Архив</label>"
        f"<button type='submit'>Показать</button></form>"
        f"<div class='task-table'>{rows}</div>{pager}"
    )
    return _shell("Задачи", body)


def render_task(service: TaskManagerService, task_id: str) -> str:
    if not TASK_ID.fullmatch(task_id):
        raise TaskError("task_not_found", "Некорректный ID задачи")
    task = service.get_task(task_id)
    history = service.get_history(task_id)
    criteria = "".join(f"<li>{_h(item['text'])}</li>" for item in task["acceptance_criteria"])
    blockers = "".join(
        f"<li><strong>{_h(item['id'])}</strong> · {_h(item['summary'])} · {_h(item['status'])}</li>"
        for item in task["blockers"]
    ) or "<li>Нет блокеров</li>"
    decisions = "".join(
        f"<li>{_h(item['type'])}: {_h(item['value'])}</li>" for item in task["user_decisions"]
    ) or "<li>Нет решений</li>"
    documents = "".join(
        f"<a class='doc-link' href='/task/{_h(task_id)}/document/{role}'>"
        f"{'Спецификация' if role == 'specification' else 'План'} ↗</a>"
        for role in ("specification", "plan") if role in task["artifacts"]
    ) or "<p>Документы ещё не привязаны.</p>"
    events = "".join(
        f"<div class='event'><strong>{_h(EVENT_LABELS.get(event['type'], event['type']))}</strong>"
        f"<span class='event-time'>#{event['sequence']} · {_h(event['at'])} · v{event['task_version']}"
        f" · {_h(' / '.join(str(event[key]) for key in ('actor_ref','source','correlation_id','run_ref') if event.get(key)))}"
        f"</span></div>"
        for event in reversed(history)
    )
    body = (
        f"<a class='back' href='/'>← Все задачи</a><div class='eyebrow'>{_h(task_id)} / {_h(task['type'])}</div>"
        f"<h1 class='detail-title'>{_h(task['title'])}</h1>"
        f"<div class='detail-intro'><span class='badge' data-status='{_h(task['status'])}'>"
        f"{_h(STATUS_LABELS.get(task['status'], task['status']))}</span><span class='meta'>Версия {task['version']}</span></div>"
        "<div class='detail-grid'><div>"
        f"<section class='panel'><h2>Задача</h2><p>{_h(task['objective'])}</p>"
        f"<div class='kv'><span>Исходный запрос</span><span>{_h(task['original_request'])}</span></div>"
        f"<div class='kv'><span>Целевой workflow</span><span>{_h(task['target_workflow'])}</span></div>"
        f"<div class='kv'><span>Передача</span><span>{_h(task['handoff_mode'])}</span></div></section>"
        f"<section class='panel'><h2>Критерии приёмки</h2><ul>{criteria}</ul></section>"
        f"<section class='panel'><h2>История</h2>{events}</section></div><aside>"
        f"<section class='panel'><h2>Документы</h2>{documents}</section>"
        f"<section class='panel'><h2>Блокеры</h2><ul>{blockers}</ul></section>"
        f"<section class='panel'><h2>Решения</h2><ul>{decisions}</ul></section>"
        f"<section class='panel'><h2>Связи</h2>"
        f"<div class='kv'><span>Активный запуск</span><span>{_h(task['active_run_ref'] or '—')}</span></div>"
        f"<div class='kv'><span>Закрепление</span><span>{_h((task['active_claim'] or {}).get('worker_ref') or '—')}</span></div>"
        f"</section></aside></div>"
    )
    return _shell(task["title"], body)


def render_document(service: TaskManagerService, task_id: str, role: str) -> str:
    document = service.get_document(task_id, role)
    title = "Спецификация" if role == "specification" else "План"
    body = (
        f"<a class='back' href='/task/{_h(task_id)}'>← К задаче</a>"
        f"<div class='eyebrow'>{_h(task_id)} / документ</div><h1 class='detail-title'>{title}</h1>"
        f"<section class='panel'><pre class='document'>{_h(document)}</pre></section>"
    )
    return _shell(title, body)


def make_handler(service: TaskManagerService):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: str) -> None:
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
                self._send(403, _shell("Доступ запрещён", "<h1>Недопустимый адрес</h1>"))
                return
            parsed = urlsplit(self.path)
            try:
                if parsed.path == "/":
                    params = parse_qs(parsed.query)
                    raw_page = params.get("page", ["1"])[0]
                    page = int(raw_page) if raw_page.isdigit() else 1
                    body = render_index(service, query=params.get("q", [""])[0],
                                        status=params.get("status", [""])[0], page=page,
                                        cursor=params.get("cursor", [None])[0],
                                        include_archived=params.get("archived", [""])[0] == "1")
                elif match := re.fullmatch(r"/task/(TASK-[0-9]{4,})", parsed.path):
                    body = render_task(service, match.group(1))
                elif match := re.fullmatch(r"/task/(TASK-[0-9]{4,})/document/(specification|plan)", parsed.path):
                    body = render_document(service, match.group(1), match.group(2))
                else:
                    raise TaskError("task_not_found", "Страница не найдена")
            except TaskError as exc:
                self._send(404 if exc.code == "task_not_found" else 409,
                           _shell("Ошибка", f"<h1>Невозможно открыть страницу</h1><p>{_h(exc)}</p>"))
                return
            self._send(200, body)

        def do_POST(self) -> None:
            self._send(405, _shell("Только чтение", "<h1>Изменения через веб-панель запрещены</h1>"))

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Локальный просмотр задач Orchestrator")
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Порт должен быть в диапазоне 0..65535")
    service = TaskManagerService(args.project)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(service))
    print(f"Откройте http://127.0.0.1:{server.server_port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
