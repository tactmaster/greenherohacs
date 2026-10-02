"""Data update coordinator for Green Hero."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GreenHeroApi, GreenHeroApiError
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class GreenHeroCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: GreenHeroApi) -> None:
        super().__init__(
            hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL
        )
        self.api = api
        self.entry = entry
        self.place_id: str | None = None
        self.electricity_area: str | None = None
        self.place_name: str | None = None

    async def _async_setup(self) -> None:
        """Resolve the primary place once."""
        places = await self.api.places()
        if places:
            db = places[0].get("db_place", places[0])
            self.place_id = db.get("place_id")
            self.electricity_area = db.get("electricity_area")
            self.place_name = db.get("name")

    async def _async_update_data(self) -> dict[str, Any]:
        if self.place_id is None:
            await self._async_setup()
        data: dict[str, Any] = {}
        try:
            data["battery"] = await self.api.battery_status(self.place_id)
        except GreenHeroApiError as err:
            _LOGGER.debug("battery_status unavailable: %s", err)
            data["battery"] = {}
        try:
            if self.electricity_area:
                data["spot_prices"] = await self.api.spot_prices(self.electricity_area)
        except GreenHeroApiError as err:
            _LOGGER.debug("spot_prices unavailable: %s", err)
        try:
            if self.place_id:
                data["overview_day"] = await self.api.overview(self.place_id, "day", "currency")
        except GreenHeroApiError as err:
            _LOGGER.debug("overview unavailable: %s", err)
        if not data.get("battery") and "spot_prices" not in data:
            raise UpdateFailed("no data returned from Green Hero")
        return data
