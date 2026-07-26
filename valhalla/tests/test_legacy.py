from pathlib import Path
from uuid import uuid4

import pytest
from pytest_httpx import HTTPXMock

from .conftest import TestClient, TestUser
from .test_app import steve_file, steve_hash, steve_url


def build_request_kwargs(file: str | Path) -> tuple[str, dict]:
    if isinstance(file, Path):
        return "PUT", {
            "files": {"file": (file.name, file.open("rb"), "image/png")},
        }
    return "POST", {
        "data": {"file": file},
    }


@pytest.mark.parametrize(
    "steve_uri",
    [(steve_url, steve_file), steve_file],
)
@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
def test_legacy_upload(
    steve_uri: tuple[str, Path] | Path | str,
    client: TestClient,
    user: TestUser,
    httpx_mock: HTTPXMock,
) -> None:
    if isinstance(steve_uri, tuple):
        steve_uri, file = steve_uri
        httpx_mock.add_response(url=steve_uri, content=file.read_bytes())
    method, kwargs = build_request_kwargs(steve_uri)
    resp = client.request(
        method, f"/api/v1/user/{user.uuid}/skin", headers=user.auth_header, **kwargs
    )
    assert resp.status_code == 200, resp.json()


@pytest.mark.parametrize(
    "steve_uri",
    [steve_url, steve_file],
)
@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
def test_legacy_upload_wrong_user(
    steve_uri: str | Path, client: TestClient, user: TestUser
) -> None:
    method, kwargs = build_request_kwargs(steve_uri)
    resp = client.request(
        method, f"/api/v1/user/{uuid4()}/skin", headers=user.auth_header, **kwargs
    )
    assert resp.status_code == 403, resp.json()


@pytest.mark.parametrize(
    "steve_uri",
    [(steve_url, steve_file), steve_file],
)
@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
def test_legacy_v0(
    steve_uri: tuple[str, Path] | Path | str,
    client: TestClient,
    user: TestUser,
    httpx_mock: HTTPXMock,
) -> None:
    if isinstance(steve_uri, tuple):
        steve_uri, file = steve_uri
        httpx_mock.add_response(url=steve_uri, content=file.read_bytes())
    method, kwargs = build_request_kwargs(steve_uri)
    resp = client.request(
        method, f"/api/user/{user.uuid}/skin", headers=user.auth_header, **kwargs
    )
    assert resp.status_code == 200
    assert resp.json() == {"message": "OK"}

    resp = client.get(f"/api/user/{user.uuid}")
    assert resp.status_code == 200

    data = resp.json()
    skin = data["textures"]["skin"]["url"]
    assert skin == steve_hash

    resp = client.delete(f"/api/user/{user.uuid}/skin", headers=user.auth_header)
    assert resp.status_code == 200
    assert resp.json() == {"message": "skin cleared"}

    resp = client.get(f"/api/user/{user.uuid}")
    assert resp.status_code == 200

    assert "skin" not in resp.json()["textures"]
