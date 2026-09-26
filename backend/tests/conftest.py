import os
import tempfile

# Настройки читаются при импорте app.config - задаём окружение тестов до любого импорта app.
_db = os.path.join(tempfile.mkdtemp(prefix="rh-test-"), "test.db")
os.environ.update({
    "DATABASE_URL": f"sqlite+aiosqlite:///{_db}",
    "RUN_WORKER": "false",
    "SCHEDULER_ENABLED": "false",
    "DEV_LOGIN_ENABLED": "true",
    "SOURCECRAFT_SERVICE_PAT": "service-pat",
    "SECRET_KEY": "test-secret",
})
