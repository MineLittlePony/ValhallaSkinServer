import hashlib
import os.path
import secrets
import shutil
import tempfile
from collections.abc import AsyncGenerator, Generator
from pathlib import Path
from typing import Literal, Self
from uuid import UUID

import anyio
import pytest
from litestar import Litestar
from litestar.testing import AsyncTestClient
from pydantic_settings import SettingsConfigDict
from pytest_httpx import HTTPXMock
from sqlalchemy.ext.asyncio import create_async_engine

from ..app import create_app
from ..config import Settings
from ..models import Base

assets = Path(__file__).parent / "assets"

tempdir = tempfile.mkdtemp(prefix="pytest-valhalla-")
async_engine = create_async_engine(
    f"sqlite+aiosqlite:////{tempdir}/test.db", connect_args={"check_same_thread": False}
)


class TestConfig(Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        toml_file=None,
    )


settings = TestConfig(
    secret_key=secrets.token_urlsafe(24),
    database_url=str(async_engine.url),
    online_mode=False,
    textures_path=os.path.join(tempdir, "textures"),
    textures_url=None,
    server_id="testing",
)


@pytest.fixture(autouse=True, scope="session")
def setup() -> Generator[None]:
    yield
    shutil.rmtree(tempdir)


@pytest.fixture
def app() -> Litestar:
    return create_app(settings)


@pytest.fixture
async def client(app: Litestar) -> AsyncGenerator[AsyncTestClient]:
    app.debug = True
    async with AsyncTestClient(app) as client, async_engine.begin() as conn:
        try:
            yield client
        finally:
            await conn.run_sync(Base.metadata.drop_all)


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

    async def login(self, client: AsyncTestClient) -> Self:
        resp = await client.post("/api/v1/auth/minecraft", data={"name": self.name})
        assert resp.is_success, f"handshake failed: {resp.content!r}"
        data = resp.json()

        callback_resp = await client.post(
            "/api/v1/auth/minecraft/callback",
            data={"name": self.name, "verifyToken": data["verifyToken"]},
        )
        assert callback_resp.is_success, f"callback failed: {callback_resp.content!r}"
        token = callback_resp.json()

        self.uuid = UUID(token["userId"])
        self.access_token = token["accessToken"]

        return self


@pytest.fixture
async def user(client: AsyncTestClient) -> TestUser:
    return await TestUser("TestUser").login(client)


@pytest.fixture
async def users(client: AsyncTestClient) -> list[TestUser]:
    """Fixture to get a list of random users"""
    users = [TestUser(f"TestUser{n}") for n in range(1, 11)]
    async with anyio.create_task_group() as tg:
        for u in users:
            tg.create_task(u.login(client))
    return users


@pytest.fixture(scope="function")
def steve_uri(request: pytest.FixtureRequest, httpx_mock: HTTPXMock) -> str | Path:
    uri: tuple[str, Path] | Path = request.param
    if isinstance(uri, tuple):
        url, path = uri
        httpx_mock.add_response(url=url, content=path.read_bytes())
        return url
    return uri
