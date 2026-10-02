"""The Green Hero integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import GreenHeroApi
from .auth import AuthError, TokenStore
from .const import CONF_REFRESH_TOKEN
from .coordinator import GreenHeroCoordinator

PLATFORMS = ["sensor", "binary_sensor"]
type GreenHeroConfigEntry = ConfigEntry[GreenHeroCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: GreenHeroConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    tokens = TokenStore(refresh_token=entry.data[CONF_REFRESH_TOKEN])
    tokens.set_session(session)
    try:
        await tokens.async_get_token()
    except AuthError as err:
        raise ConfigEntryAuthFailed(str(err)) from err

    # Persist rotated refresh token back to the entry.
    if tokens.refresh_token != entry.data[CONF_REFRESH_TOKEN]:
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_REFRESH_TOKEN: tokens.refresh_token}
        )

    api = GreenHeroApi(session, tokens)
    coordinator = GreenHeroCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    # Keep the stored refresh token up to date as it rotates.
    def _persist_token() -> None:
        if tokens.refresh_token != entry.data[CONF_REFRESH_TOKEN]:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_REFRESH_TOKEN: tokens.refresh_token}
            )

    coordinator.async_add_listener(_persist_token)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GreenHeroConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
