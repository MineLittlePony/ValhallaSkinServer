import json
from io import BytesIO
from pathlib import Path
from typing import override
from uuid import UUID

import pytest
from litestar.testing import AsyncTestClient
from respx import MockRouter

from .conftest import TestUser, assets, settings


class MockPath(Path):
    _bytes = None

    @override
    def read_bytes(self) -> bytes:
        if self._bytes is None:
            self._bytes = super().read_bytes()
        return self._bytes


textures_url = "http://testserver.local/textures/"
steve_file = MockPath(assets / "good/64x64.png")
steve_url = "https://assets.mojang.com/SkinTemplates/steve.png"
steve_hash = textures_url + steve_file.with_suffix(".txt").read_text().strip()


@pytest.fixture(name="image_url")
def _mock_image_url(httpx2_mock: MockRouter) -> None:
    httpx2_mock.head(steve_url).respond(content=steve_file.read_bytes())
    httpx2_mock.get(steve_url).respond(content=steve_file.read_bytes())


async def _test_texture_upload_verify(client: AsyncTestClient, user: TestUser) -> None:
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


async def test_texture_upload_file(client: AsyncTestClient, user: TestUser) -> None:
    upload_resp = await client.put(
        "/api/v1/textures",
        headers=user.auth_header,
        files={"file": (steve_file.name, steve_file.read_bytes(), "image/png")},
    )
    assert upload_resp.status_code == 204, upload_resp.content

    await _test_texture_upload_verify(client, user)


@pytest.mark.usefixtures("image_url")
async def test_texture_upload_url(client: AsyncTestClient, user: TestUser) -> None:
    upload_resp = await client.post(
        "/api/v1/textures",
        headers=user.auth_header,
        json={"type": "skin", "file": steve_url},
    )
    assert upload_resp.status_code == 204, upload_resp.content

    await _test_texture_upload_verify(client, user)


async def test_unknown_user_textures(client: AsyncTestClient) -> None:
    user = TestUser("UnknownUserName")
    resp = await client.get(f"/api/v1/user/{user.uuid}")
    assert resp.status_code == 404
    resp = await client.get(f"/api/v1/user/lookup/name/{user.name}6")
    assert resp.status_code == 404


async def test_unauthenticated_user_texture_upload_file(
    client: AsyncTestClient,
) -> None:
    upload_resp = await client.put(
        "/api/v1/textures",
        files={"file": (steve_file.name, steve_file.read_bytes(), "image/png")},
    )
    assert upload_resp.status_code == 401, upload_resp.json()


async def test_unauthenticated_user_texture_upload_url(client: AsyncTestClient) -> None:
    upload_resp = await client.post(
        "/api/v1/textures", json={"type": "skin", "file": steve_url}
    )
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
    httpx2_mock: MockRouter,
    monkeypatch: pytest.MonkeyPatch,
    client: AsyncTestClient,
) -> None:
    uuid = UUID("526d5b75-3b09-47fb-8f91-1efc8d2523a4")

    monkeypatch.setattr(settings, "online_mode", True)
    httpx2_mock.get(
        url=f"https://sessionserver.mojang.com/session/minecraft/hasJoined?username=username&serverId={settings.server_id}",
    ).respond(
        json={"id": str(uuid), "name": "username"},
    )
    httpx2_mock.get(
        url=f"https://sessionserver.mojang.com/session/minecraft/hasJoined?username=UserName&serverId={settings.server_id}",
    ).respond(
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


async def test_https_redirect(client: AsyncTestClient) -> None:
    resp = await client.get(
        "/",
        follow_redirects=False,
        headers={"host": "skins.minelittlepony-mod.com"},
    )
    assert resp.status_code == 307
    assert resp.has_redirect_location
    assert resp.headers["location"] == "https://skins.minelittlepony-mod.com/"


@pytest.mark.parametrize("host", ["localhost", "foo.localhost", "skinserver:8000"])
async def test_https_not_redirect(host: str, client: AsyncTestClient) -> None:
    resp = await client.get(
        "/",
        follow_redirects=False,
        headers={"host": host},
    )
    assert resp.status_code == 302
    assert (
        resp.headers["location"]
        == "https://github.com/MineLittlePony/ValhallaSkinServer"
    )
