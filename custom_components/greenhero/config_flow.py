"""Config flow for Green Hero.

Primary path: a browser login (Authorization Code + PKCE) that gives Home
Assistant its own refresh-token family, so it never fights the Green Hero web
app over a shared rotating token. We use our own `state`, so the Green Hero SPA
cannot consume our `code` (state mismatch) and it stays valid for HA to exchange.
"""
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .auth import (
    AuthError,
    TokenStore,
    async_exchange_code,
    build_authorize_url,
    generate_pkce,
    generate_state,
)
from .const import CONF_REFRESH_TOKEN, DOMAIN


def _extract_code(pasted: str) -> str | None:
    """Accept a full redirect URL or a bare code."""
    pasted = pasted.strip()
    if "code=" in pasted:
        qs = parse_qs(urlparse(pasted).query)
        if qs.get("code"):
            return qs["code"][0]
    return pasted or None


class GreenHeroConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._verifier: str | None = None
        self._state: str | None = None
        self._reauth_entry: ConfigEntry | None = None

    # --- reauth ---
    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_user()

    # --- entry points ---
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="user", menu_options=["browser", "refresh_token"]
        )

    async def _finish(self, refresh_token: str) -> ConfigFlowResult:
        if self._reauth_entry is not None:
            self.hass.config_entries.async_update_entry(
                self._reauth_entry,
                data={**self._reauth_entry.data, CONF_REFRESH_TOKEN: refresh_token},
            )
            await self.hass.config_entries.async_reload(self._reauth_entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="Green Hero", data={CONF_REFRESH_TOKEN: refresh_token}
        )

    async def async_step_browser(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            code = _extract_code(user_input["result"])
            if not code:
                errors["base"] = "invalid_code"
            else:
                session = async_get_clientsession(self.hass)
                try:
                    token = await async_exchange_code(session, code, self._verifier)
                except AuthError:
                    errors["base"] = "invalid_auth"
                else:
                    refresh_token = token.get("refresh_token")
                    if not refresh_token:
                        errors["base"] = "no_refresh_token"
                    else:
                        return await self._finish(refresh_token)

        self._verifier, challenge = generate_pkce()
        self._state = generate_state()
        url = build_authorize_url(challenge, self._state)
        return self.async_show_form(
            step_id="browser",
            data_schema=vol.Schema({vol.Required("result"): str}),
            description_placeholders={"url": url},
            errors=errors,
        )

    async def async_step_refresh_token(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            tokens = TokenStore(refresh_token=user_input[CONF_REFRESH_TOKEN].strip())
            tokens.set_session(session)
            try:
                await tokens.async_get_token()
            except AuthError:
                errors["base"] = "invalid_auth"
            else:
                return await self._finish(tokens.refresh_token)

        return self.async_show_form(
            step_id="refresh_token",
            data_schema=vol.Schema({vol.Required(CONF_REFRESH_TOKEN): str}),
            errors=errors,
        )
