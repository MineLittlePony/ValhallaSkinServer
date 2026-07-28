import posixpath
from collections.abc import Callable, Iterable, Mapping
from io import BytesIO
from typing import TYPE_CHECKING, Any, Literal, Self, override

import boto3
import botocore.exceptions
from botocore.response import StreamingBody
from pathlib_abc import PathInfo, ReadablePath, WritablePath

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client
    from mypy_boto3_s3.type_defs import HeadObjectOutputTypeDef


class S3PathInfo(PathInfo):
    __slots__ = ("pathobj",)

    def __init__(self, path: S3Path) -> None:
        self.pathobj = path

    def stat(self) -> HeadObjectOutputTypeDef | None:
        try:
            return self.pathobj.client.head_object(
                Bucket=self.pathobj.bucket,
                Key=self.pathobj.key,
            )
        except botocore.exceptions.ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return None
            raise  # pragma: no cover

    @override
    def exists(self, *, follow_symlinks: bool = True) -> bool:
        return self.stat() is not None

    @override
    def is_dir(self, *, follow_symlinks: bool = True) -> bool:
        # s3 has no directories
        return False

    @override
    def is_file(self, *, follow_symlinks: bool = True) -> bool:
        return self.exists()

    def is_symlink(self, *, follow_symlinks: bool = True) -> bool:
        s = self.stat()
        return s is not None and "WebsiteRedirectLocation" in s


class S3Path(WritablePath, ReadablePath):
    __slots__ = (
        "_bucket",
        "_client",
        "_info",
        "_key",
        "_paths",
        "_upload_args",
    )
    parser = posixpath

    def __init__(
        self,
        *segments: S3Path | str,
        upload_args: Mapping[str, Any] | Iterable[tuple[str, Any]] = (),
    ) -> None:
        paths: list[str] = []

        bucket = None
        for path in segments:
            if isinstance(path, S3Path):
                if bucket is None:
                    bucket = path.bucket
                elif bucket != path.bucket:
                    raise ValueError(
                        "all s3 path components did not share a bucket name. "
                        f"{bucket!r} != {path.bucket!r}"
                    )
                paths.extend(path._paths)  # noqa: SLF001
            else:
                if path.startswith("s3://"):
                    bucket_, *path = path[5:].split("/", maxsplit=1)
                    if bucket is None:
                        bucket = bucket_
                    elif bucket != bucket_:
                        raise ValueError(
                            "all s3 path components did not share a bucket name. "
                            f"{bucket!r} != {bucket_!r}"
                        )
                    if path:
                        paths.append(path[0])
                elif path.startswith("arn:aws:s3:::"):
                    bucket_, *path = path[13:].split("/", maxsplit=1)
                    if bucket is None:
                        bucket = bucket_
                    elif bucket != bucket_:
                        raise ValueError(
                            "all s3 path components did not share a bucket name. "
                            f"{bucket!r} != {bucket_!r}"
                        )

                    if path:
                        paths.append(path[0])
                elif bucket is None:
                    bucket, *path = path.split("/", maxsplit=1)

                    if path:
                        paths.append(path[0])
                else:
                    paths.append(path)

        if bucket is None:
            raise ValueError("missing bucket") from None

        self._bucket = bucket
        self._paths = paths
        self._upload_args = dict(upload_args)

    @property
    def client(self) -> S3Client:
        try:
            return self._client
        except AttributeError:
            self._client = boto3.client("s3")
            return self._client

    @property
    def bucket(self) -> str:
        return self._bucket

    @property
    def key(self) -> str:
        try:
            return self._key
        except AttributeError:
            self._key = "/".join(self._paths)
            return self._key

    @property
    def upload_args(self) -> dict[str, Any]:
        return self._upload_args

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"

    @property
    def arn(self) -> str:
        return f"arn:aws:s3:::{self.bucket}/{self.key}"

    def exists(self) -> bool:
        return self.info.exists()

    def is_file(self) -> bool:
        return self.info.is_file()

    @override
    def __vfspath__(self) -> str:
        return str(self)

    @override
    def with_segments(self, *pathsegments: S3Path | str) -> Self:
        return type(self)(*pathsegments, upload_args=self.upload_args)

    @property
    @override
    def info(self) -> S3PathInfo:
        try:
            return self._info
        except AttributeError:
            self._info = S3PathInfo(self)
            return self._info

    @override
    def iterdir(self) -> Iterable[Self]:
        paginator = self.client.get_paginator("list_objects_v2")
        return (
            type(self)(self.bucket, obj["Key"], upload_args=self.upload_args)
            for page in paginator.paginate(Bucket=self.bucket, Prefix=self.key)
            if "Contents" in page
            for obj in page["Contents"]
            if "Key" in obj
        )

    @override
    def readlink(self) -> Self:
        s = self.info.stat()
        if s is None or "WebsiteRedirectLocation" not in s:
            return self
        return type(self)(self.bucket, s["WebsiteRedirectLocation"])

    @override
    def symlink_to(
        self, target: S3Path | str, target_is_directory: bool = False
    ) -> None:
        if target_is_directory:
            raise NotImplementedError
        self.client.put_object(
            Bucket=self.bucket,
            Key=self.key,
            WebsiteRedirectLocation=str(target),
        )

    @override
    def mkdir(self) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=self.key,
        )

    @override
    def __open_reader__(self) -> StreamingBody:
        resp = self.client.get_object(
            Bucket=self.bucket,
            Key=self.key,
        )
        return resp["Body"]

    @override
    def __open_writer__(self, mode: Literal["w", "a", "x"]) -> BytesIO:
        def callback(content: BytesIO) -> None:
            self.client.put_object(
                Bucket=self.bucket,
                Key=self.key,
                Body=content.getvalue(),
                **self.upload_args,
            )

        return FileWriter(callback)

    @override
    def __str__(self) -> str:
        return self.uri

    @override
    def __repr__(self) -> str:
        return f"S3Path({self.uri!r})"

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, S3Path)
            and self.bucket == other.bucket
            and self.key == self.key
        )

    if TYPE_CHECKING:

        def __truediv__(self, key: Self | str) -> Self: ...


class FileWriter(BytesIO):
    def __init__(self, close_callback: Callable[[BytesIO], None]) -> None:
        super().__init__()
        self.callback = close_callback

    def close(self) -> None:
        if self.closed:  # pragma: no cover
            raise ValueError("stream was already closed")
        self.callback(self)
