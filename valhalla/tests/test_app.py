import json
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest
from litestar.testing import AsyncTestClient
from pytest_httpx import HTTPXMock

from .conftest import TestUser, assets, settings

textures_url = "http://testserver.local/textures/"
steve_file = assets / "good/64x64.png"
steve_url = "https://assets.mojang.com/SkinTemplates/steve.png"
steve_hash = textures_url + steve_file.with_suffix(".txt").read_text().strip()


def build_request_kwargs(file: str | Path) -> tuple[str, dict]:
    if isinstance(file, Path):
        return "PUT", {
            "data": {"type": "skin"},
            "files": {"file": (file.name, file.read_bytes(), "image/png")},
        }
    return "POST", {
        "json": {"file": file, "type": "skin"},
    }


@pytest.mark.parametrize(
    "steve_uri",
    [(steve_url, steve_file), steve_file],
)
@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
async def test_texture_upload_post(
    steve_uri: Path | tuple[str, Path] | str,
    client: AsyncTestClient,
    user: TestUser,
    httpx_mock: HTTPXMock,
) -> None:
    if isinstance(steve_uri, tuple):
        steve_uri, file = steve_uri
        httpx_mock.add_response(url=steve_uri, content=file.read_bytes())
    method, kwargs = build_request_kwargs(steve_uri)
    upload_resp = await client.request(
        method, "/api/v1/textures", headers=user.auth_header, **kwargs
    )
    assert upload_resp.status_code == 204, upload_resp.content

    user_resp = await client.get("/api/v1/textures", headers=user.auth_header)
    assert user_resp.status_code == 200, user_resp.json()
    textures = user_resp.json()
    skin = textures["skin"]

    assert skin["url"] == steve_hash
    assert not skin["metadata"]

    anon_resp = await client.get(f"/api/v1/user/{user.uuid}")
    assert anon_resp.status_code == 200, anon_resp.json()
    assert anon_resp.json()["textures"] == textures

    byname_resp = await client.get(f"/api/v1/user/lookup/name/{user.name}")
    assert byname_resp.status_code == 200, byname_resp.json()
    assert byname_resp.json()["textures"] == textures

    byname_resp = await client.get(f"/api/v1/user/lookup/name/{user.name.lower()}")
    assert byname_resp.status_code == 200, byname_resp.json()
    assert byname_resp.json()["textures"] == textures


async def test_unknown_user_textures(client: AsyncTestClient) -> None:
    user = TestUser("UnknownUserName")
    resp = await client.get(f"/api/v1/user/{user.uuid}")
    assert resp.status_code == 404
    resp = await client.get(f"/api/v1/user/lookup/name/{user.name}6")
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "steve_uri",
    [steve_url, steve_file],
)
@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
async def test_unauthenticated_user_texture_upload(
    steve_uri: str, client: AsyncTestClient
) -> None:
    method, kwargs = build_request_kwargs(steve_uri)
    upload_resp = await client.request(method, "/api/v1/textures", **kwargs)
    assert upload_resp.status_code == 401, upload_resp.json()


async def test_non_image_upload(client: AsyncTestClient, user: TestUser) -> None:
    resp = await client.put(
        "/api/v1/textures",
        headers=user.auth_header,
        data={"type": "skin"},
        files={"file": ("file.txt", BytesIO(b"bad file"))},
    )
    assert resp.status_code == 400, resp.json()
    assert "cannot identify image file" in resp.json()["detail"]


async def test_very_large_upload(client: AsyncTestClient, user: TestUser) -> None:
    ten_megabytes_of_zeros = b"\0" * 10_000_000
    resp = await client.put(
        "/api/v1/textures",
        headers={
            **user.auth_header,
            # lie about the content-length
            "content-length": "1000",
        },
        data={"type": "skin"},
        files={"file": ("file.txt", BytesIO(ten_megabytes_of_zeros))},
    )
    assert resp.status_code == 413, resp.json()  # Request entity too large


async def test_bad_namespaced_tex_type(client: AsyncTestClient, user: TestUser) -> None:
    resp = await client.put(
        "/api/v1/textures",
        headers=user.auth_header,
        files={"file": (steve_file.name, steve_file.read_bytes(), "image/png")},
        data={"type": "minecraft:skin"},
    )
    assert resp.status_code == 400, resp.content


async def test_skin_metadata(client: AsyncTestClient, user: TestUser) -> None:
    resp = await client.put(
        "/api/v1/textures",
        data={"meta": json.dumps({"model": "slim"})},
        files={"file": (steve_file.name, steve_file.read_bytes(), "image/png")},
        headers=user.auth_header,
    )
    assert resp.status_code == 204, resp.content

    resp = await client.get("/api/v1/textures", headers=user.auth_header)
    assert resp.status_code == 200, resp.content
    assert resp.json()["skin"]["metadata"] == {"model": "slim"}


async def test_skin_metadata_url(client: AsyncTestClient, user: TestUser) -> None:
    resp = await client.post(
        "/api/v1/textures",
        json={
            "type": "skin",
            "file": steve_url,
            "meta": {"model": "slim"},
        },
        headers=user.auth_header,
    )
    assert resp.status_code == 204

    resp = await client.get("/api/v1/textures", headers=user.auth_header)
    assert resp.status_code == 200
    assert resp.json()["skin"]["metadata"] == {"model": "slim"}


async def test_skin_delete(client: AsyncTestClient, user: TestUser) -> None:
    await test_skin_metadata(client, user)

    resp = await client.delete(
        "/api/v1/textures", headers=user.auth_header, params={"type": "skin"}
    )

    assert resp.status_code == 204


async def test_multiple_users_with_same_name(
    httpx_mock: HTTPXMock,
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncTestClient,
) -> None:
    uuid = UUID("526d5b75-3b09-47fb-8f91-1efc8d2523a4")

    monkeypatch.setattr(settings, "online_mode", True)
    httpx_mock.add_response(
        method="GET",
        url=f"https://sessionserver.mojang.com/session/minecraft/hasJoined?username=username&serverId={settings.server_id}",
        json={"id": str(uuid), "name": "username"},
    )
    httpx_mock.add_response(
        method="GET",
        url=f"https://sessionserver.mojang.com/session/minecraft/hasJoined?username=UserName&serverId={settings.server_id}",
        json={"id": str(uuid), "name": "UserName"},
    )

    id1 = await TestUser("username").login(client)
    await client.post("/api/v1/textures", headers=id1.auth_header)

    id2 = await TestUser("UserName").login(client)
    await client.post("/api/v1/textures", headers=id2.auth_header)

    resp1 = (await client.get("/api/v1/user/lookup/name/username")).json()
    resp2 = (await client.get("/api/v1/user/lookup/name/UserName")).json()
    for resp in resp1, resp2:
        assert resp["profileId"] == str(id2.uuid)
        assert resp["profileName"] == id2.name
