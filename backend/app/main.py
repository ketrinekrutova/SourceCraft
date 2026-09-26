import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import DEV_SECRET_KEY, settings
from .db import init_db
from .routers import analysis, auth, rating, reports, user

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.secret_key == DEV_SECRET_KEY:
        log.warning("SECRET_KEY не задан - используется небезопасный ключ разработки")
    await init_db()
    stop = asyncio.Event()
    tasks = []
    scheduler = None
    if settings.run_worker:
        from .workers.worker import run_workers

        tasks.append(asyncio.create_task(run_workers(settings.worker_concurrency, stop)))
    if settings.scheduler_enabled:
        from .workers.scheduler import start_scheduler

        scheduler = start_scheduler()
    yield
    stop.set()
    if scheduler:
        scheduler.shutdown(wait=False)
    for task in tasks:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task


app = FastAPI(title="SourceCraft Repo Health API", version="1.0.0", lifespan=lifespan,
              docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    """Ошибки в формате openapi.yaml: {"error": {"code", "message"}}."""
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message": str(exc.detail)}
    return JSONResponse({"error": detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    return JSONResponse({"error": {"code": "BAD_REQUEST", "message": str(exc.errors()[:3])}}, status_code=400)


for module in (rating, analysis, reports, auth, user):
    app.include_router(module.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
