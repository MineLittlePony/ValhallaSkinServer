from litestar import Router

from . import auth, bulk, history, legacy, textures, user

router = Router(
    "/v1",
    route_handlers=[
        auth.router,
        bulk.router,
        history.router,
        legacy.router,
        textures.router,
        user.router,
    ],
)
