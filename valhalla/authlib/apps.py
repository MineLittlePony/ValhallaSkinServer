from typing import TYPE_CHECKING, Any, Self

from authlib.integrations.base_client import BaseApp, OAuthError
from authlib.integrations.base_client.async_app import (
    AsyncOAuth1Mixin,
    AsyncOAuth2Mixin,
)
from authlib.integrations.base_client.async_openid import AsyncOpenIDMixin
from authlib.integrations.httpx_client import AsyncOAuth1Client, AsyncOAuth2Client
from authlib.oauth2.claims import BaseClaims
from authlib.oidc.core import UserInfo
from litestar import Request
from litestar.datastructures import URL
from litestar.response import Redirect as RedirectResponse

if TYPE_CHECKING:
    from .integration import LitestarIntegration


type AsyncOAuthMixin = AsyncOAuth1Mixin | AsyncOAuth2Mixin


class LitestarAppMixin:
    framework: LitestarIntegration

    async def save_authorize_data(
        self,
        request: Request,
        state: str | None = None,
        **kwargs: object,
    ) -> None:
        if state:
            await self.framework.set_state_data(request.session, state, kwargs)
        else:
            raise RuntimeError("Missing state value")

    async def authorize_redirect(
        self: Self & AsyncOAuthMixin,
        request: Request,
        redirect_uri: str | URL | None = None,
        **kwargs: object,
    ) -> RedirectResponse:
        if redirect_uri and isinstance(redirect_uri, URL):
            redirect_uri = str(redirect_uri)
        rv = await self.create_authorization_url(redirect_uri, **kwargs)
        await self.save_authorize_data(request, redirect_uri=redirect_uri, **rv)
        return RedirectResponse(rv["url"], status_code=302)


class LitestarOAuth1App(LitestarAppMixin, AsyncOAuth1Mixin, BaseApp):
    client_cls = AsyncOAuth1Client

    async def authorize_access_token(
        self, request: Request, **kwargs: object
    ) -> UserInfo:
        params = dict(request.query_params)
        state = params.get("oauth_token")
        if not state:
            raise OAuthError(description='Missing "oauth_token" parameter')

        data = await self.framework.get_state_data(request.session, state)
        if not data:
            raise OAuthError(description='Missing "request_token" in temporary data')

        params["request_token"] = data["request_token"]
        params.update(kwargs)
        await self.framework.clear_state_data(request.session, state)
        return await self.fetch_access_token(**params)


class LitestarOAuth2App(LitestarAppMixin, AsyncOAuth2Mixin, AsyncOpenIDMixin, BaseApp):
    client_cls = AsyncOAuth2Client

    async def logout_redirect(
        self,
        request: Request,
        post_logout_redirect_uri: str | None = None,
        id_token_hint: str | None = None,
        **kwargs: object,
    ) -> RedirectResponse:
        if post_logout_redirect_uri and isinstance(post_logout_redirect_uri, URL):
            post_logout_redirect_uri = str(post_logout_redirect_uri)
        result = await self.create_logout_url(
            post_logout_redirect_uri=post_logout_redirect_uri,
            id_token_hint=id_token_hint,
            **kwargs,
        )
        if result.get("state"):
            await self.framework.set_state_data(
                request.session,
                result["state"],
                {
                    "post_logout_redirect_uri": post_logout_redirect_uri,
                },
            )
        return RedirectResponse(result["url"], status_code=302)

    async def validate_logout_response(self, request: Request) -> dict[str, Any]:
        state = request.query_params.get("state")
        if not state:
            raise OAuthError(description='Missing "state" parameter')

        state_data = await self.framework.get_state_data(request.session, state)
        if not state_data:
            raise OAuthError(description='Invalid "state" parameter')

        await self.framework.clear_state_data(request.session, state)
        return state_data

    async def authorize_access_token(
        self,
        request: Request,
        claims_options: dict[str, str] | None = None,
        claims_cls: type[BaseClaims] | None = None,
        leeway: int = 120,
        **kwargs: object,
    ) -> UserInfo:
        if request.scope.get("method", "GET") == "GET":
            error = request.query_params.get("error")
            if error:
                description = request.query_params.get("error_description")
                raise OAuthError(error=error, description=description)

            params = {
                "code": request.query_params.get("code"),
                "state": request.query_params.get("state"),
            }
        else:
            form = await request.form()
            params = {
                "code": form.get("code"),
                "state": form.get("state"),
            }

        state_data = await self.framework.get_state_data(
            request.session, params.get("state")
        )
        await self.framework.clear_state_data(request.session, params.get("state"))
        params = self._format_state_params(state_data, params)

        token = await self.fetch_access_token(**params, **kwargs)

        if state_data is not None and "id_token" in token and "nonce" in state_data:
            userinfo = await self.parse_id_token(
                token,
                nonce=state_data["nonce"],
                claims_options=claims_options,
                claims_cls=claims_cls,
                leeway=leeway,
            )
            token["userinfo"] = userinfo
        return token
