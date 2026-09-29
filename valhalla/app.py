import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import boto3
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import create_async_engine
from starlette.middleware.sessions import SessionMiddleware

import valhalla

from . import api, auth, limit, models
from .config import Settings
from .database import SessionLocal

log = logging.getLogger("uvicorn.error")


def create_app(config: Settings | None = None) -> FastAPI:
    if config is None:
        config = Settings()

    @asynccontextmanager
    async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
        app.state.config = config

        if config.online_mode is False:
            log.warning(
                "online_mode is set to false. This is insecure and it's recommended to"
                " set it to true."
            )

        engine = create_async_engine(config.get_database_url())
        SessionLocal.configure(bind=engine)

        async with engine.begin() as session:
            await session.run_sync(models.Base.metadata.create_all)

        if config.textures_bucket and config.verify_aws_credentials:
            sts_client = boto3.client("sts")
            sts_client.get_caller_identity()

        yield

    app = FastAPI(
        title="Valhalla Skin Server",
        version=".".join(valhalla.__version__.split(".")[:2]),
        description=valhalla.__usage__,
        license_info={
            "name": "Licensed with Open Source",
            "identifier": valhalla.__metadata__.get("License-Expression"),
        },
        lifespan=app_lifespan,
    )

    limit.setup(app)
    auth.init_jwk(config)

    @app.get("/")
    async def index() -> RedirectResponse:
        for url in valhalla.__metadata__.get_all("Project-URL", []):
            name, url = str(url).split(", ")
            if name.lower() == "repository":
                return RedirectResponse(url, status.HTTP_308_PERMANENT_REDIRECT)

        raise HTTPException(status.HTTP_404_NOT_FOUND)

    if "HEROKU" in os.environ:
        app.add_middleware(HTTPSRedirectMiddleware)

    app.add_middleware(CORSMiddleware, allow_origins=["*"])
    app.add_middleware(SessionMiddleware, secret_key=config.secret_key)

    app.include_router(api.router, prefix="/api")

    if config.textures_bucket is None:
        os.makedirs(config.textures_path, exist_ok=True)
        static_textures = StaticFiles(directory=config.textures_path)
        app.mount("/textures", static_textures, name="textures")

    return app
