"""Config flow for Green Hero.

Primary path: a browser login (Authorization Code + PKCE) that gives Home
Assistant its own refresh-token family, so it never fights the Green Hero web
app over a shared rotating token. Auth0 returns the code in a web_message page
on login.greenhero.com (never redirecting to the Green Hero SPA, which would
navigate away and lose it); the user opens that page with `view-source:` and
pastes its source here.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .auth import (
    AuthError,
    TokenStore,
    async_exchange_code,
    build_authorize_url,
    generate_pkce,
    generate_state,
)
from .const import CONF_REFRESH_TOKEN, DOMAIN

_LOGGER = logging.getLogger(__name__)


def _json_field(text: str, name: str) -> str | None:
    match = re.search(rf'"{name}"\s*:\s*"([^"]+)"', text)
    return match.group(1) if match else None


def _extract_code(pasted: str) -> tuple[str | None, str | None, str | None]:
    """Return (code, state, error) from what the user pasted.

    Accepts the source of Auth0's web_message "Authorization Response" page
    (`"code":"..."` inside a script), a redirect URL with the code in the
    fragment or query, or a bare code.
    """
    pasted = pasted.strip()
    if "authorization_response" in pasted:
        return (
            _json_field(pasted, "code"),
            _json_field(pasted, "state"),
            _json_field(pasted, "error"),
        )
    if "code=" not in pasted:
        # Text without a code (a URL, a web page) is not a bare code.
        if not pasted or any(c in pasted for c in ":/<> \n"):
            return None, None, None
        return pasted, None, None
    url = urlparse(pasted)
    for part in (url.fragment.lstrip("/"), url.query):
        qs = parse_qs(part)
        if qs.get("code"):
            return qs["code"][0], qs.get("state", [None])[0], None
    return None, None, None


class GreenHeroConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._verifier: str | None = None
        self._challenge: str | None = None
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
            pasted = user_input["result"]
            code, state, error = _extract_code(pasted)
            if error in ("login_required", "interaction_required"):
                errors["base"] = "not_signed_in"
            elif error:
                _LOGGER.warning("Green Hero login returned error: %s", error)
                errors["base"] = "invalid_auth"
            elif not code:
                # The link itself, not the page it opens, is a common mix-up.
                errors["base"] = (
                    "pasted_login_link" if "/authorize?" in pasted
                    else "invalid_code"
                )
            elif state is not None and state != self._state:
                # Usually the Green Hero app's own login URL, not our link's.
                errors["base"] = "state_mismatch"
            else:
                session = async_get_clientsession(self.hass)
                try:
                    token = await async_exchange_code(session, code, self._verifier)
                except AuthError as err:
                    _LOGGER.warning("Green Hero login failed: %s", err)
                    errors["base"] = "invalid_auth"
                else:
                    refresh_token = token.get("refresh_token")
                    if not refresh_token:
                        errors["base"] = "no_refresh_token"
                    else:
                        return await self._finish(refresh_token)

        # One verifier/state per flow, so re-showing the form (errors, frontend
        # re-renders) never invalidates a login the user already started.
        if self._verifier is None:
            self._verifier, self._challenge = generate_pkce()
            self._state = generate_state()
        login_url = build_authorize_url(self._challenge, self._state)
        code_url = build_authorize_url(self._challenge, self._state, silent=True)
        return self.async_show_form(
            step_id="browser",
            data_schema=vol.Schema(
                {
                    vol.Required("result"): TextSelector(
                        TextSelectorConfig(multiline=True)
                    )
                }
            ),
            description_placeholders={
                "login_url": login_url,
                "code_url": f"view-source:{code_url}",
            },
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
