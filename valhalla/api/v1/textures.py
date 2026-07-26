from collections.abc import AsyncGenerator, AsyncIterable
from typing import Annotated, Any

import anyio.to_thread
import httpx2
from anyio import TemporaryFile
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Json
from starlette import status

from valhalla.config import settings

from ... import image, models, schemas
from ...auth import require_user
from ...byteconv import mb
from ...crud import CRUD
from ...files import Files
from .user import get_user_textures
from .utils import get_textures_url

router = APIRouter(tags=["Texture Uploads"])

max_upload_size = 5 * mb


@router.get("/textures")
async def get_texture(
    user: Annotated[models.User, Depends(require_user)],
    crud: Annotated[CRUD, Depends()],
    textures_url: Annotated[str, Depends(get_textures_url)],
) -> dict[str, schemas.Texture]:
    user_texts = await get_user_textures(user, None, crud, textures_url)
    return user_texts.textures


async def download_file(url: str, max_size: int) -> bytes:
    async with httpx2.AsyncClient() as http:
        try:
            head_response = await http.head(url)
            head_response.raise_for_status()
        except httpx2.HTTPError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error fetching file: {e}",
            ) from None

        file_size = head_response.headers.get("content-length")
        if not file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="file Content-Length is missing",
            )
        if file_size and int(file_size) > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="file Content-Length is too big",
            )

        async with http.stream("GET", url) as resp:
            file_size = int(resp.headers["content-length"])
            return await read_upload(resp.aiter_bytes(), file_size)


async def read_upload(file: AsyncIterable[bytes], file_size: int) -> bytes:
    real_file_size = 0
    async with TemporaryFile() as temp:
        async for chunk in file:
            real_file_size += len(chunk)
            if real_file_size > file_size:
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE)
            await temp.write(chunk)
        await temp.seek(0)
        return await temp.read()


async def valid_content_length(
    content_length: Annotated[int, Header(le=max_upload_size)],
) -> int:
    return content_length


async def iter_upload_file(file: UploadFile) -> AsyncGenerator[bytes, Any]:
    while chunk := await file.read(1024):
        yield chunk


@router.post("/textures")
async def post_texture(
    crud: Annotated[CRUD, Depends()],
    files: Annotated[Files, Depends()],
    user: Annotated[models.User, Depends(require_user)],
    body: schemas.TexturePost,
) -> None:
    file = await download_file(str(body.file), max_upload_size)
    await upload_file(user, body.type, file, body.meta, crud, files)
    await crud.db.commit()


@router.put("/textures")
async def put_texture(
    crud: Annotated[CRUD, Depends()],
    files: Annotated[Files, Depends()],
    user: Annotated[models.User, Depends(require_user)],
    file: Annotated[UploadFile, File()],
    file_size: Annotated[int, Depends(valid_content_length)],
    type: Annotated[schemas.TextureType, Form()] = "skin",
    meta: Annotated[Json[dict[str, str]] | None, Form()] = None,
) -> None:
    body = await read_upload(iter_upload_file(file), file_size)
    await upload_file(user, type, body, meta, crud, files)
    await crud.db.commit()


async def upload_file(
    user: models.User,
    texture_type: str,
    file: bytes,
    meta: dict[str, str] | None,
    crud: CRUD,
    files: Files,
) -> None:
    if texture_type in settings.texture_type_denylist:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "That texture type is not allowed"
        )
    texture_hash = await anyio.to_thread.run_sync(image.gen_skin_hash, file)
    upload = await crud.get_upload(texture_hash)
    if not upload:
        await anyio.to_thread.run_sync(files.put_file, texture_hash, file)
        upload = await crud.put_upload(user, texture_hash)

    await crud.put_texture(user, texture_type, upload, meta or {})


@router.delete("/textures")
async def delete_texture(
    user: Annotated[models.User, Depends(require_user)],
    crud: Annotated[CRUD, Depends()],
    type: schemas.TextureType,
) -> None:
    await crud.put_texture(user, type, None)
    await crud.db.commit()


class DeleteTexture(BaseModel):
    type: schemas.TextureType


# deprecated, delete shouldn't have a body, and it's missing a s
@router.delete("/texture", deprecated=True)
async def delete_texture_deprecated(
    texture: DeleteTexture,
    user: Annotated[models.User, Depends(require_user)],
    crud: Annotated[CRUD, Depends()],
) -> None:
    await delete_texture(user, crud, texture.type)
