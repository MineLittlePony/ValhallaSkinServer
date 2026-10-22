from uuid import UUID

from advanced_alchemy.config import SQLAlchemyAsyncConfig
from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
from litestar import Request
from litestar.connection import ASGIConnection
from litestar.security.jwt import JWTAuth, Token

from .crud import CRUD
from .models import User


async def user_from_token(token: Token, connection: ASGIConnection) -> User:
    sql_plugin = connection.app.plugins.get(SQLAlchemyPlugin)
    config = sql_plugin.config[0]
    assert isinstance(config, SQLAlchemyAsyncConfig)

    async with config.get_session() as db_session:
        crud = CRUD(db_session)
        user_id = UUID(token.sub)
        user = await crud.get_user_by_uuid(user_id)
        if user is None:
            raise PermissionError
        return user


def token_from_user(request: Request, user: User) -> str:
    jwt: JWTAuth = request.app.state.jwt
    return jwt.create_token(str(user.uuid))
