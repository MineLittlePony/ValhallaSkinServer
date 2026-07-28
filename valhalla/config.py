import secrets
from enum import Enum
from urllib.parse import urlparse

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

async_sql_drivers = {
    "sqlite": "sqlite+aiosqlite",
    "postgres": "postgresql+psycopg",
}


def resolve_db(url: str) -> str:
    url_parts = urlparse(url)
    if url_parts.scheme in async_sql_drivers:
        url_parts = url_parts._replace(scheme=async_sql_drivers[url_parts.scheme])
    url = url_parts.geturl()
    if not url_parts.netloc:
        url = url.replace(":/", ":///")
    return url


class Env(Enum):
    PRODUCTION = "prod"
    DEVELOPING = "dev"
    TESTING = "test"

    @property
    def isprod(self) -> bool:
        return self is Env.PRODUCTION


def generate_server_id() -> str:
    s = secrets.token_urlsafe(20)
    s = s.replace("_", "")
    return s.replace("-", "")


class Settings(BaseSettings):
    env: Env = Env.PRODUCTION
    debug: bool = False

    texture_type_denylist: frozenset[str] = frozenset({"cape"})

    secret_key: str = "dev"
    database_url: str = "sqlite:///./valhalla.db"

    # TODO this should be saved in the database
    server_id: str = Field(default_factory=generate_server_id)

    textures_bucket: str | None = None
    textures_path: str = "textures"
    textures_url: AnyHttpUrl | None = None
    s3_bucket_content_type: str = "image/png"

    xbox_live_client_id: str | None = None
    xbox_live_client_secret: str | None = None

    xbox_live_server_metadata_url: str = (
        "https://login.live.com/.well-known/openid-configuration"
    )
    xbox_live_client_kwargs: dict[str, str] = {
        "scope": "XboxLive.signin offline_access"
    }

    aws_endpoint_url: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    verify_aws_credentials: bool = True

    def get_database_url(self) -> str:
        return resolve_db(self.database_url)

    def get_textures_url(self) -> str | None:
        if self.textures_url is None:
            return None
        url = str(self.textures_url)
        if url and not url.endswith("/"):
            url += "/"
        return url

    model_config = SettingsConfigDict(
        env_file=".env",
    )


def get_settings() -> Settings:
    return Settings()


settings = Settings()
