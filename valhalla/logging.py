from collections.abc import Iterable
from logging import Filter, LogRecord, getLogger
from typing import override


class StatusCodeFilter(Filter):
    def __init__(self, codes: Iterable[int]) -> None:
        self.codes = frozenset(codes)

    @override
    def filter(self, record: LogRecord) -> bool:
        match record:
            case LogRecord(
                msg='%s - "%s %s HTTP/%s" %d',
                args=(_, _, _, _, int() as status_code),
            ):
                return status_code not in self.codes
            case _:
                return True


def init_logger() -> None:
    uvicorn_access = getLogger("uvicorn.access")
    uvicorn_access.addFilter(StatusCodeFilter(codes=[429]))
