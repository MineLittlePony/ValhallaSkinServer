import hashlib
import json
import secrets
import uuid
from datetime import timedelta
from typing import TypedDict

# from authlib.integrations.base_client.async_app import OAuth2Base
from litestar import Request, Router, get, post
from litestar.datastructures import Cookie
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, PermissionDeniedException
from litestar.params import URLEncodedBody
from litestar.response import Redirect

from ... import auth, mojang, xbox
from ...config import Settings
from ...crud import CRUD
from ...schemas import LoginMinecraftHandshakeResponse, LoginResponse

STORE_NAME = "auth-tokens"

# xboxlive: OAuth2Base


# @asynccontextmanager
# async def lifespan(app: Litestar) -> AsyncGenerator[None]:
#     global xboxlive
#     config: Config = app.state["config"]
#     xboxlive = OAuth().register(
#         "xboxlive",
#         client_id=config.xbox_live_client_id,
#         client_secret=config.xbox_live_client_secret,
#         server_metadata_url=config.xbox_live_server_metadata_url,
#         client_kwargs=config.xbox_live_client_kwargs,
#     )
#     yield


@get("/logout")
async def logout() -> Redirect:
    response = Redirect("/", status_code=302)
    response.delete_cookie("token")
    return response


class LoginFormData(TypedDict):
    name: str


@post("/minecraft", status_code=200, exclude_from_auth=True)
async def minecraft_login(
    request: Request,
    data: URLEncodedBody[LoginFormData],
) -> LoginMinecraftHandshakeResponse:
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


@get("/xbox", exclude_from_auth=True)
async def xbox_login(request: Request) -> Redirect:
    callback = str(request.url_for("xbox_login_callback"))
    callback = callback.replace("http://127.0.0.1", "http://localhost")
    return await xboxlive.authorize_redirect(request, callback)


@get("/xbox/callback", exclude_from_auth=True)
async def xbox_login_callback(request: Request) -> Redirect:
    if not request.client:
        raise ClientException
    try:
        token = await xboxlive.authorize_access_token(request)
        profile = await xbox.login_with_xbox(token["access_token"])
    except (OAuthError, xbox.XboxLoginError) as e:
        raise PermissionDeniedException(detail=str(e)) from None
    else:
        async with CRUD.create() as crud:
            user = await crud.get_or_create_user(profile.id, profile.name)
            expires = timedelta(days=365)
            token = auth.token_from_user(request, user)

            response = Redirect(
                "/docs",
                cookies=[
                    Cookie(
                        "token",
                        value=token,
                        secure=True,
                        httponly=True,
                        expires=int(expires.total_seconds()),
                    )
                ],
            )

            await crud.db.commit()
            return response


router = Router(
    "/auth",
    tags=["Authentication"],
    route_handlers=[
        logout,
        minecraft_login,
        minecraft_login_callback,
        # xbox_login,
        # xbox_login_callback,
    ],
)
