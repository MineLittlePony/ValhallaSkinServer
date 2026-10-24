from pathlib import Path

from valhalla.config import Settings

from .s3path import S3Path


def get_save_path(config: Settings) -> Path | S3Path:
    bucket = config.textures_bucket
    if bucket is None:
        # bucket not set, use local files for storage
        path = Path(config.textures_path)
        path.mkdir(parents=True, exist_ok=True)
        return Path(path)

    return S3Path(
        bucket,
        config.textures_path,
        upload_args={
            "ContentType": config.s3_bucket_content_type,
        },
    )


def put_file(save_path: Path | S3Path, skin_hash: str, data: bytes) -> None:
    """Save a texture to the file system"""
    file = save_path / skin_hash
    if not file.exists():
        file.write_bytes(data)
