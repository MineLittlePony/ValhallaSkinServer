from uuid import UUID

import httpx2
from fastapi import HTTPException

from .schemas import BaseModel

# ?username=username&serverId=hash&ip=ip"
_VALIDATE = "https://sessionserver.mojang.com/session/minecraft/hasJoined"


class HasJoinedResponse(BaseModel):
    id: UUID
    name: str


async def has_joined(*, username: str, server_id: str) -> HasJoinedResponse:
    """Validates a login against Mojang's servers

    http://wiki.vg/Protocol_Encryption#Authentication
    """
    params = {
        "username": username,
        "serverId": server_id,
    }
    async with httpx2.AsyncClient() as client:
        response = await client.get(_VALIDATE, params=params)
        if response.is_success:
            try:
                data = response.json()
            except ValueError:
                pass
            else:
                return HasJoinedResponse.model_validate(data)
        raise HTTPException(401)
