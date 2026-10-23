import functools
from collections.abc import Awaitable, Callable

from litestar import Router
from litestar.handlers import HTTPRouteHandler

from . import v1


def wrap_with_message[**P, R](
    fn: Callable[P, Awaitable[R]], msg: str
) -> Callable[P, Awaitable[dict[str, str]]]:
    @functools.wraps(fn)
    async def view(*args: P.args, **kwargs: P.kwargs) -> dict[str, str]:
        await fn(*args, **kwargs)
        return {"message": msg}

    return view


def copy_route(new_path: str | list[str], route: HTTPRouteHandler) -> HTTPRouteHandler:
    return HTTPRouteHandler(
        new_path,
        http_method=list(route.http_methods),
        status_code=route.status_code,
        name=f"v0_{route.handler_name}",
        dependencies=route.dependencies,
        guards=route.guards,
        middleware=route.middleware,
        opt=route.opt,
        sync_to_thread=route.sync_to_thread,
        deprecated=True,
    )(route.fn)


router = Router(
    "",
    include_in_schema=False,
    route_handlers=[
        copy_route("/auth/handshake", v1.auth.minecraft_login),
        copy_route("/auth/response", v1.auth.minecraft_login_callback),
        copy_route("/user/{user_id:uuid}", v1.user.get_user_textures_by_uuid),
        copy_route("/user/{user_id:uuid}/{skin_type:str}", v1.legacy.post_skin_old)(
            wrap_with_message(v1.legacy.post_skin_old.fn, "OK")
        ),
        copy_route("/user/{user_id:uuid}/{skin_type:str}", v1.legacy.put_skin_old)(
            wrap_with_message(v1.legacy.put_skin_old.fn, "OK")
        ),
        copy_route("/user/{user_id:uuid}/{skin_type:str}", v1.legacy.delete_skin_old)(
            wrap_with_message(v1.legacy.delete_skin_old.fn, "skin cleared")
        ),
    ],
)
