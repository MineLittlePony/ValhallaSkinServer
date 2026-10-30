from pathlib import Path, PurePath

from litestar import Router, get, head
from litestar.file_system import BaseLocalFileSystem
from litestar.params import FromPath
from litestar.response.file import ASGIFileResponse
from litestar.static_files import StaticFiles


def create_frontend_router(directory: Path) -> Router:
    """
    Similar to `litestar.create_static_file_router`, but prepends `"assets"` to all
    paths except for the index.
    """
    static_files = StaticFiles(
        is_html_mode=True,
        directories=[directory],
        file_system=BaseLocalFileSystem(),
    )

    @get("/assets/{file_path:path}", name="assets")
    async def get_handler(file_path: FromPath[PurePath]) -> ASGIFileResponse:
        return await static_files.handle(
            path=("assets" / file_path.relative_to("/")).as_posix(),
            is_head_response=False,
        )

    @head("/assets/{file_path:path}", name="assets/head")
    async def head_handler(file_path: FromPath[PurePath]) -> ASGIFileResponse:
        return await static_files.handle(
            path=("assets" / file_path.relative_to("/")).as_posix(),
            is_head_response=True,
        )

    @get("/", name="index")
    async def index_handler() -> ASGIFileResponse:
        return await static_files.handle(path="index.html", is_head_response=False)

    return Router(
        "",
        route_handlers=[
            get_handler,
            head_handler,
            index_handler,
        ],
        include_in_schema=False,
    )
