# CHECK.md - что осталось проверить руками перед сдачей

Код написан под все сценарии ТЗ. Ниже - проверки, для которых нужны реальные доступы: сервисный PAT команды, личный PAT, OAuth-приложение Я ID. Без них это нельзя проверить автоматически.

## A. Доступы

- [ ] PAT команды SourceCraft → `SOURCECRAFT_SERVICE_PAT` (без него API отвечает 401 даже на `GET /repos` - проверено).
- [ ] OAuth-приложение Я ID (oauth.yandex.ru): `YA_ID_CLIENT_ID`, `YA_ID_CLIENT_SECRET`, redirect URI `https://<стенд>/api/v1/auth/yandex/callback`, права - доступ к логину и аватару.
- [ ] Хостинг демо-стенда, `docker compose up -d --build`, HTTPS, `COOKIE_SECURE=true`, `SECRET_KEY`.

## B. Проверки на живом API (с PAT)

- [ ] `python -m app.cli discover` - каталог обходится до конца (крутится `next_page_token`), число репозиториев совпадает с sourcecraft.dev/find/repositories.
- [ ] Для публичного чужого репозитория зафиксировать, что отдаёт сервисный PAT: `cicd/runs`, `issues`, `pulls`, `releases`, `contributors` (200 или 403). От этого зависит полнота публичного рейтинга; в UI это видно по полю «данные: N%».
- [ ] Личный анализ своего репозитория с AppSec: `gitRepo = Repository.id` из основного API принимается AppSec (описание параметра говорит, что принимается internal ID или UUID).
- [ ] Клон приватного репозитория по PAT: сервис пробует `Authorization: Basic <username:PAT>`, затем `Bearer <PAT>` (`app/clients/git_client.py`). Если ни один вариант не проходит - поправить `GitAuth.header_variants`.
- [ ] Шаблоны веб-ссылок на файл/issue/прогон/коммит в `app/normalizers/common.py` открывают нужные страницы SourceCraft.

## C. Контрольные сценарии методики

Автоматически проверяются `backend/tests/test_scoring_scenarios.py` (см. таблицу в README). Для демонстрации подобрать реальные репозитории под профили: здоровый; с уязвимостями (свой, с AppSec); без CI; заброшенный с хорошей документацией; пустой; с большим числом старых TODO. Крупный репозиторий: `python scripts/make_large_repo.py`, затем push в SourceCraft.

## D. Демонстрация (ТЗ 9.4)

1. Рейтинг: фильтр по языку, сортировка по Score / лайкам / активности, переход на анализ.
2. Страница анализа: Score, категории, раскрытие «Как посчитано», «Нет данных» с причиной, рекомендации с фактами, скачивание `.md`.
3. Вход через Я ID → PAT → «Мои репозитории» → личный анализ с Security.
4. «Повторный анализ» → обновились дата, статус и изменение к прошлому анализу.
5. Расписание: `SCHEDULE_CRON` в `.env`, код - `backend/app/workers/scheduler.py`; масштабирование - `docker compose up --scale worker=3`.
