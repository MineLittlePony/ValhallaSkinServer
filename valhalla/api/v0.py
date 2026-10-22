import functools
from collections.abc import Awaitable, Callable

from litestar import Router, delete, get, post, put

from . import v1


def wrap_with_message[**P, R](
    fn: Callable[P, Awaitable[R]], msg: str
) -> Callable[P, Awaitable[dict[str, str]]]:
    @functools.wraps(fn)
    async def view(*args: P.args, **kwargs: P.kwargs) -> dict[str, str]:
        await fn(*args, **kwargs)
        return {"message": msg}

    return view


router = Router(
    "",
    include_in_schema=False,
    route_handlers=[
        post(
            "/auth/handshake",
            dependencies=v1.auth.minecraft_login.dependencies,
            exclude_from_auth=True,
            deprecated=True,
        )(v1.auth.minecraft_login.fn),
        post(
            "/auth/response",
            dependencies=v1.auth.minecraft_login_callback.dependencies,
            exclude_from_auth=True,
            deprecated=True,
        )(v1.auth.minecraft_login_callback.fn),
        get(
            "/user/{user_id:uuid}",
            dependencies=v1.user.get_user_textures_by_uuid.dependencies,
            exclude_from_auth=True,
            deprecated=True,
        )(v1.user.get_user_textures_by_uuid.fn),
        post(
            "/user/{user_id:uuid}/{skin_type:str}",
            status_code=200,
            dependencies=v1.legacy.post_skin_old.dependencies,
            deprecated=True,
        )(wrap_with_message(v1.legacy.post_skin_old.fn, "OK")),
        put(
            "/user/{user_id:uuid}/{skin_type:str}",
            dependencies=v1.legacy.put_skin_old.dependencies,
            deprecated=True,
        )(wrap_with_message(v1.legacy.put_skin_old.fn, "OK")),
        delete(
            "/user/{user_id:uuid}/{skin_type:str}",
            dependencies=v1.legacy.delete_skin_old.dependencies,
            status_code=200,
            deprecated=True,
        )(wrap_with_message(v1.legacy.delete_skin_old.fn, "skin cleared")),
    ],
)
