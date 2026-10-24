from functools import cache, lru_cache

import valhalla


@lru_cache(maxsize=10)
def github_url(path: str | None = None, *, is_dir: bool = False) -> str:
    repo = _get_repository()

    if path is None:
        return repo

    if is_dir:
        return f"{repo}/tree/main/{path}"

    return f"{repo}/blob/main/{path}"


@cache
def _get_repository() -> str:
    for url in valhalla.__metadata__.get_all("Project-URL", []):
        name, url = str(url).split(", ")
        if name.lower() == "repository":
            return url

    raise AssertionError("Repository was not set in project urls")
