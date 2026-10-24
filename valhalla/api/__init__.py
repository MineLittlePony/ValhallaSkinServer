from litestar import Router

from . import v0, v1

router = Router("/api", route_handlers=[v1.router, v0.router])
