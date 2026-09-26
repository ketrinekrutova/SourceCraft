from datetime import datetime

from pydantic import BaseModel


class Me(BaseModel):
    id: str
    login: str | None
    display_name: str | None
    avatar_url: str | None
    has_token: bool
    sourcecraft_username: str | None
    orgs: list[str]


class TokenRequest(BaseModel):
    token: str


class OrgsRequest(BaseModel):
    orgs: list[str]


class UserRepository(BaseModel):
    id: str
    name: str
    full_name: str
    url: str
    private: bool
    visibility: str
    health_score: int | None
    likes: int
    language: str | None
    last_activity_at: datetime | None
    last_analyzed_at: datetime | None
    analyzed: bool


class UserRepositoryList(BaseModel):
    items: list[UserRepository]
    orgs_checked: list[str]
    errors: list[str] = []
