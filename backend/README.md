# Backend — структура кода

Соответствует фазам 0-2 плана в корневом `../README.md`. Общая идея: `scoring/` — чистый Python
без внешних зависимостей, тестируется и разрабатывается независимо от доступов к API (см. `../CHECK.md`).

```
app/
  scoring/            Фаза 2 — формулы категорий (README раздел 3.2), 0 внешних зависимостей
    facts.py          общий контракт №1: вход каждой формулы
    result.py         общий контракт №2: CategoryScore/Recommendation, веса категорий
    categories/       по одной функции score_<category>(facts) -> CategoryScore на категорию
    aggregate.py      взвешенная сумма с перенормировкой при no_data (README 3.1)
    recommendations.py
  clients/            Фаза 1 — HTTP/CLI-обёртки, сейчас все методы raise NotImplementedError
    sourcecraft_api.py    api.sourcecraft.tech, пути сверены со swagger
    scs_security.py       SCS Security API, base URL — гипотеза (CHECK.md A3)
    sourcecraft_cli.py    git clone/log/grep/blame
  normalizers/        Фаза 1 — raw JSON конкретного клиента -> Facts (мост между Фазой 1 и 2)
  schemas/            Фаза 0 — контракт ответа API для фронта (Pydantic)
  models/             Фаза 0 — таблицы Postgres (SQLAlchemy)
  routers/            Фаза 0/5 — FastAPI-эндпоинты, сейчас raise NotImplementedError
  workers/            Фаза 3 — быстрый/полный проход, планировщик
tests/
  test_scoring_scenarios.py   8 контрольных сценариев из CHECK.md раздела C — уже проходят
```

## Что уже работает

```
python -m unittest discover -s tests -v
```

Формулы `scoring/` реализованы полностью и покрыты тестами на все 8 контрольных сценариев
CHECK.md — можно менять веса/пороги и сразу видеть, что ломается.

## Что ещё не реализовано (осознанно)

Всё в `clients/`, `normalizers/`, `routers/`, `workers/` — заглушки с `raise NotImplementedError`
и точными ссылками на эндпоинты/поля в докстрингах. Реализация блокируется на `../CHECK.md`
(Этап 0: токены, подтверждение base URL SCS API, гипотеза списка репозиториев пользователя).

## Установка (когда будет нужно поднимать реально)

```
pip install -r requirements.txt
cp .env.example .env   # заполнить после Этапа 0
uvicorn app.main:app --reload
```
