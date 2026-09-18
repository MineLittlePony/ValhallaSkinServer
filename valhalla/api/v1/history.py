from datetime import datetime
from typing import Annotated
from urllib.parse import urljoin
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from valhalla.api.v1.utils import get_textures_url

from ... import models, schemas
from ...auth import require_user
from ...crud import CRUD

router = APIRouter(tags=["User History"])


@router.get("/history")
async def get_current_user_texture_history(
    *,
    user: Annotated[models.User, Depends(require_user)],
    crud: Annotated[CRUD, Depends()],
    textures_url: Annotated[str, Depends(get_textures_url)],
    limit: int | None = None,
    at: datetime | None = None,
    show_duplicates: bool = False,
) -> schemas.UserTextureHistory:
    return await get_user_texture_history(
        user=user,
        limit=limit,
        at=at,
        show_duplicates=show_duplicates,
        crud=crud,
        textures_url=textures_url,
    )


@router.get("/history/{user_id}")
async def get_user_texture_history_by_uuid(
    *,
    crud: Annotated[CRUD, Depends()],
    textures_url: Annotated[str, Depends(get_textures_url)],
    user_id: UUID,
    limit: int | None = None,
    at: datetime | None = None,
    show_duplicates: bool = False,
) -> schemas.UserTextureHistory:
    user = await crud.get_user_by_uuid(user_id)
    if user is None:
        raise HTTPException(404)

    return await get_user_texture_history(
        user=user,
        limit=limit,
        at=at,
        show_duplicates=show_duplicates,
        crud=crud,
        textures_url=textures_url,
    )


async def get_user_texture_history(
    *,
    user: models.User,
    limit: int | None,
    at: datetime | None,
    crud: CRUD,
    textures_url: str,
    show_duplicates: bool,
) -> schemas.UserTextureHistory:
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
