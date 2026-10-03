"""Green Hero sensors."""
from __future__ import annotations

import datetime as dt
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
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import prices
from .const import CURRENCY, DOMAIN, PRICE_UNIT
from .coordinator import GreenHeroCoordinator


# Overview totals are energy flows between Production, Battery, Grid and Load:
# P_B, P_L, P_G, B_L, B_G, G_L, plus L (total load). With quantity=currency the
# same keys hold money instead of kWh.
_FLOWS = ("P_B", "P_L", "P_G", "B_L", "B_G", "G_L", "L")


def _flows(payload: Any) -> dict[str, float]:
    total = payload.get("total") if isinstance(payload, dict) else None
    if not isinstance(total, dict):
        return {}
    return {
        k: float(total[k]) for k in _FLOWS if isinstance(total.get(k), (int, float))
    }


def _sum(f: dict[str, float], *keys: str) -> float | None:
    vals = [f[k] for k in keys if k in f]
    return round(sum(vals), 3) if vals else None


def _consumption(payload: Any) -> float | None:
    """Total household use in kWh: L, or grid + solar + battery into the load."""
    f = _flows(payload)
    if "L" in f:
        return round(f["L"], 3)
    return _sum(f, "G_L", "P_L", "B_L")


def _grid_cost(payload: Any) -> float | None:
    """What grid electricity used at home cost (G_L in currency mode)."""
    f = _flows(payload)
    return round(f["G_L"], 2) if "G_L" in f else None


def _flow_attrs(payload: Any) -> dict[str, Any]:
    f = _flows(payload)
    attrs: dict[str, Any] = {
        "from_grid": f.get("G_L"),
        "from_solar": f.get("P_L"),
        "from_battery": f.get("B_L"),
        "solar_to_battery": f.get("P_B"),
        "solar_to_grid": f.get("P_G"),
        "battery_to_grid": f.get("B_G"),
        "total_use": f.get("L"),
        "exported": _sum(f, "P_G", "B_G"),
    }
    return {k: v for k, v in attrs.items() if v is not None}


def _cheapest_price(d: dict) -> float | None:
    r = prices.cheapest_today(d)
    return round(r[1], 4) if r else None


def _cheapest_time(d: dict) -> dt.datetime | None:
    r = prices.cheapest_today(d)
    return r[0] if r else None


def _peak_price(d: dict) -> float | None:
    r = prices.peak_today(d)
    return round(r[1], 4) if r else None


def _spot_now(d: dict) -> float | None:
    v = prices.current_price(d)
    return round(v, 4) if v is not None else None


def _spot_attrs(d: dict) -> dict[str, Any]:
    attrs: dict[str, Any] = dict(prices.stats_today(d))
    attrs["prices_today"] = prices.day_rows(d, 0)
    attrs["prices_tomorrow"] = prices.day_rows(d, 1)
    return attrs


@dataclass(frozen=True, kw_only=True)
class GreenHeroSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict[str, Any]], Any]
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] | None = None


SENSORS: tuple[GreenHeroSensorDescription, ...] = (
    # --- battery ---
    GreenHeroSensorDescription(
        key="battery_soc", translation_key="battery_soc",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (d.get("battery") or {}).get("soc"),
    ),
    GreenHeroSensorDescription(
        key="battery_power", translation_key="battery_power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: (d.get("battery") or {}).get("power"),
    ),
    # --- spot price (incl. future via attributes) ---
    GreenHeroSensorDescription(
        key="spot_price_now", translation_key="spot_price_now",
        native_unit_of_measurement=PRICE_UNIT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_spot_now, attrs_fn=_spot_attrs,
    ),
    GreenHeroSensorDescription(
        key="spot_price_cheapest", translation_key="spot_price_cheapest",
        native_unit_of_measurement=PRICE_UNIT,
        value_fn=_cheapest_price,
    ),
    GreenHeroSensorDescription(
        key="spot_price_peak", translation_key="spot_price_peak",
        native_unit_of_measurement=PRICE_UNIT,
        value_fn=_peak_price,
    ),
    GreenHeroSensorDescription(
        key="spot_price_cheapest_time", translation_key="spot_price_cheapest_time",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_cheapest_time,
    ),
    # --- cost (currency) ---
    GreenHeroSensorDescription(
        key="cost_today", translation_key="cost_today",
        native_unit_of_measurement=CURRENCY,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: _grid_cost(d.get("cost_day")),
        attrs_fn=lambda d: _flow_attrs(d.get("cost_day")),
    ),
    GreenHeroSensorDescription(
        key="cost_month", translation_key="cost_month",
        native_unit_of_measurement=CURRENCY,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: _grid_cost(d.get("cost_month")),
        attrs_fn=lambda d: _flow_attrs(d.get("cost_month")),
    ),
    GreenHeroSensorDescription(
        key="cost_year", translation_key="cost_year",
        native_unit_of_measurement=CURRENCY,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: _grid_cost(d.get("cost_year")),
        attrs_fn=lambda d: _flow_attrs(d.get("cost_year")),
    ),
    # --- energy (Energy dashboard compatible) ---
    GreenHeroSensorDescription(
        key="energy_today", translation_key="energy_today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _consumption(d.get("energy_day")),
        attrs_fn=lambda d: _flow_attrs(d.get("energy_day")),
    ),
    GreenHeroSensorDescription(
        key="energy_lifetime", translation_key="energy_lifetime",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: _consumption(d.get("energy_lifetime")),
        attrs_fn=lambda d: _flow_attrs(d.get("energy_lifetime")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: GreenHeroCoordinator = entry.runtime_data
    async_add_entities(GreenHeroSensor(coordinator, d) for d in SENSORS)


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
