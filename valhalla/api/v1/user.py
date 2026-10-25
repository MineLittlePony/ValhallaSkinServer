from datetime import datetime
from uuid import UUID

from litestar import Request, Router, get
from litestar.di import NamedDependency, Provide
from litestar.exceptions import NotFoundException
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.params import FromPath, FromQuery

from valhalla import models, schemas
from valhalla.config import Settings
from valhalla.crud import CRUD


@get(
    "/user/{user_id:uuid}",
    summary="Get user textures by UUID",
    description="""
Retrieve the textures for a single user, looking them up by their UUID.

This endpoint has a rate limit of 60/minute. For requesting many user textures at once,
use the **Get multiple user textures** (`/api/v1/bulk_textures`) endpoint.
    """,
    middleware=[RateLimitConfig(("minute", 60)).middleware],
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    },
    cache=True,
    exclude_from_auth=True,
)
async def get_user_textures_by_uuid(
    request: Request,
    crud: NamedDependency[CRUD],
    user_id: FromPath[UUID],
    at: FromQuery[datetime | None] = None,
) -> schemas.UserTextures:
    """Get the currently logged in user information."""
    user = await crud.get_user_by_uuid(user_id)

    if user is None:
        raise NotFoundException

    return await get_user_textures(request, user, at, crud)


@get(
    "/user/lookup/name/{name:str}",
    summary="Get user textures by name",
    description="""
Look up a user by name, then return their active textures.

This acts as a convenience endpoint so you don't have to resolve a user's uuid before
fetching the textures.

    """,
    middleware=[RateLimitConfig(("minute", 20)).middleware],
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    },
    exclude_from_auth=True,
)
async def get_user_textures_by_name(
    request: Request,
    name: FromPath[str],
    crud: NamedDependency[CRUD],
    at: FromQuery[datetime | None] = None,
) -> schemas.UserTextures:
    """Lookup the texture of a user as of their last login."""
    user = await crud.get_user_by_name(name)

    if user is None:
        raise NotFoundException

    return await get_user_textures(request, user, at, crud)


async def get_user_textures(
    request: Request,
    user: models.User,
    at: datetime | None,
    crud: CRUD,
) -> schemas.UserTextures:
    config: Settings = request.app.state.config
    textures_url = config.get_textures_url(request)
    textures = await crud.get_user_textures(user, at=at)
    return schemas.UserTextures.from_sql(user, textures, textures_url)


router = Router(
    "",
    tags=["User Information"],
    route_handlers=[
        get_user_textures_by_uuid,
        get_user_textures_by_name,
    ],
)
