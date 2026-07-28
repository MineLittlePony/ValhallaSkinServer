from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import boto3
from fastapi import Depends

from .config import Settings, get_settings
from .s3path import S3Path


def get_target_path(
    config: Annotated[Settings, Depends(get_settings)],
) -> Path | S3Path:
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


@dataclass
class Files:
    save_path: Annotated[Path | S3Path, Depends(get_target_path)]

    def put_file(self, skin_hash: str, data: bytes) -> None:
        """Save a texture to the file system"""

        file = self.save_path / skin_hash
        if not file.exists():
            file.write_bytes(data)


def verify_aws_credentials() -> None:
    sts_client = boto3.client("sts")
    sts_client.get_caller_identity()
