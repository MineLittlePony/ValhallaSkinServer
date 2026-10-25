from typing import cast
from uuid import UUID

from advanced_alchemy.config import SQLAlchemyAsyncConfig
from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
from authlib.oidc.core import UserInfo
from litestar import Request
from litestar.connection import ASGIConnection
from litestar.exceptions import PermissionDeniedException
from litestar.security.jwt import JWTAuth, Token

from .crud import CRUD
from .models import User
from .xbox import XboxLoginError, login_with_xbox


async def user_from_token(token: Token, connection: ASGIConnection) -> User:
    sql_plugin = connection.app.plugins.get(SQLAlchemyPlugin)
    config = cast("SQLAlchemyAsyncConfig", sql_plugin.config[0])

    async with config.get_session() as db_session:
        crud = CRUD(db_session)
        user_id = UUID(token.sub)
        user = await crud.get_user_by_uuid(user_id)
        if user is None:
            raise PermissionDeniedException
        return user


def token_from_user(request: Request, user: User) -> str:
    jwt: JWTAuth = request.app.state.jwt
    return jwt.create_token(str(user.uuid))


async def login_with_xbox_userinfo(request: Request, token: UserInfo) -> User:
    try:
        profile = await login_with_xbox(str(token["access_token"]))
    except XboxLoginError as e:
        raise PermissionDeniedException(detail=str(e)) from e

    sql = request.app.plugins.get(SQLAlchemyPlugin)
    config = cast("SQLAlchemyAsyncConfig", sql.config[0])
    async with config.get_session() as session:
        return await CRUD(session).get_or_create_user(profile.id, profile.name)
