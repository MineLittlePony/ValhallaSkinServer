from datetime import UTC, datetime
from functools import partial
from typing import Annotated
from uuid import UUID

from fastapi import File, Form, HTTPException, UploadFile, status
from pydantic import AnyHttpUrl, ConfigDict, Field
from pydantic import BaseModel as PydanticBaseModel
from pydantic.alias_generators import to_camel
from pydantic.functional_serializers import PlainSerializer
from pydantic.functional_validators import AfterValidator


def serialize_datetime(dt: datetime) -> int:
    # convert to milliseconds
    return int(dt.timestamp() * 1000)


Timestamp = Annotated[
    datetime,
    PlainSerializer(
        serialize_datetime,
        return_type=int,
        when_used="json-unless-none",
    ),
]


class BaseModel(PydanticBaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )


class LoginMinecraftHandshakeResponse(BaseModel):
    server_id: str
    verify_token: int
    offline: bool = False


class LoginResponse(BaseModel):
    access_token: str
    user_id: UUID


class Texture(BaseModel):
    url: str
    metadata: dict[str, str] | None = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://textures.minelittlepony-mod.com/textures/4bbd43fd83ee1053c42994c4bf1db9496ede6b73",
                "metadata": {"model": "default"},
            }
        }
    )


class UserTextures(BaseModel):
    timestamp: Timestamp = Field(default_factory=partial(datetime.now, UTC))
    profile_id: UUID
    profile_name: str | None
    textures: dict[str, Texture]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "timestamp": 1667697567511,
                "profileId": "51aa42eb7aef4b6ab758ab0fadac5ab5",
                "profileName": "Sollace",
                "textures": {
                    "skin": {
                        "url": "https://textures.minelittlepony-mod.com/textures/4bbd43fd83ee1053c42994c4bf1db9496ede6b73",
                        "metadata": {"model": "default"},
                    }
                },
            }
        }
    )


class TextureHistoryEntry(BaseModel):
    url: str
    metadata: dict[str, str] | None = None
    start_time: Timestamp
    end_time: Timestamp | None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://textures.minelittlepony-mod.com/textures/4bbd43fd83ee1053c42994c4bf1db9496ede6b73",
                "metadata": {
                    "model": "default",
                },
                "startTime": 1667697567511,
                "endTime": "null",
            }
        }
    )


class UserTextureHistory(BaseModel):
    profile_id: UUID
    profile_name: str | None
    textures: dict[str, list[TextureHistoryEntry]]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "profileId": "51aa42eb7aef4b6ab758ab0fadac5ab5",
                "profileName": "Sollace",
                "textures": [
                    {
                        "url": "https://textures.minelittlepony-mod.com/textures/4bbd43fd83ee1053c42994c4bf1db9496ede6b73",
                        "metadata": {
                            "model": "default",
                        },
                        "startTime": 1667697567511,
                        "endTime": "null",
                    }
                ],
            }
        }
    )


class TextureUpload(BaseModel):
    type: str = Form()
    file: UploadFile = File(media_type="image/png")
    metadata: dict[str, str] | None = Form(None)


def validate_texture_type(s: str) -> str:
    if ":" in s:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API v1 does not support namespaced texture types.",
        )
    return s


TextureType = Annotated[str, AfterValidator(validate_texture_type)]


class TexturePost(BaseModel):
    type: TextureType
    file: AnyHttpUrl
    meta: dict[str, str] | None = None


class BulkRequest(BaseModel):
    uuids: list[UUID]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "uuids": [
                    "51aa42eb7-aef4-b6ab-758a-b0fadac5ab5",
                ]
            }
        }
    )


class BulkResponse(BaseModel):
    users: list[UserTextures]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": [
                    {
                        "timestamp": 1667697567511,
                        "profileId": "51aa42eb7aef4b6ab758ab0fadac5ab5",
                        "profileName": "Sollace",
                        "textures": {
                            "skin": {
                                "url": "https://textures.minelittlepony-mod.com/textures/4bbd43fd83ee1053c42994c4bf1db9496ede6b73",
                                "metadata": {"model": "default"},
                            }
                        },
                    },
                ]
            }
        }
    )
