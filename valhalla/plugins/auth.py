from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, TypedDict, override
from uuid import UUID

from authlib.integrations.base_client import OAuthError
from authlib.oidc.core import UserInfo
from litestar import Litestar, Request, Response, Router, get, status_codes
from litestar.config.app import AppConfig
from litestar.exceptions import PermissionDeniedException
from litestar.openapi.spec import SecurityRequirement
from litestar.plugins import InitPlugin
from litestar.security.jwt import JWTCookieAuth
from litestar.types import Dependencies, Guard, Middleware

from valhalla.authlib import OAuth
from valhalla.authlib.apps import LitestarOAuth1App, LitestarOAuth2App


class BaseUser(Protocol):
    uuid: UUID


@dataclass(kw_only=True)
class OAuthConfig[UserT: BaseUser = BaseUser]:
    # oauth metadata
    server_metadata_url: str
    client_id: str
    client_secret: str
    client_kwargs: dict[str, str] | None

    retrieve_user_info: Callable[[Request, UserInfo], Awaitable[UserT]]

    # route definitions
    route_prefix: str = ""
    login_url: str = "/auth/{name}"
    callback_url: str = "/auth/{name}/callback"
    post_callback_redirect_name: str

    # route metadata
    dependencies: Dependencies | None = None
    security: Sequence[SecurityRequirement] | None = None
    guards: Sequence[Guard] | None = None
    middleware: Sequence[Middleware] | None = None
    opt: Mapping[str, Any] | None = None
    tags: Sequence[str] | None = None


class AuthCallbackResponse(TypedDict):
    token: str


class OAuthPlugin[UserT: BaseUser = BaseUser](InitPlugin):
    def __init__(self, config: Mapping[str, OAuthConfig[UserT]]) -> None:
        self.config = config
        self.oauth = OAuth()

    @override
    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.on_startup.append(self.app_on_start)
        for name, config in self.config.items():
            client = self.oauth.register(
                name,
                server_metadata_url=config.server_metadata_url,
                client_id=config.client_id,
                client_secret=config.client_secret,
                client_kwargs=config.client_kwargs,
            )

            router = self.create_router(client, name, config)

            app_config.route_handlers.append(router)

        return app_config

    def app_on_start(self, app: Litestar) -> None:
        if not self.config:
            app.get_logger().warning(
                "[OAuthPlugin] No login routes have been registered. "
                "This is probably due to a misconfiguration in the application."
            )

    def create_router(
        self,
        client: LitestarOAuth1App | LitestarOAuth2App,
        name: str,
        config: OAuthConfig[UserT],
    ) -> Router:

        @get(
            config.login_url.format(name=name),
            status_code=status_codes.HTTP_302_FOUND,
            name=f"authlib_{name}_login",
            summary=f"Login for {name.title()}",
            description=f"Start the login flow for {name.title()}",
        )
        async def login_handler(request: Request) -> Response:
            redirect_uri = request.url_for(f"authlib_{name}_callback")
            return await client.authorize_redirect(request, redirect_uri)

        @get(
            config.callback_url.format(name=name),
            status_code=status_codes.HTTP_302_FOUND,
            name=f"authlib_{name}_callback",
            summary=f"Login Callback for {name.title()}",
            description=f"""
Called automatically by the {name.title()} OAuth flow.

Response is subject to change.
            """,
        )
        async def login_callback(request: Request) -> Response:
            try:
                userinfo = await client.authorize_access_token(request)
            except OAuthError as e:
                raise PermissionDeniedException(detail=str(e)) from None

            user = await config.retrieve_user_info(request, userinfo)

            jwt: JWTCookieAuth = request.app.state.jwt
            resp = jwt.login(
                str(user.uuid), response_status_code=status_codes.HTTP_302_FOUND
            )
            resp.headers["location"] = request.url_for(
                config.post_callback_redirect_name
            )
            return resp

        return Router(
            config.route_prefix,
            route_handlers=[
                login_handler,
                login_callback,
            ],
            dependencies=config.dependencies,
            security=config.security,
            guards=config.guards,
            middleware=config.middleware,
            opt=config.opt,
            tags=config.tags,
        )
