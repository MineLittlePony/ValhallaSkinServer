import datetime
import enum
from collections.abc import Awaitable, Callable
from typing import Any, overload
from uuid import UUID

import httpx2
from pydantic import AnyHttpUrl, BaseModel

XBOX_AUTH_BASE = "https://{0}.auth.xboxlive.com/{0}/{1}"
XBOX_USER_AUTH = XBOX_AUTH_BASE.format("user", "authenticate")
XBOX_XSTS_AUTH = XBOX_AUTH_BASE.format("xsts", "authorize")

MC_BASE = "https://api.minecraftservices.com/{0}"
MC_AUTH_XBOX = MC_BASE.format("authentication/login_with_xbox")
MC_PROFILE = MC_BASE.format("minecraft/profile")


class XError(enum.IntEnum):
    NO_ACCOUNT = 2148916233
    REGION = 2148916235
    CHILD = 2148916238


x_default_error_message = "Unknown error while authenticating with xbox live"
x_error_messages = {
    XError.NO_ACCOUNT: "This account is not associated with a Xbox Live account.",
    XError.REGION: "This account is in a region where Xbox Live is not available.",
    XError.CHILD: "This account is a child and must be added to a Family.",
}


class XSTSError(BaseModel):
    Identity: str
    XErr: XError
    Message: str
    Redirect: str


def get_x_error_message(err: XSTSError) -> str:
    return x_error_messages.get(err.XErr, x_default_error_message)


class XboxLoginError(Exception):
    def __init__(self, err: XSTSError):
        super().__init__(get_x_error_message(err))
        self.err = err


class TextureState(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class SkinVariant(enum.Enum):
    CLASSIC = "CLASSIC"
    SLIM = "SLIM"


class Texture(BaseModel):
    id: UUID
    state: TextureState
    url: AnyHttpUrl


class Skin(Texture):
    variant: SkinVariant


class Cape(Texture):
    alias: str


class MinecraftProfile(BaseModel):
    id: UUID
    name: str
    skins: list[Skin]
    capes: list[Cape]


class MinecraftAuth(BaseModel):
    username: str
    roles: list[Any]
    access_token: str
    token_type: str
    expires_in: int


class XboxAuth(BaseModel):
    IssueInstant: datetime.datetime
    NotAfter: datetime.datetime
    Token: str
    DisplayClaims: dict[str, list[dict[str, str]]]


async def login_with_xbox(xbl_access_token: str) -> MinecraftProfile:
    async with httpx2.AsyncClient() as client:

        async def auth_xbl(access_token: str) -> XboxAuth:
            response = await client.post(
                XBOX_USER_AUTH,
                json={
                    "Properties": {
                        "AuthMethod": "RPS",
                        "SiteName": "user.auth.xboxlive.com",
                        "RpsTicket": f"d={access_token}",
                    },
                    "RelyingParty": "http://auth.xboxlive.com",
                    "TokenType": "JWT",
                },
            )

            return XboxAuth.model_validate(response.json())

        async def auth_xsts(xbox_auth: XboxAuth) -> XboxAuth:
            response = await client.post(
                XBOX_XSTS_AUTH,
                json={
                    "Properties": {
                        "SandboxId": "RETAIL",
                        "UserTokens": [xbox_auth.Token],
                    },
                    "RelyingParty": "rp://api.minecraftservices.com/",
                    "TokenType": "JWT",
                },
            )
            if response.is_client_error:
                raise XboxLoginError(XSTSError.model_validate(response.json()))

            return XboxAuth.model_validate(response.json())

        async def auth_minecraft_from_xbox(xbox_auth: XboxAuth) -> MinecraftAuth:
            userhash = xbox_auth.DisplayClaims["xui"][0]["uhs"]
            xsts_token = xbox_auth.Token
            response = await client.post(
                MC_AUTH_XBOX,
                json={"identityToken": f"XBL3.0 x={userhash};{xsts_token}"},
            )
            return MinecraftAuth.model_validate(response.json())

        async def get_minecraft_profile(mc_auth: MinecraftAuth) -> MinecraftProfile:
            response = await client.get(
                MC_PROFILE,
                headers={"Authorization": f"Bearer {mc_auth.access_token}"},
            )
            return MinecraftProfile.model_validate(response.json())

        async def login(xbl_access_token: str) -> MinecraftProfile:
            """Start the lengthy authorization process."""
            return await compose(
                xbl_access_token,
                auth_xbl,
                auth_xsts,
                auth_minecraft_from_xbox,
                get_minecraft_profile,
            )

        return await login(xbl_access_token)


@overload
async def compose[T1, T2](
    payload: T1,
    func1: Callable[[T1], Awaitable[T2]],
    /,
) -> T2: ...


@overload
async def compose[T1, T2, T3](
    payload: T1,
    func1: Callable[[T1], Awaitable[T2]],
    func2: Callable[[T2], Awaitable[T3]],
    /,
) -> T3: ...


@overload
async def compose[T1, T2, T3, T4](
    payload: T1,
    func1: Callable[[T1], Awaitable[T2]],
    func2: Callable[[T2], Awaitable[T3]],
    func3: Callable[[T3], Awaitable[T4]],
    /,
) -> T4: ...


@overload
async def compose[T1, T2, T3, T4, T5](
    payload: T1,
    func1: Callable[[T1], Awaitable[T2]],
    func2: Callable[[T2], Awaitable[T3]],
    func3: Callable[[T3], Awaitable[T4]],
    func4: Callable[[T4], Awaitable[T5]],
    /,
) -> T5: ...


async def compose(payload: Any, *funcs: Callable[[Any], Awaitable[Any]]) -> Any:
    for func in funcs:
        payload = await func(payload)
    return payload
