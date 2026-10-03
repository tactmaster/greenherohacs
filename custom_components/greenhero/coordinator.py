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


def _rows_from(payload) -> list:
    """Extract a price-row list from a spot-prices payload, tolerant of shape."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for k in ("prices", "values", "data", "spot_prices"):
            v = payload.get(k)
            if isinstance(v, list):
                return v
            if isinstance(v, dict):
                for kk in ("prices", "values"):
                    if isinstance(v.get(kk), list):
                        return v[kk]
    return []


class GreenHeroCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: GreenHeroApi) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.api = api
        self.entry = entry
        self.place_id: str | None = None
        self.electricity_area: str | None = None
        self.place_name: str | None = None
        self._warned: set[str] = set()

    def _log_failure(self, key: str, err: Exception) -> None:
        """Warn once per data source, then keep further repeats at debug."""
        if key in self._warned:
            _LOGGER.debug("%s unavailable: %s", key, err)
        else:
            self._warned.add(key)
            _LOGGER.warning("Green Hero %s unavailable: %s", key, err)

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
            self._log_failure(key, err)

    async def _async_update_data(self) -> dict[str, Any]:
        if self.place_id is None:
            await self._async_setup()
        data: dict[str, Any] = {}

        import datetime as _dt

        await self._try(data, "battery", self.api.battery_status(self.place_id))
        if self.electricity_area:
            # The web app fetches one day at a time; get today + tomorrow and merge
            # so we have day-ahead prices for charts/automations.
            merged: list = []
            for off in (0, 1):
                day = (_dt.date.today() + _dt.timedelta(days=off)).isoformat()
                try:
                    payload = await self.api.spot_prices_day(self.electricity_area, day)
                except GreenHeroApiError as err:
                    # Tomorrow's prices only appear in the afternoon; not an error.
                    if off == 0:
                        self._log_failure("spot_prices", err)
                    continue
                rows = _rows_from(payload)
                merged.extend(rows)
            if merged:
                data["spot_prices"] = {"prices": merged}
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
