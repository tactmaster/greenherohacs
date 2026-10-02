"""Auth0 token management for Green Hero (device flow + refresh token)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import aiohttp

from .const import (
    AUTH0_AUDIENCE,
    AUTH0_CLIENT_ID,
    AUTH0_DEVICE_CODE_URL,
    AUTH0_SCOPE,
    AUTH0_TOKEN_URL,
)


class AuthError(Exception):
    """Authentication failure."""


@dataclass
class TokenStore:
    """Holds the current access token and refreshes it when stale."""

    refresh_token: str
    client_id: str = AUTH0_CLIENT_ID
    access_token: str | None = None
    expires_at: float = 0.0
    _session: aiohttp.ClientSession | None = field(default=None, repr=False)

    def set_session(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def async_get_token(self) -> str:
        """Return a valid access token, refreshing if needed (60s skew)."""
        if self.access_token and time.time() < self.expires_at - 60:
            return self.access_token
        return await self._async_refresh()

    async def _async_refresh(self) -> str:
        assert self._session is not None
        async with self._session.post(
            AUTH0_TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "refresh_token": self.refresh_token,
            },
        ) as resp:
            body = await resp.json()
            if resp.status != 200:
                raise AuthError(f"token refresh failed: {resp.status} {body}")
        self.access_token = body["access_token"]
        self.expires_at = time.time() + int(body.get("expires_in", 86400))
        # Auth0 refresh-token rotation: store the new refresh token if returned.
        if "refresh_token" in body:
            self.refresh_token = body["refresh_token"]
        return self.access_token


async def async_request_device_code(session: aiohttp.ClientSession) -> dict:
    """Start the device authorization flow."""
    data = {"client_id": AUTH0_CLIENT_ID, "scope": AUTH0_SCOPE}
    if AUTH0_AUDIENCE:
        data["audience"] = AUTH0_AUDIENCE
    async with session.post(AUTH0_DEVICE_CODE_URL, data=data) as resp:
        body = await resp.json()
        if resp.status != 200:
            raise AuthError(f"device code request failed: {resp.status} {body}")
        return body


async def async_poll_device_token(
    session: aiohttp.ClientSession, device_code: str
) -> dict | None:
    """Poll once for the device token. Returns token dict, or None if pending."""
    async with session.post(
        AUTH0_TOKEN_URL,
        data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": AUTH0_CLIENT_ID,
        },
    ) as resp:
        body = await resp.json()
        if resp.status == 200:
            return body
        if body.get("error") in ("authorization_pending", "slow_down"):
            return None
        raise AuthError(f"device token error: {body.get('error')} {body}")
