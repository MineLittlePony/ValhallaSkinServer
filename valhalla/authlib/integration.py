import json
import time
from collections.abc import Hashable
from typing import TYPE_CHECKING, Any, override

from authlib.integrations.base_client import FrameworkIntegration

if TYPE_CHECKING:
    from valhalla.authlib import OAuth


class LitestarIntegration(FrameworkIntegration):
    expires_in = 3600

    async def _get_cache_data(self, key: Hashable) -> dict[str, Any] | None:
        if self.cache is None:
            return None
        value = await self.cache.get(key)
        if not value:
            return None
        try:
            return json.loads(value)
        except TypeError, ValueError:
            return None

    async def get_state_data(
        self, session: dict[str, Any] | None, state: str | None
    ) -> dict[str, Any] | None:
        key = f"_state_{self.name}_{state}"
        if self.cache:
            # require a session-bound marker to prove the callback originates
            # from the user-agent that started the flow (RFC 6749 §10.12)
            if session is None or session.get(key) is None:
                return None
            value = await self._get_cache_data(key)
        elif session is not None:
            value = session.get(key)
        else:
            value = None

        if value:
            return value.get("data")
        return None

    async def set_state_data(
        self,
        session: dict[str, dict[str, object]] | None,
        state: str,
        data: object,
    ) -> None:
        key_prefix = f"_state_{self.name}_"
        key = f"{key_prefix}{state}"
        now = time.time()
        if session is not None:
            # clear old state data to avoid session size growing
            for old_key in list(session.keys()):
                if old_key.startswith(key_prefix):
                    session.pop(old_key)
            session[key] = {"data": data, "exp": now + self.expires_in}

    def _clear_session_state(self, session: dict[str, Any]) -> None:
        now = time.time()
        prefix = f"_state_{self.name}"
        for key in dict(session):
            if key.startswith(prefix):
                value = session[key]
                exp = value.get("exp")
                if not exp or exp < now:
                    session.pop(key)

    async def clear_state_data(
        self, session: dict[str, Any] | None, state: str | None
    ) -> None:
        key = f"_state_{self.name}_{state}"
        if session is not None:
            session.pop(key, None)
            self._clear_session_state(session)

    def update_token(
        self,
        token: str,
        refresh_token: str | None = None,
        access_token: str | None = None,
    ) -> None:
        pass

    @staticmethod
    @override
    def load_config(oauth: OAuth, name: str, params: list[str]) -> dict[str, Any]:
        return {}
