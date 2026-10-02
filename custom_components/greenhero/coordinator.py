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
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
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

    async def _try(self, data: dict, key: str, coro) -> None:
        try:
            data[key] = await coro
        except GreenHeroApiError as err:
            _LOGGER.debug("%s unavailable: %s", key, err)

    async def _async_update_data(self) -> dict[str, Any]:
        if self.place_id is None:
            await self._async_setup()
        data: dict[str, Any] = {}

        await self._try(data, "battery", self.api.battery_status(self.place_id))
        if self.electricity_area:
            # today + tomorrow prices
            await self._try(data, "spot_prices", self.api.spot_prices(self.electricity_area))
        if self.place_id:
            # cost (currency) and energy for the usual periods
            await self._try(data, "cost_day", self.api.overview(self.place_id, "day", "currency"))
            await self._try(data, "cost_month", self.api.overview(self.place_id, "month", "currency"))
            await self._try(data, "cost_year", self.api.overview(self.place_id, "year", "currency"))
            await self._try(data, "energy_day", self.api.overview(self.place_id, "day", "energy"))
            await self._try(data, "energy_lifetime", self.api.overview(self.place_id, "lifetime", "energy"))

        if not data:
            raise UpdateFailed("no data returned from Green Hero")
        return data
