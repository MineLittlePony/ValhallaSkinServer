from typing import Any

from litestar import Request, Router, post, status_codes
from litestar.di import NamedDependency, Provide
from litestar.middleware.rate_limit import RateLimitConfig
from litestar.params import JSONBody

from valhalla.config import Settings
from valhalla.crud import CRUD
from valhalla.models import User
from valhalla.schemas import BulkRequest, BulkResponse, UserTextures


@post(
    "/bulk_textures",
    summary="Get multiple user textures",
    description="""
Call this endpoint to reduce load on the server when requesting many users.

Requesting this endpoint with a single UUID is forbidden. All requests must contain at
least 2 UUIDs.

For a single UUID, see the **Get user textures by UUID** (`/api/v1/user/{user_id}`)
endpoint.

    """,
    status_code=status_codes.HTTP_200_OK,
    middleware=[RateLimitConfig(("minute", 10)).middleware],
    dependencies={
        "crud": Provide(CRUD, sync_to_thread=False),
    },
    exclude_from_auth=True,
)
async def bulk_request_textures(
    request: Request[User, Any, Any],
    crud: NamedDependency[CRUD],
    data: JSONBody[BulkRequest],
) -> BulkResponse:
    """Bulk request several user textures.

    If a requested user does not have any textures, it is ignored.
    """
    config: Settings = request.app.state.config
    textures_url = config.get_textures_url(request)
    users = await crud.get_users_by_uuid_bulk(data.uuids)
    by_uuid = {u.uuid: u for u in users}
    user_data = await crud.get_user_textures_bulk(users)
    return BulkResponse(
        users=[
            UserTextures.from_sql(by_uuid[user], textures, textures_url)
            for user, textures in user_data.items()
        ]
    )


router = Router(
    "",
    tags=["User Information"],
    route_handlers=[bulk_request_textures],
)
