from dataclasses import dataclass
from typing import Any
from uuid import UUID

from litestar import Request, Router, delete, post, put
from litestar.datastructures import UploadFile
from litestar.di import NamedDependency
from litestar.exceptions import PermissionDeniedException
from litestar.params import FromPath, FromQuery, MultipartBody, URLEncodedBody
from pydantic import AnyHttpUrl

from ... import schemas
from ...crud import CRUD
from ...models import User
from ...schemas import BaseModel
from . import auth, textures
from .textures import LimitContentLength


class PostFormData(BaseModel):
    file: AnyHttpUrl


@post(
    "/user/{user_id:uuid}/{skin_type:str}",
    status_code=200,
    dependencies=textures.post_texture.dependencies,
    include_in_schema=False,
)
async def post_skin_old(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    data: URLEncodedBody[PostFormData],
    user_id: FromQuery[UUID],
    skin_type: FromQuery[str],
) -> None:
    """Upload a skin texture from a url

    Deprecated: Use the /textures endpoint to upload skins
    """
    if user_id != request.user.uuid:
        raise PermissionDeniedException
    form = await request.form()
    meta = {k: v for k, v in form.items() if isinstance(v, str)}
    body = schemas.TexturePost.model_construct(
        type=skin_type,
        file=data.file,
        meta=meta,
    )
    await textures.post_texture.fn(request, crud, body)


@dataclass
class PutFormData:
    file: UploadFile


@put(
    "/user/{user_id:uuid}/{skin_type:str}",
    dependencies=textures.put_texture.dependencies,
    include_in_schema=False,
)
async def put_skin_old(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    user_id: FromPath[UUID],
    skin_type: FromPath[str],
    content_length: LimitContentLength,
    data: MultipartBody[PutFormData],
) -> None:
    """Upload a skin texture from a file

    Deprecated: Use the /textures endpoint to upload skins
    """
    if user_id != request.user.uuid:
        raise PermissionDeniedException

    form = await request.form()
    meta = {k: v for k, v in form.items() if isinstance(v, str)}
    body = textures.TexturesPut.model_construct(
        file=data.file,
        type=skin_type,
        meta=meta,
    )
    await textures.put_texture.fn(
        request,
        crud,
        body,
        content_length,
    )


@delete(
    "/user/{user_id:uuid}/{skin_type:str}",
    dependencies=textures.delete_texture.dependencies,
    status_code=200,
    include_in_schema=False,
)
async def delete_skin_old(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    user_id: FromPath[UUID],
    skin_type: FromPath[str],
) -> None:
    if user_id != request.user.uuid:
        raise PermissionDeniedException
    await textures.delete_texture.fn(request, crud, skin_type)


router = Router(
    "",
    route_handlers=[
        post_skin_old,
        put_skin_old,
        delete_skin_old,
        post(
            "/auth/handshake",
            dependencies=auth.minecraft_login.dependencies,
            opt=auth.minecraft_login.opt,
            include_in_schema=False,
        )(auth.minecraft_login.fn),
        post(
            "/auth/response",
            dependencies=auth.minecraft_login_callback.dependencies,
            opt=auth.minecraft_login_callback.opt,
            include_in_schema=False,
        )(auth.minecraft_login_callback.fn),
    ],
)
