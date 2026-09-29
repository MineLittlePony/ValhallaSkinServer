from urllib.parse import urljoin

from fastapi import Request

from ...config import Config


def get_textures_url(request: Request, settings: Config) -> str:
    return settings.get_textures_url() or urljoin(str(request.base_url), "textures/")
