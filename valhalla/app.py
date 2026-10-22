import hashlib
import os

import boto3
from advanced_alchemy.extensions.litestar import SQLAlchemyAsyncConfig, SQLAlchemyPlugin
from litestar import Litestar, Request, get
from litestar import status_codes as status
from litestar.config.compression import CompressionConfig
from litestar.config.cors import CORSConfig
from litestar.datastructures import State
from litestar.exceptions import NotFoundException
from litestar.middleware.session.client_side import CookieBackendConfig
from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import (
    RapidocRenderPlugin,
    RedocRenderPlugin,
    ScalarRenderPlugin,
    StoplightRenderPlugin,
    SwaggerRenderPlugin,
)
from litestar.openapi.spec import License
from litestar.plugins.pydantic import PydanticPlugin
from litestar.response import Redirect
from litestar.security.jwt import JWTCookieAuth
from litestar.static_files import create_static_files_router
from litestar.stores.base import Store
from litestar.stores.valkey import ValkeyStore

import valhalla

from . import api, auth
from .auth import OAuthConfig, OAuthPlugin
from .config import Settings
from .models import Base, User


def create_app(config: Settings | None = None) -> Litestar:
    if config is None:
        config = Settings()

    async def on_startup(app: Litestar) -> None:
        if config.online_mode is False:
            app.get_logger().warning(
                "online_mode is set to false. This is insecure and it's recommended to"
                " set it to true."
            )

        if config.textures_bucket and config.verify_aws_credentials:
            sts_client = boto3.client("sts")
            sts_client.get_caller_identity()

    @get("/", include_in_schema=False, exclude_from_auth=True)
    async def index() -> Redirect:
        for url in valhalla.__metadata__.get_all("Project-URL", []):
            name, url = str(url).split(", ")
            if name.lower() == "repository":
                return Redirect(url, status_code=status.HTTP_308_PERMANENT_REDIRECT)
        raise NotFoundException

    static_files = []
    if config.textures_bucket is None:
        os.makedirs(config.textures_path, exist_ok=True)
        static_files.append(
            create_static_files_router(
                path="/textures",
                directories=[config.textures_path],
                name="textures",
            )
        )

    stores: dict[str, Store] = {}
    if config.redis_url is not None:
        stores["rate_limit"] = ValkeyStore.with_client(config.redis_url)

    sqlalchemy_config = SQLAlchemyAsyncConfig(
        connection_string=config.get_database_url(),
        metadata=Base.metadata,
    )

    jwt_auth = JWTCookieAuth[User](
        token_secret=config.secret_key,
        retrieve_user_handler=auth.user_from_token,
        exclude=[
            "^/docs",
        ],
    )

    auth_config = {}
    if config.xbox_live_client_id and config.xbox_live_client_secret:
        auth_config["xbox"] = OAuthConfig(
            server_metadata_url=config.xbox_live_server_metadata_url,
            client_id=config.xbox_live_client_id,
            client_secret=config.xbox_live_client_secret,
            client_kwargs=config.xbox_live_client_kwargs,
            route_prefix="/api/v1",
            retrieve_user_info=auth.login_with_xbox_userinfo,
        )

    async def dependency_config(request: Request) -> Settings:
        return request.state["config"]

    return Litestar(
        route_handlers=[
            index,
            *static_files,
            api.router,
        ],
        openapi_config=OpenAPIConfig(
            path="/docs",
            title="Valhalla Skin Server",
            version=".".join(valhalla.__version__.split(".")[:2]),
            description=valhalla.__usage__,
            license=License(
                name="GNU Affero General Public License",
                identifier="AGPL-3.0-only",
                url="https://github.com/MineLittlePony/ValhallaSkinServer/blob/main/LICENSE",
            ),
            render_plugins=[
                ScalarRenderPlugin(),
                RapidocRenderPlugin(),
                RedocRenderPlugin(),
                StoplightRenderPlugin(),
                SwaggerRenderPlugin(),
            ],
        ),
        compression_config=CompressionConfig("gzip"),
        cors_config=CORSConfig(allow_origins=["*"]),
        middleware=[
            CookieBackendConfig(
                secret=hashlib.sha256(config.secret_key.encode()).digest(),
            ).middleware,
            jwt_auth.middleware,
        ],
        state=State(
            {
                "config": config,
                "jwt": jwt_auth,
            }
        ),
        stores=stores,
        plugins=[
            PydanticPlugin(prefer_alias=True),
            SQLAlchemyPlugin(sqlalchemy_config),
            OAuthPlugin(auth_config),
        ],
        on_startup=[
            on_startup,
        ],
    )
