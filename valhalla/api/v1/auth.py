import hashlib
import json
import secrets
import uuid
from datetime import timedelta
from typing import TypedDict

from litestar import Request, Router, get, post
from litestar.di import NamedDependency, Provide
from litestar.exceptions import PermissionDeniedException
from litestar.params import URLEncodedBody
from litestar.response import Redirect

from valhalla import auth, mojang
from valhalla.config import Settings
from valhalla.crud import CRUD
from valhalla.schemas import LoginMinecraftHandshakeResponse, LoginResponse

STORE_NAME = "auth-tokens"


@get("/logout")
async def logout() -> Redirect:
    response = Redirect("/", status_code=302)
    response.delete_cookie("token")
    return response


class LoginFormData(TypedDict):
    name: str


@post(
    "/minecraft",
    summary="Login for Minecraft",
    status_code=200,
    exclude_from_auth=True,
)
async def minecraft_login(
    request: Request,
    data: URLEncodedBody[LoginFormData],
) -> LoginMinecraftHandshakeResponse:
    """Login for Minecraft

    After calling this endpoint, send a POST request to Mojang's API with the
    `verifyToken` and `serverId`.

    After making the request to Mojang, call the endpoint
    `/api/v1/auth/minecraft/callback` with your `verifyToken`.
    """
    settings: Settings = request.app.state.config
    store = request.app.stores.get(STORE_NAME)
    # Generate a random 32 bit integer. It will be checked later.
    verify_token = secrets.randbits(32)
    await store.set(
        str(verify_token),
        json.dumps([data["name"], request.client]),
        expires_in=timedelta(seconds=30),
    )

    return LoginMinecraftHandshakeResponse(
        server_id=settings.server_id,
        verify_token=verify_token,
        offline=not settings.online_mode,
    )


class CallbackFormData(TypedDict):
    verifyToken: str
    name: str


@post(
    "/minecraft/callback",
    summary="Login Callback for Minecraft",
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    },
    status_code=200,
    exclude_from_auth=True,
)
async def minecraft_login_callback(
    request: Request,
    crud: NamedDependency[CRUD],
    data: URLEncodedBody[CallbackFormData],
) -> LoginResponse:
    """Login Callback for Minecraft"""
    settings: Settings = request.app.state.config
    verify_token = data["verifyToken"]
    name = data["name"]

    store = request.app.stores.get(STORE_NAME)
    value = await store.get(str(verify_token))
    await store.delete(str(verify_token))
    if value is None:
        raise PermissionDeniedException

    client = request.client
    if client is not None:
        client = list(client)

    data = json.loads(value)
    if data != [name, client]:
        raise PermissionDeniedException

    if settings.online_mode:
        joined = await mojang.has_joined(
            username=name,
            server_id=settings.server_id,
        )
        uid = joined.id
        name = joined.name
    else:
        # offline mode
        # calculate the offline player id instead of asking mojang
        offline_name = f"OfflinePlayer:{name}".encode()
        hash = hashlib.md5(offline_name, usedforsecurity=False).digest()
        uid = uuid.UUID(bytes=hash)

    user = await crud.get_or_create_user(uid, name)
    token = auth.token_from_user(request, user)
    auth_header = f"Bearer {token}"

    return LoginResponse(
        access_token=auth_header,
        user_id=user.uuid,
    )


router = Router(
    "/auth",
    tags=["Authentication"],
    route_handlers=[
        logout,
        minecraft_login,
        minecraft_login_callback,
    ],
)
