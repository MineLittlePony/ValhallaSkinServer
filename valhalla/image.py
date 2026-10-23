import hashlib
from io import BytesIO

from litestar.exceptions import ClientException
from PIL import Image, UnidentifiedImageError


def gen_skin_hash(image_data: bytes) -> str:
    try:
        image = Image.open(BytesIO(image_data))
    except UnidentifiedImageError as e:
        raise ClientException(detail=str(e)) from None

    if image.format != "PNG":
        raise ClientException(detail="Unsupported image format")

    # Check size of image.
    # width should be same as or double the height
    # Width is then checked for predefined values
    # 64, 128, 256, 512, 1024

    # set of supported width sizes. Height is either same or half
    sizes = {64, 128, 256, 512, 1024}
    width, height = image.size
    valid = width / 2 == height or width == height

    if not valid or width not in sizes:
        raise ClientException(detail="Unsupported image size")

    # Create a hash of the image and use it as the filename.
    return hashlib.sha1(image.tobytes(), usedforsecurity=False).hexdigest()
