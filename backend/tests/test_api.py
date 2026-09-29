"""Интеграционные тесты API на подменённом SourceCraft: сквозной путь публичного и личного
анализа, контроль доступа к закрытым данным (ТЗ 5, ограничение 11.4), устойчивость к сбоям."""

import asyncio

import httpx
import pytest
from sqlalchemy import delete

from app.clients.http import SourceError
from app.clients.sourcecraft_api import SourceCraftAPIClient
from app.config import settings
from app.db import async_session, init_db
from app.main import app
from app.models import Analysis, Job, Repository, User, UserRepoAccess
from app.scoring.facts import (
    ActivityFacts,
    CiCdFacts,
    CiRunFact,
    CodeHealthFacts,
    DocumentationFacts,
    IssuesFacts,
    SecurityFacts,
)
from app.scoring.recommendations import AllFacts
from app.services import analysis as analysis_service
from app.services.collector import CollectResult
from app.services.queue import claim_next

PUBLIC = {"id": "100", "slug": "lib", "organization": {"slug": "acme"}, "visibility": "public",
          "web_url": "https://sourcecraft.dev/acme/lib", "clone_url": {"https": "https://git.sourcecraft.dev/acme/lib.git"},
          "language": {"name": "Python"}, "rating": {"reaction_counts": [{"type": "positive_low", "count": "7"}]},
          "last_updated": "2026-09-20T10:00:00Z"}
PRIVATE = {**PUBLIC, "id": "200", "slug": "secret", "visibility": "private", "web_url": "https://sourcecraft.dev/alice/secret",
           "organization": {"slug": "alice"}}
TOKENS = {"alice-pat": {"id": "u-alice", "username": "alice"}, "bob-pat": {"id": "u-bob", "username": "bob"}}
ACCESS = {"service-pat": {"100"}, "alice-pat": {"100", "200"}, "bob-pat": {"100"}}
REPOS = {("acme", "lib"): PUBLIC, ("alice", "secret"): PRIVATE}


@pytest.fixture(autouse=True)
def fake_sourcecraft(monkeypatch):
    def token_of(client):
        return client._http.headers.get("Authorization", "").removeprefix("Bearer ")

    async def get_user(self):
        user = TOKENS.get(token_of(self))
        if not user:
            raise SourceError("no_access", "401", 401)
        return user

    async def get_repo(self, org, slug):
        data = REPOS.get((org, slug))
        if not data or data["id"] not in ACCESS.get(token_of(self), set()):
            raise SourceError("not_found", "404", 404)
        return data

    async def get_repo_by_id(self, repo_id):
        for data in REPOS.values():
            if data["id"] == repo_id and repo_id in ACCESS.get(token_of(self), set()):
                return data
        raise SourceError("not_found", "404", 404)

    async def list_org_repos(self, org, limit=500):
        return [d for (o, _), d in REPOS.items() if o == org and d["id"] in ACCESS.get(token_of(self), set())]

    monkeypatch.setattr(SourceCraftAPIClient, "get_user", get_user)
    monkeypatch.setattr(SourceCraftAPIClient, "get_repo", get_repo)
    monkeypatch.setattr(SourceCraftAPIClient, "get_repo_by_id", get_repo_by_id)
    monkeypatch.setattr(SourceCraftAPIClient, "list_org_repos", list_org_repos)


def facts(critical: int = 0, scanned: bool = False) -> AllFacts:
    return AllFacts(
        security=SecurityFacts(has_ever_scanned=scanned, open_critical_count=critical),
        cicd=CiCdFacts(True, [CiRunFact("success", 1.0) for _ in range(12)]),
        documentation=DocumentationFacts(is_empty_repo=False, has_readme=True, has_license=True),
        activity=ActivityFacts(days_since_last_commit=3, commits_per_week_last90d=3, active_authors_last90d=2,
                               merged_prs_last90d=4, days_since_last_release=None, commits_last90d=40),
        issues=IssuesFacts(has_ever_had_issues=False),
        code_health=CodeHealthFacts(clone_succeeded=True, markers_count=3, kloc=5),
    )


@pytest.fixture
def fake_collect(monkeypatch):
    calls = []

    async def collect(ctx):
        calls.append(ctx)
        if ctx.scope == "personal":
            # Личный анализ видит AppSec: 2 критические уязвимости.
            return CollectResult(facts=facts(critical=2, scanned=True), sources={"appsec": "ok"})
        return CollectResult(facts=facts(), sources={"appsec": "skipped: public scope"})

    monkeypatch.setattr(analysis_service, "collect", collect)
    return calls


