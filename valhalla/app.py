import os
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import valhalla

from . import api, limit, models
from .config import settings
from .database import engine


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    async with engine.begin() as session:
        await session.run_sync(models.Base.metadata.create_all)

    if settings.textures_bucket and settings.verify_aws_credentials:
        from .files import verify_aws_credentials

        verify_aws_credentials()

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


@app.middleware("http")
async def redirect_http_to_https(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    # redirect to https if using a standard http port. If non-standard, assume dev env
    scheme = request.headers.get("X-Forwarded-Proto", request.url.scheme)
    port = int(request.headers.get("X-Forwarded-Port", request.url.port or 0))
    if port in (80, 443) and scheme == "http":
        url = request.url.replace(scheme="https")
        return RedirectResponse(url, status.HTTP_308_PERMANENT_REDIRECT)
    return await call_next(request)


app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

app.include_router(api.router, prefix="/api")

if settings.textures_bucket is None:
    os.makedirs(settings.textures_path, exist_ok=True)
    static_textures = StaticFiles(directory=settings.textures_path)
    app.mount("/textures", static_textures, name="textures")
