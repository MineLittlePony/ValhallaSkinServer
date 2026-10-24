from dataclasses import dataclass
from typing import Any

from litestar import Request, Router, delete, post, put, status_codes
from litestar.connection import ASGIConnection
from litestar.datastructures import UploadFile
from litestar.di import NamedDependency
from litestar.exceptions import PermissionDeniedException
from litestar.handlers import BaseRouteHandler
from litestar.params import FromPath, FromQuery, MultipartBody, URLEncodedBody
from pydantic import AnyHttpUrl

from valhalla import schemas
from valhalla.crud import CRUD
from valhalla.models import User
from valhalla.schemas import BaseModel

from . import auth, textures


def check_user_id(
    connection: ASGIConnection[Any, User, Any, Any], _: BaseRouteHandler
) -> None:
    """
    Checks that the logged in user matches the `user_id` from the request `path_params`.
    If they don't match, raises a `PermissionDeniedException`.
    """
    if connection.path_params["user_id"] != connection.user.uuid:
        raise PermissionDeniedException


class PostFormData(BaseModel):
    file: AnyHttpUrl


@post(
    "/user/{user_id:uuid}/{skin_type:str}",
    status_code=status_codes.HTTP_200_OK,
    dependencies=textures.post_texture.dependencies,
    guards=[check_user_id],
    include_in_schema=False,
)
async def post_skin_old(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    data: URLEncodedBody[PostFormData],
    skin_type: FromQuery[str],
) -> None:
    """Upload a skin texture from a url

    Deprecated: Use the /textures endpoint to upload skins
    """
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
    status_code=textures.put_texture.status_code,
    dependencies=textures.put_texture.dependencies,
    raises=textures.put_texture.raises,
    guards=[check_user_id],
    include_in_schema=False,
)
async def put_skin_old(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    skin_type: FromPath[str],
    data: MultipartBody[PutFormData],
) -> None:
    """Upload a skin texture from a file

    Deprecated: Use the /textures endpoint to upload skins
    """

    form = await request.form()
    meta = {k: v for k, v in form.items() if isinstance(v, str)}
    body = textures.TexturesPut.model_construct(
        file=data.file,
        type=skin_type,
        meta=meta,
    )
    await textures.put_texture.fn(request, crud, body)


@delete(
    "/user/{user_id:uuid}/{skin_type:str}",
    dependencies=textures.delete_texture.dependencies,
    guards=[check_user_id],
    status_code=status_codes.HTTP_200_OK,
    include_in_schema=False,
)
async def delete_skin_old(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    skin_type: FromPath[str],
) -> None:
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
