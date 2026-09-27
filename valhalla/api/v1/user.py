from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request
from fastapi.exceptions import HTTPException

from ... import models, schemas
from ...crud import CRUD
from ...limit import limiter
from .utils import get_textures_url

router = APIRouter(tags=["User information"])


@router.get("/user/{user_id}")
@limiter.shared_limit(
    "60/minute",
    scope="user",
    error_message=(
        "You have surpassed the request limit for this endpoint of 60 requests per"
        " minute. Use '/api/v1/bulk_textures' if you have multiple users to request."
        " For more details, see https://skins.minelittlepony-mod.com/docs."
    ),
)
async def get_user_textures_by_uuid(
    request: Request,
    user_id: Annotated[UUID, Path()],
    textures_url: Annotated[str, Depends(get_textures_url)],
    at: datetime | None = None,
) -> schemas.UserTextures:
    """Get the currently logged in user information.

    This endpoint has a request limit of 60 per minute. For requesting
    multiple users at once, use the [`/api/v1/bulk_textures`][bt] endpoint.

    [bt]: #/User%20information/bulk_request_textures_api_v1_bulk_textures_post
    """
    async with CRUD.create() as crud:
        user = await crud.get_user_by_uuid(user_id)

        if user is None:
            raise HTTPException(404)

        return await get_user_textures(user, at, crud, textures_url)


@router.get("/user/lookup/name/{name}")
@limiter.shared_limit(
    "20/minute",
    scope="user",
    error_message=(
        "You have surpassed the request limit for this endpoint of 20 requests per"
        " minute."
    ),
)
async def get_user_textures_by_name(
    request: Request,
    name: str,
    textures_url: Annotated[str, Depends(get_textures_url)],
    at: datetime | None = None,
) -> schemas.UserTextures:
    """Lookup the texture of a user as of their last login."""
    async with CRUD.create() as crud:
        user = await crud.get_user_by_name(name)

        if user is None:
            raise HTTPException(404)

        return await get_user_textures(user, at, crud, textures_url)


async def get_user_textures(
    user: models.User,
    at: datetime | None,
    crud: CRUD,
    textures_url: str,
) -> schemas.UserTextures:
    textures = await crud.get_user_textures(user, at=at)
    return schemas.UserTextures.from_sql(user, textures, textures_url)
