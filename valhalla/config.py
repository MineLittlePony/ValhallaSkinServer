import secrets
from typing import Literal
from urllib.parse import urlparse

from pydantic import AnyHttpUrl, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

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


def generate_server_id() -> str:
    s = secrets.token_urlsafe(20)
    s = s.replace("_", "")
    return s.replace("-", "")


class Settings(BaseSettings):
    online_mode: bool = Field(
        default=True,
        description="""
Disable this setting to remove the requirement for users to sign into Minecraft before
uploading their skins.

It is similar to the online-mode setting in the Minecraft server.properties file.

WARNING:
    This setting is intended for development purposes. Setting it to false in production
    is not supported or recommended.
        """,
    )
    texture_type_denylist: frozenset[Literal["skin", "cape", "elytra"]] = Field(
        default=frozenset({"cape"}),
        description="List of textures which will be denied upload.",
    )

    secret_key: str = Field(
        default="dev",
        description="""
The secret key used to sign the session data.

It's important to change this from the default. Use the following command to create a
new secret key.

$ openssl rand -base64 24
        """,
    )
    database_url: str = Field(
        default="sqlite:///./valhalla.db",
        description="The url to the database. Supports sqlite and postgresql.",
        examples=["postgresql://user:pass@host:5432/dbname"],
    )
    redis_url: str | None = Field(
        default=None,
        description="URL pointing to a redis instance for the rate limiter",
        examples=["redis://<host>:<port>/n"],
    )

    # TODO this should be saved in the database
    server_id: str = Field(default_factory=generate_server_id, exclude=True)

    textures_bucket: str | None = Field(
        default=None,
        description="""
The S3 bucket to store uploaded textures in.
        """,
    )
    textures_path: str = Field(
        default="textures",
        description="""
The base path to where uploaded textures are stored.

For S3, it behaves as a key prefix
        """,
    )
    textures_url: AnyHttpUrl | None = Field(
        default=None,
        description="""
The url to where the textures will be accessed on the client.

For s3, will be https://{bucket-name}.s3.amazonaws.com/ or your configured domain alias.

If empty, will assume same origin.
""",
        examples=[
            "https://foobar.s3.amazonaws.com",
        ],
    )

    s3_bucket_content_type: str = Field(default="image/png", exclude=True)

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
    verify_aws_credentials: bool = Field(default=True, exclude=True)

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
        toml_file="config.toml",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
            TomlConfigSettingsSource(settings_cls),
        )


def get_settings() -> Settings:
    return Settings()


settings = Settings()
