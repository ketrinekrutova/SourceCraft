from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_SECRET_KEY = "dev-insecure-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # SQLite - для локального запуска одной командой; в docker-compose - Postgres
    # (там же работает горизонтальное масштабирование воркеров через SKIP LOCKED).
    database_url: str = "sqlite+aiosqlite:///./repo_health.db"

    # --- SourceCraft ---
    sourcecraft_api_base_url: str = "https://api.sourcecraft.tech"
    sourcecraft_git_base_url: str = "https://git.sourcecraft.dev"
    sourcecraft_web_base_url: str = "https://sourcecraft.dev"
    appsec_api_base_url: str = "https://appsec.sourcecraft.tech"
    # PAT команды - только для публичного конвейера (каталог открытых репозиториев).
    # Для приватных данных всегда используется PAT конкретного пользователя.
    sourcecraft_service_pat: str = ""
    # Лимиты от организаторов (ответ в чате 24.09): appsec - 100 rps, остальные хосты - 10 rps
    # на каждый. Берём с запасом; при нескольких процессах-воркерах делить на их число.
    sourcecraft_api_rps: float = 8.0
    appsec_api_rps: float = 50.0
    http_timeout_s: float = 30.0

    # --- Я ID (OAuth) ---
    ya_id_client_id: str = ""
    ya_id_client_secret: str = ""
    ya_id_redirect_uri: str = "http://localhost:8000/api/v1/auth/yandex/callback"
    # Куда вернуть пользователя после входа (адрес фронтенда).
    frontend_url: str = "http://localhost:5173"
    # Локальный вход без Я ID - ТОЛЬКО для разработки, пока OAuth-приложение не зарегистрировано.
    dev_login_enabled: bool = False

    # Подпись cookie сессии и шифрование сохранённых PAT пользователей.
    secret_key: str = DEV_SECRET_KEY
    cookie_secure: bool = False
    session_max_age_s: int = 7 * 24 * 3600
    cors_origins: str = "http://localhost:5173"

    # --- Воркеры и расписание ---
    run_worker: bool = True  # воркер внутри API-процесса; для масштабирования - `python -m app.worker`
    worker_concurrency: int = 2
    scheduler_enabled: bool = True
    # Раз в сутки ночью: публичные репозитории меняются медленно, а полный обход каталога при
    # лимите 10 rps занимает часы - чаще пересчитывать бессмысленно (см. README, «Периодичность»).
    schedule_cron: str = "0 3 * * *"
    recalc_interval_hours: int = 24
    discovery_max_repos: int = 0  # 0 = весь каталог
    job_stale_after_s: int = 1800  # задача без heartbeat дольше - считается упавшей

    # --- Границы анализа (крупные репозитории, README «Крупные репозитории») ---
    clone_timeout_s: int = 900
    history_days: int = 181  # shallow-клон истории: окно активности 90 дн. + порог «старых» TODO 180 дн.
    max_scan_files: int = 20000
    max_scan_bytes: int = 200 * 1024 * 1024
    max_file_bytes: int = 1024 * 1024
    blame_max_files: int = 40
    issues_max: int = 500
    issue_comments_sample: int = 30
    ci_runs_max: int = 50
    pulls_max: int = 300
    work_dir: str = ""  # пусто = системный temp


settings = Settings()
