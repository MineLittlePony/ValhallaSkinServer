from pathlib import Path

import pytest
from fastapi import HTTPException

from .. import image
from .conftest import assets

bad = assets / "bad"
good = assets / "good"


def path_names(path: Path) -> str:
    return path.stem


@pytest.mark.parametrize("path", list(bad.iterdir()), ids=path_names)
def test_invalid_images(path: Path) -> None:
    with pytest.raises(HTTPException):
        image.gen_skin_hash(path.read_bytes())


@pytest.mark.parametrize("path", list(good.glob("*.png")), ids=path_names)
def test_valid_images(path: Path) -> None:
    hash_file = path.with_suffix(".txt")

    image_data = path.read_bytes()

    target_hash = None
    if hash_file.exists():
        target_hash = hash_file.read_text().strip()

    actual_hash = image.gen_skin_hash(image_data)

    assert actual_hash == target_hash
