from collections.abc import AsyncGenerator, AsyncIterable
from typing import Any

import anyio.to_thread
import httpx2
from anyio import TemporaryFile
from litestar import Request, Router, delete, get, post, put, status_codes
from litestar.datastructures import UploadFile
from litestar.di import NamedDependency, Provide
from litestar.exceptions import ClientException, HTTPException
from litestar.params import FromQuery, JSONBody, MultipartBody
from pydantic import BaseModel, ConfigDict, Json

from valhalla import image, schemas
from valhalla.byteconv import mb
from valhalla.config import Settings
from valhalla.crud import CRUD
from valhalla.files import get_save_path, put_file
from valhalla.models import User

from .user import get_user_textures

max_upload_size = 5 * mb


class ContentTooLargeException(HTTPException):
    status_code = status_codes.HTTP_413_REQUEST_ENTITY_TOO_LARGE


@get(
    "/textures",
    summary="Get own textures",
    description="""
Gets the logged in user's currently active textures.
    """,
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    },
)
async def get_texture(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
) -> dict[str, schemas.Texture]:
    user_texts = await get_user_textures(request, request.user, None, crud)
    return user_texts.textures


async def download_file(url: str, max_size: int) -> bytes:
    async with httpx2.AsyncClient() as http:
        try:
            head_response = await http.head(url)
            head_response.raise_for_status()
        except httpx2.HTTPError as e:
            raise ClientException(
                detail=f"Error fetching file: {e}",
            ) from None

        file_size = head_response.headers.get("content-length")
        if not file_size:
            raise ClientException(
                detail="file Content-Length is missing",
            )
        if file_size and int(file_size) > max_size:
            raise ClientException(
                detail="file Content-Length is too big",
            )

        async with http.stream("GET", url) as resp:
            file_size = int(resp.headers["content-length"])
            if file_size > max_upload_size:
                raise ContentTooLargeException
            return await read_upload(resp.aiter_bytes())


async def read_upload(file: AsyncIterable[bytes]) -> bytes:
    real_file_size = 0
    async with TemporaryFile() as temp:
        async for chunk in file:
            real_file_size += len(chunk)
            if real_file_size > max_upload_size:
                raise ContentTooLargeException
            await temp.write(chunk)
        await temp.seek(0)
        return await temp.read()


async def iter_upload_file(file: UploadFile) -> AsyncGenerator[bytes, Any]:
    while chunk := await file.read(1024):
        yield chunk


@post(
    "/textures",
    summary="Set a texture from a URL",
    description="""
Sets the logged in user's active texture by downloading a URL.

Upload sizes are limited to 5MB.
    """,
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    },
    raises=[ContentTooLargeException],
)
async def post_texture(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    data: JSONBody[schemas.TexturePost],
) -> None:
    file = await download_file(str(data.file), max_upload_size)
    await upload_file(request, data.type, file, data.meta, crud)
    await crud.db.commit()


class TexturesPut(BaseModel):
    file: UploadFile
    type: schemas.TextureType = "skin"
    meta: Json[dict[str, str]] | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)


@put(
    "/textures",
    summary="Upload a texture",
    description="""
Sets the logged in user's active textures by uploading an image.

Upload sizes are limited to 5MB.
    """,
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    },
    raises=[ContentTooLargeException],
)
async def put_texture(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    data: MultipartBody[TexturesPut],
) -> None:
    if "content-length" in data.file.headers:
        max_len = int(data.file.headers["content-length"])
        if max_len > max_upload_size:
            raise ContentTooLargeException

    body = await read_upload(iter_upload_file(data.file))
    await upload_file(request, data.type, body, data.meta, crud)
    await crud.db.commit()


def upload_to_file_store(config: Settings, hash: str, file: bytes) -> None:
    save_path = get_save_path(config)
    put_file(save_path, hash, file)


async def upload_file(
    request: Request[User, Any, Any],
    texture_type: str,
    file: bytes,
    meta: dict[str, str] | None,
    crud: CRUD,
) -> None:
    settings: Settings = request.app.state.config
    if texture_type in settings.texture_type_denylist:
        raise ClientException(detail="That texture type is not allowed")
    texture_hash = await anyio.to_thread.run_sync(image.gen_skin_hash, file)
    upload = await crud.get_upload(texture_hash)
    if not upload:
        await anyio.to_thread.run_sync(
            upload_to_file_store, settings, texture_hash, file
        )
        upload = await crud.put_upload(request.user, texture_hash)

    await crud.put_texture(request.user, texture_type, upload, meta or {})


@delete(
    "/textures",
    summary="Delete a texture (query)",
    description="""
Deactivates one of the logged in user's active textures.
    """,
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    },
)
async def delete_texture(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    type: FromQuery[schemas.TextureType],
) -> None:
    await crud.put_texture(request.user, type, None)
    await crud.db.commit()


class DeleteTexture(BaseModel):
    type: schemas.TextureType


# deprecated, delete shouldn't have a body, and it's missing a s
@delete(
    "/texture",
    summary="Delete a texture (formdata)",
    description="""
Deactivates one of the logged in user's active textures.

This endpoint does not follow REST standards, as it accepts a body in a DELETE method.
Please prefer to use the query version.
    """,
    dependencies=delete_texture.dependencies,
    deprecated=True,
)
async def delete_texture_deprecated(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    data: JSONBody[DeleteTexture],
) -> None:
    await delete_texture.fn(request, crud, data.type)


router = Router(
    "",
    tags=["Texture Uploads"],
    security=[{"BearerToken": []}],
    route_handlers=[
        get_texture,
        put_texture,
        post_texture,
        delete_texture,
        delete_texture_deprecated,
    ],
)
