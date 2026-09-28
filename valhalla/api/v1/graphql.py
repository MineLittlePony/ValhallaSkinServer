from datetime import datetime
from urllib.parse import urljoin
from uuid import UUID

import strawberry
from strawberry.fastapi import GraphQLRouter
from strawberry.scalars import JSON

from valhalla.config import settings
from valhalla.crud import CRUD


@strawberry.type
class Texture:
    type: str
    url: str
    metadata: JSON


@strawberry.type
class User:
    profile_id: UUID
    profile_name: str | None
    textures: list[Texture]


@strawberry.type
class HistoryItem:
    url: str
    type: str
    metadata: JSON
    start_time: datetime
    end_time: datetime | None


@strawberry.type
class Query:
    @strawberry.field
    async def user(
        self,
        profile_id: UUID,
        at: datetime | None = None,
        types: list[str] | None = None,
    ) -> User | None:
        async with CRUD.create() as crud:
            user = await crud.get_user_by_uuid(profile_id)
            if user is None:
                return None

            textures = await crud.get_user_textures(user, at=at, types=types)

            return User(
                profile_id=user.uuid,
                profile_name=user.name,
                textures=[
                    Texture(
                        type=t.tex_type,
                        url=urljoin(settings.get_textures_url() or "", t.upload.hash),
                        metadata=t.meta,
                    )
                    for t in (textures).values()
                ],
            )

    @strawberry.field
    async def users(
        profile_ids: list[UUID],
        *,
        types: list[str] | None = None,
    ) -> list[User]:
        async with CRUD.create() as crud:
            users = await crud.get_users_by_uuid_bulk(profile_ids)
            users_by_id = {u.uuid: u for u in users}
            textures = await crud.get_user_textures_bulk(users, types=types)

            base_url = settings.get_textures_url() or ""

            return [
                User(
                    profile_id=(user := users_by_id[uid]).uuid,
                    profile_name=user.name,
                    textures=[
                        Texture(
                            type=t.tex_type,
                            url=urljoin(base_url, t.upload.hash),
                            metadata=t.meta,
                        )
                        for t in textures.values()
                    ],
                )
                for uid, textures in textures.items()
            ]

    @strawberry.field
    async def history(profile_id: UUID) -> list[HistoryItem] | None:
        async with CRUD.create() as crud:
            user = await crud.get_user_by_uuid(profile_id)
            if user is None:
                return None
            history = await crud.get_user_textures_history(user)
            return [
                HistoryItem(
                    url=h.upload.hash,
                    metadata=h.meta,
                    type=h.tex_type,
                    start_time=h.start_time,
                    end_time=h.end_time,
                )
                for h in history.values()
                for h in h
            ]


schema = strawberry.Schema(query=Query)

graphql = GraphQLRouter(schema, path="/graphql", graphql_ide="apollo-sandbox")
