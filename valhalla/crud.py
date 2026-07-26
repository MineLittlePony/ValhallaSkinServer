# sqlalchemy isn't 100% with type checking, so disable it in pyright
# mypy has it disabled in pyproject.toml
# pyright: reportGeneralTypeIssues=false
from collections import defaultdict
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import update
from sqlalchemy.sql.expression import func

from . import models
from .db import get_db


@dataclass
class CRUD:
    db: Annotated[AsyncSession, Depends(get_db)]

    async def get_user(self, user_id: int) -> models.User | None:
        result = await self.db.execute(
            select(models.User).where(models.User.id == user_id).limit(1)
        )
        return result.scalar()

    async def get_user_by_name(self, name: str) -> models.User | None:
        result = await self.db.execute(
            select(models.User)
            .where(func.lower(models.User.name) == name.lower())
            .limit(1)
        )
        return result.scalar()

    async def get_user_by_uuid(self, uuid: UUID) -> models.User | None:
        result = await self.db.execute(
            select(models.User).where(models.User.uuid == uuid).limit(1)
        )
        return result.scalar()

    async def resolve_uuids(self, uuids: list[UUID]) -> AsyncIterator[models.User]:
        for uid in uuids:
            usr = await self.get_user_by_uuid(uid)
            if usr:
                yield usr

    async def get_user_textures(
        self,
        user: models.User,
        *,
        at: datetime | None = None,
    ) -> dict[str, models.Texture]:
        result = await self.db.execute(
            select(models.Texture)
            .options(selectinload(models.Texture.upload))
            .where(
                models.Texture.id.in_(
                    select(func.max(models.Texture.id))
                    .where(
                        models.Texture.user_id == user.id,
                        models.Texture.end_time == None  # noqa: E711
                        if at is None
                        else models.Texture.end_time < at,
                    )
                    .order_by(models.Texture.tex_type)
                    .group_by(models.Texture.tex_type)
                )
            )
        )
        return {item.tex_type: item for item in result.scalars()}

    async def get_user_textures_history(
        self,
        user: models.User,
        *,
        limit: int | None = None,
        at: datetime | None = None,
    ) -> dict[str, list[models.Texture]]:
        result = await self.db.stream_scalars(
            select(models.Texture)
            .options(selectinload(models.Texture.upload))
            .where(
                models.Texture.user_id == user.id,
                *(() if at is None else (models.Texture.end_time < at,)),
            )
            .order_by(models.Texture.tex_type, models.Texture.id.desc())
            .group_by(models.Texture.tex_type, models.Texture.id),
        )

        results: dict[str, list[models.Texture]] = defaultdict(list)
        async for item in result:
            if item.tex_type in results and len(results[item.tex_type]) == limit:
                continue
            results[item.tex_type].append(item)

        return dict(results)

    async def _clear_duplicate_names(self, name: str) -> None:
        await self.db.execute(
            update(models.User)
            .where(
                func.lower(models.User.name) == name.lower(),
            )
            .values({models.User.name: None})
        )

    async def get_or_create_user(self, uuid: UUID, name: str) -> models.User:
        user = await self.get_user_by_uuid(uuid)
        if user is None:
            await self._clear_duplicate_names(name)
            user = models.User(uuid=uuid, name=name)
            self.db.add(user)

            await self.db.commit()
            await self.db.refresh(user)
        elif user.name != name:
            await self._clear_duplicate_names(name)
            user.name = name

            await self.db.commit()

        return user

    async def get_upload(self, texture_hash: str) -> models.Upload | None:
        results = await self.db.execute(
            select(models.Upload).where(models.Upload.hash == texture_hash).limit(1)
        )
        return results.scalar()

    async def put_upload(self, user: models.User, texture_hash: str) -> models.Upload:
        upload = models.Upload(
            hash=texture_hash,
            user_id=user.id,
        )
        self.db.add(upload)
        return upload

    async def put_texture(
        self,
        user: models.User,
        tex_type: str,
        upload: models.Upload | None,
        meta: dict[str, str] | None = None,
    ) -> None:
        await self.db.execute(
            update(models.Texture)
            .where(
                models.Texture.user_id == user.id,
                models.Texture.tex_type == tex_type,
            )
            .values({models.Texture.end_time: datetime.now(UTC)}),
        )
        if upload:
            self.db.add(
                models.Texture(
                    user_id=user.id,
                    upload_id=upload.id,
                    tex_type=tex_type,
                    meta=meta or {},
                )
            )
        await self.db.commit()
