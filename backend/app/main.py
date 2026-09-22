from fastapi import FastAPI

from .routers import analysis, auth, me, rating, reports

app = FastAPI(title="SourceCraft Repo Health API")

app.include_router(rating.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(me.router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok"}
