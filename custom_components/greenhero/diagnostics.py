"""Diagnostics for Green Hero: the raw payloads behind each sensor."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import GreenHeroConfigEntry
from .const import CONF_REFRESH_TOKEN

TO_REDACT = {CONF_REFRESH_TOKEN, "latitude", "longitude", "email"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GreenHeroConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "place": {
            "place_id": coordinator.place_id,
            "electricity_area": coordinator.electricity_area,
        },
        "last_update_success": coordinator.last_update_success,
        "data": async_redact_data(coordinator.data or {}, TO_REDACT),
    }
