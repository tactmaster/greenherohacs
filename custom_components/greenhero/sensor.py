"""Green Hero sensors."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GreenHeroCoordinator


def _iter_prices(data: dict[str, Any]):
    """Yield (datetime, value) from the spot-prices payload, any known shape."""
    import datetime as dt

    sp = data.get("spot_prices") or {}
    prices = sp.get("prices") or sp.get("values") or []
    for item in prices:
        ts = val = None
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            ts, val = item[0], item[1]
        elif isinstance(item, dict):
            ts = item.get("timestamp") or item.get("start") or item.get("time")
            val = item.get("value") if item.get("value") is not None else item.get("price")
        if ts is None or val is None:
            continue
        try:
            t = dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            yield t, float(val)
        except (ValueError, TypeError):
            continue


def _current_spot_price(data: dict[str, Any]) -> float | None:
    """Pick the price for the current hour from the spot-prices payload."""
    import datetime as dt

    now = dt.datetime.now().astimezone()
    best = None
    for t, val in _iter_prices(data):
        if t.tzinfo is None:
            t = t.astimezone()
        if t <= now and (best is None or t > best[0]):
            best = (t, val)
    return best[1] if best else None


def _spot_price_attrs(data: dict[str, Any]) -> dict[str, Any]:
    sp = data.get("spot_prices") or {}
    vals = [v for _, v in _iter_prices(data)]
    attrs: dict[str, Any] = {}
    if "average" in sp:
        attrs["average"] = sp["average"]
    if "min" in sp:
        attrs["min"] = sp["min"]
    if "max" in sp:
        attrs["max"] = sp["max"]
    if vals and "average" not in attrs:
        attrs["min"] = min(vals)
        attrs["max"] = max(vals)
        attrs["average"] = round(sum(vals) / len(vals), 4)
    attrs["count"] = len(vals)
    return attrs


@dataclass(frozen=True, kw_only=True)
class GreenHeroSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS: tuple[GreenHeroSensorDescription, ...] = (
    GreenHeroSensorDescription(
        key="battery_soc",
        translation_key="battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (d.get("battery") or {}).get("soc"),
    ),
    GreenHeroSensorDescription(
        key="battery_power",
        translation_key="battery_power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (d.get("battery") or {}).get("power"),
    ),
    GreenHeroSensorDescription(
        key="spot_price_now",
        translation_key="spot_price_now",
        native_unit_of_measurement="SEK/kWh",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_current_spot_price,
        attrs_fn=_spot_price_attrs,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: GreenHeroCoordinator = entry.runtime_data
    async_add_entities(
        GreenHeroSensor(coordinator, desc) for desc in SENSORS
    )


class GreenHeroSensor(CoordinatorEntity[GreenHeroCoordinator], SensorEntity):
    _attr_has_entity_name = True
    entity_description: GreenHeroSensorDescription

    def __init__(
        self, coordinator: GreenHeroCoordinator, description: GreenHeroSensorDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            name=coordinator.place_name or "Green Hero",
            manufacturer="Green Hero",
        )

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if self.entity_description.attrs_fn is None:
            return None
        return self.entity_description.attrs_fn(self.coordinator.data)
