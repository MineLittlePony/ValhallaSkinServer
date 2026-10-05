import hashlib
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from fastapi.security import OAuth2
from joserfc import jwk, jwt
from joserfc.errors import JoseError
from starlette import status

from .config import Settings

auth_scheme = OAuth2(auto_error=False)


async def current_user_id(
    header: Annotated[str | None, Depends(auth_scheme)],
    cookie: Annotated[str | None, Cookie(alias="token")] = None,
) -> int | None:
    if header and header.startswith("Bearer "):
        header = header[7:]
    token = header or cookie
    if token is None:
        return None

    try:
        return user_from_token(token)
    except JoseError:
        return None


def require_user_id(
    user_id: Annotated[int | None, Depends(current_user_id)],
) -> int:
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED)
    return user_id


jose_key: jwk.OctKey
claims_validator = jwt.JWTClaimsRegistry()


def init_jwk(settings: Settings) -> None:
    global jose_key
    jose_key = jwk.import_key(
        hashlib.sha256(settings.secret_key.encode()).digest(), key_type="oct"
    )


def token_from_user(
    user_id: int,
    *,
    expire_in: timedelta,
    issued_at: datetime | None = None,
) -> str:
    if issued_at is None:
        issued_at = datetime.now(UTC)
    header = {"alg": "HS256"}
    claims = {
        "sid": user_id,
        "iat": issued_at,
        "exp": issued_at + expire_in,
    }
    return jwt.encode(header, claims, key=jose_key)


def user_from_token(token: str, *, validate: bool = True) -> int | None:
    entity = jwt.decode(token, key=jose_key, algorithms=["HS256"])
    if validate:
        claims_validator.validate(entity.claims)
    return entity.claims["sid"]
