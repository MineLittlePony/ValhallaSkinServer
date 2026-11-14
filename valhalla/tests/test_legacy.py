from uuid import uuid4

import pytest
from httpx2 import AsyncClient
from respx import MockRouter

from .conftest import TestUser
from .test_app import steve_file, steve_hash, steve_url


@pytest.fixture(name="image_url")
def _mock_image_url(httpx2_mock: MockRouter) -> None:
    httpx2_mock.head(steve_url).respond(content=steve_file.read_bytes())
    httpx2_mock.get(steve_url).respond(content=steve_file.read_bytes())


@pytest.mark.usefixtures("image_url")
async def test_legacy_upload_file(client: AsyncClient, user: TestUser) -> None:
    resp = await client.post(
        f"/api/v1/user/{user.uuid}/skin",
        headers=user.auth_header,
        data={"file": steve_url},
    )
    assert resp.status_code == 204, resp.content


async def test_legacy_upload_uri(client: AsyncClient, user: TestUser) -> None:
    content = steve_file.read_bytes()
    resp = await client.put(
        f"/api/v1/user/{user.uuid}/skin",
        headers=user.auth_header,
        files={"file": (steve_file.name, content, "image/png")},
    )
    assert resp.status_code == 204, resp.content


# @pytest.mark.usefixtures("image_url")
async def test_legacy_upload_wrong_user_url(
    client: AsyncClient, user: TestUser
) -> None:
    resp = await client.post(
        f"/api/v1/user/{uuid4()}/skin",
        headers=user.auth_header,
        data={"file": steve_url},
    )
    assert resp.status_code == 403, resp.json()


async def test_legacy_upload_wrong_user_file(
    client: AsyncClient, user: TestUser
) -> None:
    content = steve_file.read_bytes()
    resp = await client.put(
        f"/api/v1/user/{uuid4()}/skin",
        headers=user.auth_header,
        files={"file": (steve_file.name, content, "image/png")},
    )
    assert resp.status_code == 403, resp.json()


async def _test_legacy_v0_upload_verify(client: AsyncClient, user: TestUser) -> None:
    resp = await client.get(f"/api/user/{user.uuid}")
    assert resp.status_code == 200, resp.content

    data = resp.json()
    skin = data["textures"]["skin"]["url"]
    assert skin == steve_hash

    resp = await client.delete(f"/api/user/{user.uuid}/skin", headers=user.auth_header)
    assert resp.status_code == 200, resp.content
    assert resp.json() == {"message": "skin cleared"}

    resp = await client.get(f"/api/user/{user.uuid}")
    assert resp.status_code == 200, resp.content

    assert "skin" not in resp.json()["textures"]


async def test_legacy_v0_upload_file(client: AsyncClient, user: TestUser) -> None:
    content = steve_file.read_bytes()
    resp = await client.put(
        f"/api/user/{user.uuid}/skin",
        headers=user.auth_header,
        files={"file": (steve_file.name, content, "image/png")},
    )
    assert resp.status_code == 200, resp.content
    assert resp.json() == {"message": "OK"}

    await _test_legacy_v0_upload_verify(client, user)


@pytest.mark.usefixtures("image_url")
async def test_legacy_v0_upload_url(
    client: AsyncClient,
    user: TestUser,
) -> None:
    resp = await client.post(
        f"/api/user/{user.uuid}/skin",
        headers=user.auth_header,
        data={"file": steve_url},
    )
    assert resp.status_code == 200, resp.content
    assert resp.json() == {"message": "OK"}

    await _test_legacy_v0_upload_verify(client, user)
