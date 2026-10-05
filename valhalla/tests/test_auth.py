from datetime import UTC, datetime, timedelta

import pytest
from freezegun import freeze_time
from joserfc.errors import ExpiredTokenError, InvalidClaimError

from valhalla.auth import token_from_user, user_from_token


@pytest.mark.parametrize(
    ("expire_in", "issued_at", "exc_type", "exc_match"),
    [
        pytest.param(
            timedelta(hours=-1),
            None,
            ExpiredTokenError,
            r"^expired_token: The token is expired$",
            id="verify_exp",
        ),
        pytest.param(
            timedelta(hours=1),
            datetime(year=2026, month=10, day=6, tzinfo=UTC),
            InvalidClaimError,
            r"^invalid_claim: The token was issued in the future$",
            id="verify_iss",
        ),
    ],
)
@freeze_time("2026-10-05")
def test_auth_verify(
    expire_in: timedelta,
    issued_at: datetime | None,
    exc_type: type[BaseException],
    exc_match: str,
) -> None:
    token = token_from_user(user_id=1, expire_in=expire_in, issued_at=issued_at)

    with pytest.raises(exc_type, match=exc_match):
        user_from_token(token)
