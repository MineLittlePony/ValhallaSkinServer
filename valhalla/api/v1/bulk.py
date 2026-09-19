from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ...crud import CRUD
from ...limit import limiter
from ...schemas import BulkRequest, BulkResponse, UserTextures
from .utils import get_textures_url

router = APIRouter(tags=["User information"])


@router.post("/bulk_textures")
@limiter.shared_limit(
    "10/minute",
    scope="user",
    error_message=(
        "You have surpassed the request limit for this endpoint of 10 requests per"
        " minute. Please don't try to scrape skins. Open an issue if you require"
        " scraping."
    ),
)
async def bulk_request_textures(
    request: Request,
    body: BulkRequest,
    crud: Annotated[CRUD, Depends()],
    textures_url: str = Depends(get_textures_url),
) -> BulkResponse:
    """Bulk request several user textures.

    If a requested user does not have any textures, it is ignored.
    """
    users = await crud.get_users_by_uuid_bulk(body.uuids)
    by_uuid = {u.uuid: u for u in users}
    user_data = await crud.get_user_textures_bulk(users)
    return BulkResponse(
        users=[
            UserTextures.from_sql(by_uuid[user], textures, textures_url)
            for user, textures in user_data.items()
        ]
    )
