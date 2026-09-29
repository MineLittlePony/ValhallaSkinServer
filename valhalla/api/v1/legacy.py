from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from pydantic import AnyHttpUrl
from starlette import status

from ... import models, schemas
from ...auth import require_user_id
from ...config import Config
from ...crud import CRUD
from ...files import Files
from . import auth, textures

router = APIRouter(deprecated=True)

router.add_api_route(
    "/auth/handshake",
    auth.minecraft_login,
    methods=["POST"],
    tags=["Authentication"],
    summary="Start authentication via Minecraft",
    description="Aliased to `/api/v1/auth/minecraft`",
)
router.add_api_route(
    "/auth/response",
    auth.minecraft_login_callback,
    methods=["POST"],
    tags=["Authentication"],
    summary="Callback for authentication via Minecraft",
    description="Aliased to `/api/v1/auth/minecraft/callback`",
)


async def check_user_id(user: models.User, user_id: UUID) -> None:
    if user_id != user.uuid:
        raise HTTPException(status.HTTP_403_FORBIDDEN)


@router.post("/user/{user_id}/{skin_type}", tags=["Texture Uploads"])
async def post_skin_old(
    request: Request,
    config: Config,
    file: Annotated[AnyHttpUrl, Form()],
    current_user_id: Annotated[int, Depends(require_user_id)],
    files: Annotated[Files, Depends()],
    user_id: UUID,
    skin_type: str,
) -> None:
    """Upload a skin texture from a url

    Deprecated: Use the /textures endpoint to upload skins
    """
    async with CRUD.create() as crud:
        user = await crud.require_user(current_user_id)
        await check_user_id(user, user_id)
        form = await request.form()
        meta = {k: v for k, v in form.items() if isinstance(v, str)}
        body = schemas.TexturePost(type=skin_type, file=file, meta=meta)
        await textures.post_texture_internal(config, files, user, crud, body)


@router.put("/user/{user_id}/{skin_type}", tags=["Texture Uploads"])
async def put_skin_old(
    request: Request,
    config: Config,
    current_user_id: Annotated[int, Depends(require_user_id)],
    files: Annotated[Files, Depends()],
    file: Annotated[UploadFile, File()],
    file_size: Annotated[int, Depends(textures.valid_content_length)],
    user_id: UUID,
    skin_type: str,
) -> None:
    """Upload a skin texture from a file

    Deprecated: Use the /textures endpoint to upload skins
    """
    async with CRUD.create() as crud:
        user = await crud.require_user(current_user_id)
        await check_user_id(user, user_id)
        form = await request.form()
        meta = {k: v for k, v in form.items() if isinstance(v, str)}
        await textures.put_texture_internal(
            config, files, user, crud, file, file_size, skin_type, meta
        )


@router.delete("/user/{user_id}/{skin_type}", tags=["Texture Uploads"])
async def delete_skin_old(
    current_user_id: Annotated[int, Depends(require_user_id)],
    user_id: UUID,
    skin_type: str,
) -> None:
    async with CRUD.create() as crud:
        user = await crud.require_user(current_user_id)
        await check_user_id(user, user_id)
        await textures.delete_texture_internal(user, crud, skin_type)
