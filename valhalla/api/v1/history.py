from datetime import datetime
from typing import Any, Literal
from urllib.parse import urljoin
from uuid import UUID

from litestar import Request, Router, get, status_codes
from litestar.di import NamedDependency, Provide
from litestar.exceptions import NotFoundException
from litestar.openapi import ResponseSpec
from litestar.params import FromPath, FromQuery
from typing_extensions import TypedDict

from valhalla import schemas
from valhalla.config import Settings
from valhalla.crud import CRUD
from valhalla.models import User


@get(
    summary="Get own texture history",
    description="""
Gets the current users texture history, sorted most recent first.

By default, duplicate textures will be hidden. To show them, send the request
with `?show_duplicates=true` in the query params.
    """,
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    },
    security=[{"BearerToken": []}],
)
async def get_current_user_texture_history(
    *,
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    limit: FromQuery[int | None] = None,
    at: FromQuery[datetime | None] = None,
    show_duplicates: FromQuery[bool] = False,
) -> schemas.UserTextureHistory:
    return await get_user_texture_history(
        request.user,
        request=request,
        limit=limit,
        at=at,
        show_duplicates=show_duplicates,
        crud=crud,
    )


@get(
    "/{user_id:uuid}",
    summary="Get user's history by uuid",
    description="""
Gets a users texture history, sorted most recent first.

By default, duplicate textures will be hidden. To show them, send the request
with `?show_duplicates=true` in the query params.
    """,
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    },
    exclude_from_auth=True,
    raises=[NotFoundException],
    responses={
        status_codes.HTTP_404_NOT_FOUND: ResponseSpec(
            TypedDict[
                {
                    "status_code": Literal[404],
                    "detail": Literal["User not found"],
                }
            ],
            description="`user_id` does not match a user",
        )
    },
    cache=True,
)
async def get_user_texture_history_by_uuid(
    *,
    request: Request[User, Any, Any],
    user_id: FromPath[UUID],
    crud: NamedDependency[CRUD],
    limit: FromQuery[int | None] = None,
    at: FromQuery[datetime | None] = None,
    show_duplicates: FromQuery[bool] = False,
) -> schemas.UserTextureHistory:
    user = await crud.get_user_by_uuid(user_id)
    if user is None:
        raise NotFoundException(detail="User not found")
    return await get_user_texture_history(
        user,
        request=request,
        limit=limit,
        at=at,
        show_duplicates=show_duplicates,
        crud=crud,
    )


async def get_user_texture_history(
    user: User,
    *,
    request: Request[User, Any, Any],
    limit: int | None,
    at: datetime | None,
    crud: CRUD,
    show_duplicates: bool,
) -> schemas.UserTextureHistory:
    config: Settings = request.app.state.config
    textures_url = config.get_textures_url(request)
    textures = await crud.get_user_textures_history(
        user=user,
        limit=limit,
        at=at,
        show_duplicates=show_duplicates,
    )
    return schemas.UserTextureHistory(
        profile_id=user.uuid,
        profile_name=user.name,
        textures={
            key: [
                schemas.TextureHistoryEntry(
                    url=urljoin(textures_url, entry.upload.hash),
                    metadata=entry.meta,
                    start_time=entry.start_time,
                    end_time=entry.end_time,
                )
                for entry in value
            ]
            for key, value in textures.items()
        },
    )


router = Router(
    "/history",
    tags=["User History"],
    route_handlers=[
        get_current_user_texture_history,
        get_user_texture_history_by_uuid,
    ],
)
