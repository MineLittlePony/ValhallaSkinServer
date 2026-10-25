from typing import override

from litestar import status_codes
from litestar.datastructures import URL
from litestar.enums import ScopeType
from litestar.middleware import ASGIMiddleware
from litestar.response.redirect import ASGIRedirectResponse
from litestar.types import ASGIApp, Receive, Scope, Send


class HttpsRedirectMiddleware(ASGIMiddleware):
    """Redirects http to https

    Excludes requests that come from localhost.
    """

    scopes = (ScopeType.HTTP, ScopeType.WEBSOCKET)

    @override
    async def handle(
        self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp
    ) -> None:
        if scope["scheme"] in ("http", "ws") and self.should_redirect(
            url := URL.from_scope(scope)
        ):
            new_url = url.with_replacements(scheme=url.scheme + "s")
            await ASGIRedirectResponse(
                path=str(new_url),
                status_code=status_codes.HTTP_307_TEMPORARY_REDIRECT,
            )(scope, receive, send)
            return

        await next_app(scope, receive, send)

    def should_redirect(self, url: URL) -> bool:
        host = url.hostname
        return url.port is None and (
            host is not None
            and host not in ("localhost", "127.0.0.1", "::1")
            and not host.endswith((".localhost", ".local"))
        )
