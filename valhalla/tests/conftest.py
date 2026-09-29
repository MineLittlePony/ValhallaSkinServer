import hashlib
import os.path
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Literal, Self
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from pydantic_settings import SettingsConfigDict
from pytest_httpx import HTTPXMock
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine

from ..app import create_app
from ..config import Settings
from ..models import Base

assets = Path(__file__).parent / "assets"

tempdir = tempfile.mkdtemp(prefix="pytest-valhalla-")
engine = create_engine(
    f"sqlite+pysqlite:////{tempdir}/test.db", connect_args={"check_same_thread": False}
)
async_engine = create_async_engine(
    f"sqlite+aiosqlite:////{tempdir}/test.db", connect_args={"check_same_thread": False}
)


@pytest.fixture(autouse=True, scope="session")
def cleanup() -> Generator[None]:
    yield
    shutil.rmtree(tempdir)


class TestConfig(Settings):
    model_config = SettingsConfigDict(
        env_file=None,
        toml_file=None,
    )


settings = TestConfig(
    database_url=str(async_engine.url),
    online_mode=False,
    textures_path=os.path.join(tempdir, "textures"),
    textures_url=None,
    server_id="testing",
)


@pytest.fixture
def client() -> Generator[TestClient]:
    app = create_app(settings)

    with TestClient(app) as client:
        with engine.begin() as conn:
            Base.metadata.create_all(conn)

        yield client

        with engine.begin() as conn:
            Base.metadata.drop_all(conn)


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
