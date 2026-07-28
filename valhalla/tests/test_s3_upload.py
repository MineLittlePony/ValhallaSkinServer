import os
from collections.abc import Generator

import boto3
import pytest
from moto import mock_aws

from valhalla.config import Settings
from valhalla.files import get_target_path
from valhalla.s3path import S3Path


@pytest.fixture(scope="function")
def aws_credentials() -> None:
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture(scope="function")
def aws(aws_credentials: None) -> Generator[None]:
    with mock_aws():
        s3_client = boto3.client("s3")
        s3_client.create_bucket(Bucket="test")
        yield


def test_filesystem(aws: None) -> None:
    fs = get_target_path(
        Settings(
            textures_bucket="test",
            textures_path="path",
            s3_bucket_content_type="text/txt",
        )
    )
    file = fs / "file.txt"
    assert not file.exists()

    file.write_bytes(b"hello, world")

    assert file.is_file()

    assert file.read_bytes() == b"hello, world"


def test_symlink_creation(aws: None) -> None:
    s = S3Path("s3://test/bar/baz")
    s.write_text("zzz")

    assert s.readlink() is s

    s2 = S3Path("s3://test/foo")

    with pytest.raises(NotImplementedError):
        s2.symlink_to(s, target_is_directory=True)

    s2.symlink_to(s)

    assert s2.info.is_symlink() is True

    assert s2.readlink() == s


def test_mkdir(aws: None) -> None:
    s = S3Path("s3://test/bar")
    s.mkdir()  # creates an empty file
    assert s.exists() is True


def test_iterdir(aws: None) -> None:
    s = S3Path("s3://test")
    (s1 := s.joinpath("foo")).write_text("")
    (s2 := s.joinpath("bar")).write_text("")
    (s3 := s.joinpath("baz")).write_text("")

    assert list(s.iterdir()) == [s1, s2, s3]


def test_is_dir(aws: None) -> None:
    s = S3Path("s3://test/bar")
    assert s.info.is_dir() is False
