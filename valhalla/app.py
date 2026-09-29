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
from starlette.middleware.sessions import SessionMiddleware

import valhalla

from . import api, limit, models
from .config import settings
from .database import engine

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    if settings.online_mode is False:
        log.warning(
            "online_mode is set to false. This is insecure and it's recommended to"
            " set it to true."
        )

    async with engine.begin() as session:
        await session.run_sync(models.Base.metadata.create_all)

    if settings.textures_bucket and settings.verify_aws_credentials:
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
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.include_router(api.router, prefix="/api")

if settings.textures_bucket is None:
    os.makedirs(settings.textures_path, exist_ok=True)
    static_textures = StaticFiles(directory=settings.textures_path)
    app.mount("/textures", static_textures, name="textures")
