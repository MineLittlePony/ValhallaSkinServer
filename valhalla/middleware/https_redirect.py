from litestar import status_codes
from litestar.datastructures import URL
from litestar.middleware import ASGIMiddleware
from litestar.response.redirect import ASGIRedirectResponse
from litestar.types import ASGIApp, Receive, Scope, Send


class HttpsRedirectMiddleware(ASGIMiddleware):
    """Redirects http to https

    Excludes requests that come from localhost.
    """

    async def handle(
        self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp
    ) -> None:
        if scope["scheme"] in ("http", "ws") and self.is_localhost(scope) is None:
            url = str(
                URL.from_scope(scope).with_replacements(scheme=scope["scheme"] + "s")
            )
            await ASGIRedirectResponse(
                path=url,
                status_code=status_codes.HTTP_308_PERMANENT_REDIRECT,
            )(scope, receive, send)
            return

        await next_app(scope, receive, send)

    def is_localhost(self, scope: Scope) -> int | None:
        host = (scope["server"] or (None, None))[0]
        return host in (None, "127.0.0.1", "::1")
