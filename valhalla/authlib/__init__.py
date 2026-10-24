"""Authlib integration for Litestar.

Mostly copied from authlib.integrations.starlette_client
"""

from authlib.integrations.base_client import BaseOAuth, OAuthError

from .apps import LitestarOAuth1App, LitestarOAuth2App
from .integration import LitestarIntegration


class OAuth(BaseOAuth):
    oauth1_client_cls = LitestarOAuth1App
    oauth2_client_cls = LitestarOAuth2App
    framework_integration_cls = LitestarIntegration


__all__ = [
    "OAuth",
    "OAuthError",
    "StarletteIntegration",
    "StarletteOAuth1App",
    "StarletteOAuth2App",
]
