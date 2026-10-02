"""Green Hero binary sensors."""
from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import prices
from .const import DOMAIN
from .coordinator import GreenHeroCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: GreenHeroCoordinator = entry.runtime_data
    async_add_entities([CheapNowBinarySensor(coordinator)])


class CheapNowBinarySensor(CoordinatorEntity[GreenHeroCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "cheap_now"

    def __init__(self, coordinator: GreenHeroCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_cheap_now"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.place_name or "Green Hero",
            manufacturer="Green Hero",
        )

    @property
    def is_on(self) -> bool | None:
        return prices.is_cheap_now(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        cur = prices.current_price(self.coordinator.data)
        return {"current_price": cur, **prices.stats_today(self.coordinator.data)}
