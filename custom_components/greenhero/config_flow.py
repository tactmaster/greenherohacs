"""Config flow for Green Hero (refresh-token based)."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .auth import AuthError, TokenStore
from .const import CONF_REFRESH_TOKEN, DOMAIN


class GreenHeroConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            refresh_token = user_input[CONF_REFRESH_TOKEN].strip()
            session = async_get_clientsession(self.hass)
            tokens = TokenStore(refresh_token=refresh_token)
            tokens.set_session(session)
            try:
                await tokens.async_get_token()  # validates by refreshing once
            except AuthError:
                errors["base"] = "invalid_auth"
            else:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()
                # store the (possibly rotated) refresh token
                return self.async_create_entry(
                    title="Green Hero",
                    data={CONF_REFRESH_TOKEN: tokens.refresh_token},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_REFRESH_TOKEN): str}),
            errors=errors,
        )
