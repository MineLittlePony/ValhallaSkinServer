import secrets
from datetime import timedelta
from typing import Annotated

from authlib.integrations.starlette_client import OAuth, OAuthError, StarletteOAuth2App
from expiringdict import ExpiringDict
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from ... import auth, mojang, xbox
from ...config import settings
from ...crud import CRUD
from ...schemas import LoginMinecraftHandshakeResponse, LoginResponse

router = APIRouter(tags=["Authentication"])


# Validate tokens are kept 100 at a time for 30 seconds each
validate_tokens: dict[int, tuple[str, str]] = ExpiringDict(100, 30)


@router.get("/auth/logout", status_code=302)
async def logout() -> RedirectResponse:
    response = RedirectResponse("/", status_code=302)
    response.delete_cookie("token")
    return response


def get_client_ip(request: Request) -> str:
    if not request.client:
        raise HTTPException(400)
    return request.headers.get("X-Forwarded-For", request.client.host)


@router.post("/auth/minecraft")
async def minecraft_login(
    client: Annotated[str, Depends(get_client_ip)],
    name: Annotated[str, Form()],
) -> LoginMinecraftHandshakeResponse:
    # Generate a random 32 bit integer. It will be checked later.
    verify_token = secrets.randbits(32)
    validate_tokens[verify_token] = name, client

    return LoginMinecraftHandshakeResponse(
        server_id=settings.server_id,
        verify_token=verify_token,
    )


@router.post("/auth/minecraft/callback")
async def minecraft_login_callback(
    response: Response,
    crud: Annotated[CRUD, Depends()],
    client: Annotated[str, Depends(get_client_ip)],
    name: Annotated[str, Form()],
    verify_token: Annotated[int, Form(alias="verifyToken")],
) -> LoginResponse:
    if verify_token not in validate_tokens:
        raise HTTPException(403)

    try:
        xname, addr = validate_tokens[verify_token]
        if xname != name:
            raise HTTPException(403)
        if addr != client:
            raise HTTPException(403)
    finally:
        del validate_tokens[verify_token]

    joined = await mojang.has_joined(
        username=name,
        server_id=settings.server_id,
    )

    user = await crud.get_or_create_user(joined.id, joined.name)
    token = auth.token_from_user(user, expire_in=timedelta(hours=1))
    auth_header = f"Bearer {token}"

    response.headers["Authorization"] = token

    try:
        return LoginResponse(
            access_token=auth_header,
            user_id=user.uuid,
        )
    finally:
        await crud.db.commit()


xboxlive: StarletteOAuth2App = OAuth().register(
    "xboxlive",
    client_id=settings.xbox_live_client_id,
    client_secret=settings.xbox_live_client_secret,
    server_metadata_url=settings.xbox_live_server_metadata_url,
    client_kwargs=settings.xbox_live_client_kwargs,
)


@router.api_route("/auth/xbox")
async def xbox_login(request: Request) -> RedirectResponse:
    callback = str(request.url_for("xbox_login_callback"))
    callback = callback.replace("http://127.0.0.1", "http://localhost")
    return await xboxlive.authorize_redirect(request, callback)


@router.api_route("/auth/xbox/callback")
async def xbox_login_callback(
    request: Request, crud: Annotated[CRUD, Depends()]
) -> RedirectResponse:
    if not request.client:
        raise HTTPException(400)
    try:
        token = await xboxlive.authorize_access_token(request)
        profile = await xbox.login_with_xbox(token["access_token"])
    except (OAuthError, xbox.XboxLoginError) as e:
        raise HTTPException(403, str(e)) from None
    else:
        user = await crud.get_or_create_user(profile.id, profile.name)
        expires = timedelta(days=365)
        token = auth.token_from_user(user, expire_in=expires)

        response = RedirectResponse("/docs")
        response.set_cookie(
            "token",
            token,
            secure=True,
            httponly=True,
            expires=int(expires.total_seconds()),
        )

        await crud.db.commit()
        return response
