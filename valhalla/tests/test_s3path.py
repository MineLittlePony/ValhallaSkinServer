import re

import pytest

from valhalla.s3path import S3Path


def test_s3_path() -> None:
    path = S3Path("bucketname", "path/to", "file.txt")

    assert str(path) == "s3://bucketname/path/to/file.txt"


def test_s3_path_repr() -> None:
    path = S3Path("foobar", "zzzz/ddd/bbb")

    assert repr(path) == "S3Path('s3://foobar/zzzz/ddd/bbb')"
    assert path.uri == "s3://foobar/zzzz/ddd/bbb"
    assert path.arn == "arn:aws:s3:::foobar/zzzz/ddd/bbb"


def test_s3_path_init() -> None:
    assert str(S3Path("bucket")) == "s3://bucket/"

    assert str(S3Path("s3://bucket/file")) == "s3://bucket/file"
    assert str(S3Path("arn:aws:s3:::bucket/file")) == "s3://bucket/file"
    assert str(S3Path("s3://bucket")) == "s3://bucket/"
    assert str(S3Path("arn:aws:s3:::bucket")) == "s3://bucket/"

    assert (
        str(S3Path(S3Path("bucket"), "asdf", S3Path("bucket/barrrf")))
        == "s3://bucket/asdf/barrrf"
    )
    assert (
        str(S3Path(S3Path("bucket"), "s3://bucket/asdf", "arn:aws:s3:::bucket/barrrf"))
        == "s3://bucket/asdf/barrrf"
    )

    for bucket2 in (
        S3Path("bucket2/asdf"),
        "s3://bucket2/asdf",
        "arn:aws:s3:::bucket2/asdf",
    ):
        with pytest.raises(
            ValueError,
            match=re.escape(
                "all s3 path components did not share a bucket name. "
                "'bucket' != 'bucket2'"
            ),
        ):
            S3Path("bucket", bucket2)

    with pytest.raises(ValueError, match=re.escape("missing bucket")):
        S3Path()
