from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from litestar import Request, Router, get
from litestar.di import NamedDependency, Provide
from litestar.params import FromQuery

from ... import schemas
from ...config import Settings
from ...crud import CRUD
from ...models import User


@get(
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    }
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
        request=request,
        limit=limit,
        at=at,
        show_duplicates=show_duplicates,
        crud=crud,
    )


@get(
    "/{user_id:uuid}",
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    },
    exclude_from_auth=True,
)
async def get_user_texture_history_by_uuid(
    *,
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    limit: FromQuery[int | None] = None,
    at: FromQuery[datetime | None] = None,
    show_duplicates: FromQuery[bool] = False,
) -> schemas.UserTextureHistory:
    return await get_user_texture_history(
        request=request,
        limit=limit,
        at=at,
        show_duplicates=show_duplicates,
        crud=crud,
    )


async def get_user_texture_history(
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
        user=request.user,
        limit=limit,
        at=at,
        show_duplicates=show_duplicates,
    )
    return schemas.UserTextureHistory(
        profile_id=request.user.uuid,
        profile_name=request.user.name,
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