@pytest.fixture
async def client():
    await init_db()
    async with async_session() as s:
        for model in (Analysis, Job, UserRepoAccess, Repository, User):
            await s.execute(delete(model))
        await s.commit()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def drain_queue():
    while True:
        async with async_session() as s:
            job = await claim_next(s, "test")
        if job is None:
            return
        await analysis_service.run_job(job.id)


async def login(c: httpx.AsyncClient, token: str | None) -> None:
    # Каждый пользователь - отдельный dev-логин; различаем их через yandex_id.
    r = await c.post("/api/v1/auth/dev-login")
    assert r.status_code == 200
    if token:
        r = await c.put("/api/v1/user/token", json={"token": token})
        assert r.status_code == 200, r.text


async def test_public_flow_rating_detail_report(client, fake_collect):
    r = await client.post("/api/v1/repositories/analyze", json={"repository_url": "https://sourcecraft.dev/acme/lib"})
    assert r.status_code == 202
    job_id = r.json()["job_id"]
    again = await client.post("/api/v1/repositories/analyze", json={"repository_url": "acme/lib"})
    assert again.json()["job_id"] == job_id  # идемпотентно
    await drain_queue()

    job = (await client.get(f"/api/v1/jobs/{job_id}")).json()
    assert job["status"] == "COMPLETED"
    rating = (await client.get("/api/v1/repositories")).json()
    assert [i["id"] for i in rating["items"]] == ["100"]
    item = rating["items"][0]
    assert item["health_score"] is not None and item["likes"] == 7 and item["language"] == "Python"

    detail = (await client.get("/api/v1/repositories/100")).json()
    assert detail["metrics"]["security"]["status"] == "NO_DATA"  # публичный анализ - без AppSec
    assert detail["metrics"]["issues"]["status"] == "NO_DATA"
    assert detail["metrics"]["security"]["weight"] == 0
    assert abs(sum(m["weight"] for m in detail["metrics"].values()) - 1) < 1e-3
    assert fake_collect[0].scope == "public" and fake_collect[0].api_token == "service-pat"

    report = await client.get("/api/v1/repositories/100/report")
    assert report.status_code == 200
    assert "attachment" in report.headers["content-disposition"]
    assert f"Repo Health Score: {detail['health_score']}/100" in report.text
    assert "Нет данных" in report.text
    pdf = await client.get("/api/v1/repositories/100/report?format=pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert pdf.headers["content-type"] == "application/pdf"

    langs = (await client.get("/api/v1/repositories/languages")).json()
    assert langs == ["Python"]


async def test_reanalyze_updates_date_and_keeps_history(client, fake_collect):
    await client.post("/api/v1/repositories/analyze", json={"repository_url": "acme/lib"})
    await drain_queue()
    first = (await client.get("/api/v1/repositories/100")).json()
    await asyncio.sleep(0.01)
    r = await client.post("/api/v1/repositories/100/reanalyze")
    assert r.status_code == 202
    await drain_queue()
    second = (await client.get("/api/v1/repositories/100")).json()
    assert second["last_analyzed_at"] > first["last_analyzed_at"]
    assert second["previous"]["health_score"] == first["health_score"]
    history = (await client.get("/api/v1/repositories/100/history")).json()
    assert len(history) == 2


async def test_failed_job_keeps_previous_result(client, fake_collect, monkeypatch):
    await client.post("/api/v1/repositories/analyze", json={"repository_url": "acme/lib"})
    await drain_queue()
    score = (await client.get("/api/v1/repositories/100")).json()["health_score"]

    async def broken(ctx):
        raise RuntimeError("SourceCraft недоступен")

    monkeypatch.setattr(analysis_service, "collect", broken)
    await client.post("/api/v1/repositories/100/reanalyze")
    await drain_queue()
    detail = (await client.get("/api/v1/repositories/100")).json()
    assert detail["health_score"] == score
    assert detail["latest_job"]["status"] == "FAILED"
    rating = (await client.get("/api/v1/repositories")).json()["items"][0]
    assert rating["status"] == "FAILED" and rating["health_score"] == score


async def test_private_repo_is_visible_only_to_owner(client, fake_collect):
    await login(client, "alice-pat")
    r = await client.post("/api/v1/repositories/analyze", json={"repository_url": "alice/secret", "scope": "personal"})
    assert r.status_code == 202, r.text
    await drain_queue()
    assert fake_collect[-1].scope == "personal" and fake_collect[-1].user_token == "alice-pat"

    mine = await client.get("/api/v1/repositories/200?scope=personal")
    assert mine.status_code == 200
    assert mine.json()["metrics"]["security"]["status"] == "OK"
    listed = (await client.get("/api/v1/user/repositories")).json()
    assert any(i["id"] == "200" and i["private"] and i["analyzed"] for i in listed["items"])

    # Не попадает в публичный рейтинг и не открывается публично.
    assert (await client.get("/api/v1/repositories")).json()["total"] == 0
    assert (await client.get("/api/v1/repositories/200")).status_code == 404
    assert (await client.get("/api/v1/repositories/200/report")).status_code == 404

    # Аноним.
    client.cookies.clear()
    assert (await client.get("/api/v1/repositories/200?scope=personal")).status_code == 401
    assert (await client.get("/api/v1/repositories/200/report?scope=personal")).status_code == 401

    # Другой пользователь без доступа.
    async with async_session() as s:
        await s.execute(delete(User).where(User.yandex_id == "dev-user"))
        await s.commit()
    await login(client, "bob-pat")
    assert (await client.get("/api/v1/repositories/200?scope=personal")).status_code == 404
    r = await client.post("/api/v1/repositories/analyze", json={"repository_url": "alice/secret", "scope": "personal"})
    assert r.status_code == 404


async def test_personal_analysis_of_public_repo_does_not_leak_into_rating(client, fake_collect):
    await client.post("/api/v1/repositories/analyze", json={"repository_url": "acme/lib"})
    await drain_queue()
    public_score = (await client.get("/api/v1/repositories")).json()["items"][0]["health_score"]

    await login(client, "alice-pat")
    await client.post("/api/v1/repositories/analyze", json={"repository_url": "acme/lib", "scope": "personal"})
    await drain_queue()
    personal = (await client.get("/api/v1/repositories/100?scope=personal")).json()
    assert personal["metrics"]["security"]["score"] == 60  # 2 критические уязвимости
    assert personal["health_score"] != public_score

    rating = (await client.get("/api/v1/repositories")).json()["items"][0]
    assert rating["health_score"] == public_score
    public = (await client.get("/api/v1/repositories/100")).json()
    assert public["metrics"]["security"]["status"] == "NO_DATA"


async def test_public_analysis_without_service_pat_reuses_known_repo(client, fake_collect, monkeypatch):
    # Репозиторий уже в базе под id из API (личный анализ), сервисного PAT на стенде нет:
    # публичный запуск по ссылке должен взять эту запись, а не вставлять дубль org/slug (была 500).
    await login(client, "alice-pat")
    await client.post("/api/v1/repositories/analyze", json={"repository_url": "acme/lib", "scope": "personal"})
    await client.post("/api/v1/repositories/analyze", json={"repository_url": "alice/secret", "scope": "personal"})
    await drain_queue()
    monkeypatch.setattr(settings, "sourcecraft_service_pat", "")

    r = await client.post("/api/v1/repositories/analyze", json={"repository_url": "https://sourcecraft.dev/acme/lib"})
    assert r.status_code == 202, r.text
    assert r.json()["repository_id"] == "100"
    await drain_queue()
    rating = (await client.get("/api/v1/repositories")).json()["items"]
    assert [(i["id"], i["health_score"] is not None) for i in rating] == [("100", True)]

    r = await client.post("/api/v1/repositories/analyze", json={"repository_url": "alice/secret"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "NOT_PUBLIC"


async def test_revoked_access_blocks_personal_report(client, fake_collect):
    await login(client, "alice-pat")
    await client.post("/api/v1/repositories/analyze", json={"repository_url": "alice/secret", "scope": "personal"})
    await drain_queue()
    await client.delete("/api/v1/user/token")  # без токена подтверждения доступа снимаются
    assert (await client.get("/api/v1/repositories/200?scope=personal")).status_code == 404


async def test_validation_errors(client):
    r = await client.post("/api/v1/repositories/analyze", json={"repository_url": "???"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "INVALID_REPOSITORY_URL"
    r = await client.get("/api/v1/repositories?sort_by=stars")
    assert r.status_code == 400
    r = await client.post("/api/v1/repositories/analyze", json={"repository_url": "acme/lib", "scope": "personal"})
    assert r.status_code == 401
    await login(client, None)
    r = await client.put("/api/v1/user/token", json={"token": "wrong"})
    assert r.json()["error"]["code"] == "INVALID_TOKEN"
