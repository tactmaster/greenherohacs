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


# --- Authorization Code + PKCE (browser login that gives HA its own token family) ---
import base64 as _b64
import hashlib as _hashlib
import secrets as _secrets
from urllib.parse import urlencode as _urlencode

from .const import AUTH0_DOMAIN, AUTH0_REDIRECT_URI


def generate_pkce() -> tuple[str, str]:
    """Return (code_verifier, code_challenge) for PKCE S256."""
    verifier = _b64.urlsafe_b64encode(_secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = _hashlib.sha256(verifier.encode()).digest()
    challenge = _b64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def generate_state() -> str:
    return _secrets.token_urlsafe(24)


def build_authorize_url(
    code_challenge: str, state: str, *, silent: bool = False
) -> str:
    """Build the Auth0 /authorize URL for the manual browser login.

    response_mode=web_message makes Auth0 answer with a small HTML page on
    login.greenhero.com that embeds the code (meant for postMessage to an
    app.greenhero.com opener; with no opener it just sits there). Any redirect
    to app.greenhero.com instead loads the Green Hero SPA, which navigates away
    and loses our code before the user can copy it.

    silent=True adds prompt=none: if the browser already has a Green Hero
    session the response page comes back immediately, so opening it with a
    `view-source:` prefix shows the code as plain, copyable text.
    """
    params = {
        "client_id": AUTH0_CLIENT_ID,
        "response_type": "code",
        "response_mode": "web_message",
        "redirect_uri": AUTH0_REDIRECT_URI,
        "scope": AUTH0_SCOPE,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    if silent:
        params["prompt"] = "none"
    return f"{AUTH0_DOMAIN}/authorize?{_urlencode(params)}"


async def async_exchange_code(
    session: aiohttp.ClientSession, code: str, code_verifier: str
) -> dict:
    """Exchange an authorization code for tokens (incl. a fresh refresh token)."""
    async with session.post(
        AUTH0_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "client_id": AUTH0_CLIENT_ID,
            "code": code,
            "code_verifier": code_verifier,
            "redirect_uri": AUTH0_REDIRECT_URI,
        },
    ) as resp:
        body = await resp.json()
        if resp.status != 200:
            raise AuthError(f"code exchange failed: {resp.status} {body}")
        return body
