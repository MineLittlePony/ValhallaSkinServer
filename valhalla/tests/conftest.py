import hashlib
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal, Self
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pytest_httpx import HTTPXMock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..app import app
from ..config import settings
from ..db import get_db
from ..models import Base

assets = Path(__file__).parent / "assets"


SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = async_sessionmaker[AsyncSession](engine)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app.router.lifespan_context = app_lifespan


async def override_get_db() -> AsyncGenerator[AsyncSession, Any]:
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def client(tmpdir: Path) -> Generator[TestClient]:
    settings.online_mode = False
    settings.textures_path = str(tmpdir)
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def anyio_backend() -> Literal["asyncio"]:
    return "asyncio"


class TestUser:
    __test__ = False

    def __init__(self, name: str, uuid: UUID | None = None) -> None:
        if uuid is None:
            uuid = UUID(
                bytes=hashlib.md5(
                    f"OfflineUser:{name}".encode(), usedforsecurity=False
                ).digest()
            )
        self.name = name
        self.uuid = uuid
        self.access_token: str | None = None

    @property
    def auth_header(self) -> dict[str, str]:
        if self.access_token is None:
            return {}
        return {"authorization": self.access_token}

    def login(self, client: TestClient) -> Self:
        data = (
            client.post("/api/v1/auth/minecraft", data={"name": self.name})
            .raise_for_status()
            .json()
        )
        token = (
            client.post(
                "/api/v1/auth/minecraft/callback",
                data={"name": self.name, "verifyToken": data["verifyToken"]},
            )
            .raise_for_status()
            .json()
        )
        self.uuid = UUID(token["userId"])
        self.access_token = token["accessToken"]
        return self


@pytest.fixture
def user(client: TestClient) -> TestUser:
    return TestUser("TestUser").login(client)


@pytest.fixture
def users(client: TestClient) -> list[TestUser]:
    """Fixture to get a list of random users"""
    return [TestUser(f"TestUser{n}").login(client) for n in range(1, 11)]


@pytest.fixture(scope="function")
def steve_uri(request: pytest.FixtureRequest, httpx_mock: HTTPXMock) -> str | Path:
    uri: tuple[str, Path] | Path = request.param
    if isinstance(uri, tuple):
        url, path = uri
        httpx_mock.add_response(url=url, content=path.read_bytes())
        return url
    return uri
