from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from freezegun import freeze_time
from litestar import Litestar, Request
from litestar.exceptions import NotAuthorizedException
from litestar.security.jwt import JWTAuth

from valhalla.auth import token_from_user
from valhalla.models import User


@pytest.mark.parametrize(
    "ff_time",
    [
        pytest.param(timedelta(hours=2), id="verify_exp"),
        pytest.param(timedelta(hours=-2), id="verify_iss"),
    ],
)
def test_auth_verify(app: Litestar, ff_time: timedelta) -> None:
    state: Any = {"litestar_app": app}
    request = Request(state)
    user = User(uuid=uuid4(), name="Name")
    with freeze_time("2026-10-05") as ft:
        tkn = token_from_user(request, user)

        ft.tick(ff_time)

        jwt: JWTAuth = app.state.jwt
        with pytest.raises(NotAuthorizedException, match=r"^401: Invalid token$"):
            jwt.token_cls.decode(tkn, jwt.token_secret, jwt.algorithm)
