from datetime import datetime
from typing import Annotated
from urllib.parse import urljoin
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Request
from fastapi.exceptions import HTTPException

from ... import models, schemas
from ...crud import CRUD
from ...limit import limiter
from .utils import get_textures_url

router = APIRouter(tags=["User information"])


async def resolve_user_id(
    crud: Annotated[CRUD, Depends()],
    user_id: Annotated[UUID, Path()],
) -> models.User | None:
    return await crud.get_user_by_uuid(user_id)


async def resolve_user_name(
    crud: Annotated[CRUD, Depends()],
    name: Annotated[str, Path()],
) -> models.User | None:
    return await crud.get_user_by_name(name)


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
    textures_url: Annotated[str, Depends(get_textures_url)],
    crud: Annotated[CRUD, Depends()],
    user: Annotated[models.User | None, Depends(resolve_user_id)],
    at: datetime | None = None,
) -> schemas.UserTextures:
    """Get the currently logged in user information.

    This endpoint has a request limit of 60 per minute. For requesting
    multiple users at once, use the [`/api/v1/bulk_textures`][bt] endpoint.

    [bt]: #/User%20information/bulk_request_textures_api_v1_bulk_textures_post
    """
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
    textures_url: Annotated[str, Depends(get_textures_url)],
    crud: Annotated[CRUD, Depends()],
    user: Annotated[models.User | None, Depends(resolve_user_name)],
    at: datetime | None = None,
) -> schemas.UserTextures:
    """Lookup the texture of a user as of their last login."""
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
    return schemas.UserTextures(
        profile_id=user.uuid,
        profile_name=user.name,
        textures={
            k: schemas.Texture(
                url=urljoin(textures_url, v.upload.hash),
                metadata=v.meta,
            )
            for k, v in textures.items()
        },
    )
