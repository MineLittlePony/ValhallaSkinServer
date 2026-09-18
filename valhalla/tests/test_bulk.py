from uuid import UUID

from .conftest import TestClient, TestUser, assets

test_skin = assets / "good" / "64x64.png"


def test_unknown_bulk_user(client: TestClient, user: TestUser) -> None:
    uuid = UUID(bytes=b"\0" * 16)
    resp = client.post(
        "/api/v1/bulk_textures",
        json={
            "uuids": [
                str(uuid),
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["users"]) == 0


def test_bulk_users(client: TestClient, users: list[TestUser]) -> None:
    # setup
    for u in users:
        resp = client.put(
            "/api/v1/textures",
            headers=u.auth_header,
            files={
                "file": (test_skin.name, test_skin.open("rb"), "image/png"),
            },
        )
        assert resp.status_code == 200

    uuids = [str(u.uuid) for u in users]

    resp = client.post("/api/v1/bulk_textures", json={"uuids": uuids})
    assert resp.status_code == 200

    data = resp.json()
    original_users = [user["profileId"] for user in data["users"]]
    assert original_users == uuids
