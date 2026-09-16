from typing import Annotated

from fastapi import APIRouter, Depends, Request

from ...crud import CRUD
from ...limit import limiter
from ...schemas import BulkRequest, BulkResponse
from .user import get_user_textures
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
    return BulkResponse(
        users=[
            await get_user_textures(user, None, crud, textures_url)
            async for user in crud.resolve_uuids(body.uuids)
        ]
    )
