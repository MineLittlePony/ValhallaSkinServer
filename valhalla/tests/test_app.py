import json
from io import BytesIO
from pathlib import Path

import pytest
from pytest_httpx import HTTPXMock

from ..config import settings
from .conftest import TestClient, TestUser, assets

textures_url = "http://testserver/textures/"
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
def test_texture_upload_post(
    steve_uri: Path | tuple[str, Path] | str,
    client: TestClient,
    user: TestUser,
    httpx_mock: HTTPXMock,
) -> None:
    if isinstance(steve_uri, tuple):
        steve_uri, file = steve_uri
        httpx_mock.add_response(url=steve_uri, content=file.read_bytes())
    method, kwargs = build_request_kwargs(steve_uri)
    upload_resp = client.request(
        method, "/api/v1/textures", headers=user.auth_header, **kwargs
    )
    assert upload_resp.status_code == 200, upload_resp.json()

    user_resp = client.get("/api/v1/textures", headers=user.auth_header)
    assert user_resp.status_code == 200, user_resp.json()
    textures = user_resp.json()
    skin = textures["skin"]

    assert skin["url"] == steve_hash
    assert not skin["metadata"]

    anon_resp = client.get(f"/api/v1/user/{user.uuid}")
    assert anon_resp.status_code == 200, anon_resp.json()
    assert anon_resp.json()["textures"] == textures


def test_unknown_user_textures(client: TestClient, user: TestUser) -> None:
    resp = client.get(f"/api/v1/user/{user.uuid}")
    assert resp.status_code == 404


@pytest.mark.parametrize(
    "steve_uri",
    [steve_url, steve_file],
)
@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
def test_unauthenticated_user_texture_upload(
    steve_uri: str, client: TestClient
) -> None:
    method, kwargs = build_request_kwargs(steve_uri)
    upload_resp = client.request(method, "/api/v1/textures", **kwargs)
    assert upload_resp.status_code == 401, upload_resp.json()


def test_non_image_upload(client: TestClient, user: TestUser) -> None:
    resp = client.put(
        "/api/v1/textures",
        headers=user.auth_header,
        data={"type": "skin"},
        files={"file": ("file.txt", BytesIO(b"bad file"))},
    )
    assert resp.status_code == 400, resp.json()
    assert "cannot identify image file" in resp.json()["detail"]


def test_very_large_upload(client: TestClient, user: TestUser) -> None:
    ten_megabytes_of_zeros = b"\0" * 10_000_000
    resp = client.put(
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


def test_env() -> None:
    assert not settings.env.isprod


def test_bad_namespaced_tex_type(client: TestClient, user: TestUser) -> None:
    resp = client.put(
        "/api/v1/textures",
        headers=user.auth_header,
        files={"file": (steve_file.name, steve_file.read_bytes(), "image/png")},
        data={"type": "minecraft:skin"},
    )
    assert resp.status_code == 400


def test_skin_metadata(client: TestClient, user: TestUser) -> None:
    resp = client.put(
        "/api/v1/textures",
        data={"meta": json.dumps({"model": "slim"})},
        files={"file": (steve_file.name, steve_file.read_bytes(), "image/png")},
        headers=user.auth_header,
    )
    assert resp.status_code == 200

    resp = client.get("/api/v1/textures", headers=user.auth_header)
    assert resp.status_code == 200
    assert resp.json()["skin"]["metadata"] == {"model": "slim"}


def test_skin_metadata_url(client: TestClient, user: TestUser) -> None:
    resp = client.post(
        "/api/v1/textures",
        json={
            "type": "skin",
            "file": steve_url,
            "meta": {"model": "slim"},
        },
        headers=user.auth_header,
    )
    assert resp.status_code == 200

    resp = client.get("/api/v1/textures", headers=user.auth_header)
    assert resp.status_code == 200
    assert resp.json()["skin"]["metadata"] == {"model": "slim"}


def test_skin_delete(client: TestClient, user: TestUser) -> None:
    test_skin_metadata(client, user)

    resp = client.delete(
        "/api/v1/textures", headers=user.auth_header, params={"type": "skin"}
    )

    assert resp.status_code == 200
