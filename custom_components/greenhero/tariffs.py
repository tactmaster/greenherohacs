"""What grid electricity really costs, from Green Hero data plus tariff options.

Swedish pricing (2026): every imported kWh pays the spot price, the grid
company's transfer fee and energy tax, with 25% VAT on all of it. Green Hero is
the supplier and adds no markup on the spot price. An exported kWh earns the spot price plus any grid benefit (nätnytta) or
supplier bonus; there's no VAT for private sellers and the 60 öre tax credit
ended on 1 January 2026. Import and export are priced separately, never netted.

Green Hero's import cost already covers the supplier side (spot + VAT) but
not the grid company's charges, which these helpers add.
"""
from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from typing import Any

from . import prices
from .const import (
    CONF_ENERGY_TAX,
    CONF_EXPORT_COMPENSATION,
    CONF_FIXED_GRID_FEE,
    CONF_TRANSFER_FEE,
    DEFAULT_OPTIONS,
    VAT_RATE,
)

ORE_PER_SEK = 100


def _opt(options: Mapping[str, Any], key: str) -> float:
    return float(options.get(key, DEFAULT_OPTIONS[key]))


def _grid_per_kwh(options: Mapping[str, Any]) -> float:
    """Grid company charges per imported kWh, SEK incl. VAT."""
    return (_opt(options, CONF_TRANSFER_FEE) + _opt(options, CONF_ENERGY_TAX)) / ORE_PER_SEK


def _month_rows(data: dict[str, Any]) -> list[tuple[str, dict]]:
    payload = data.get("energy_lifetime")
    rows = payload.get("months") if isinstance(payload, dict) else None
    return [r for r in rows or [] if isinstance(r, list) and len(r) == 2]


def imported_kwh(data: dict[str, Any], *, year: bool = False) -> float | None:
    """Grid import (G_L) this month, or this year so far, from the lifetime data."""
    today = dt.date.today()
    prefix = f"{today.year}-" if year else f"{today:%Y-%m}-"
    vals = [
        v["G_L"]
        for month, v in _month_rows(data)
        if str(month).startswith(prefix)
        and isinstance(v, dict)
        and isinstance(v.get("G_L"), (int, float))
    ]
    return round(sum(vals), 3) if vals else None


def import_price_now(data: dict[str, Any], options: Mapping[str, Any]) -> float | None:
    """SEK for one kWh from the grid right now, all charges and VAT included."""
    spot = prices.current_price(data)
    if spot is None:
        return None
    return round(spot * (1 + VAT_RATE) + _grid_per_kwh(options), 4)


def export_price_now(data: dict[str, Any], options: Mapping[str, Any]) -> float | None:
    """SEK earned for one kWh exported right now."""
    spot = prices.current_price(data)
    if spot is None:
        return None
    return round(spot + _opt(options, CONF_EXPORT_COMPENSATION) / ORE_PER_SEK, 4)


def grid_fees(
    data: dict[str, Any], options: Mapping[str, Any], *, year: bool = False
) -> float | None:
    """Grid company bill: imported kWh × (transfer fee + energy tax) + fixed fee.

    Uses today's rates for the whole period, so a year figure is an estimate
    if the grid company changed its prices during the year.
    """
    kwh = imported_kwh(data, year=year)
    if kwh is None:
        return None
    months = dt.date.today().month if year else 1
    return round(kwh * _grid_per_kwh(options) + months * _opt(options, CONF_FIXED_GRID_FEE), 2)


def grid_fee_attrs(
    data: dict[str, Any], options: Mapping[str, Any], *, year: bool = False
) -> dict[str, Any]:
    return {
        "imported_kwh": imported_kwh(data, year=year),
        "transfer_fee_ore_per_kwh": _opt(options, CONF_TRANSFER_FEE),
        "energy_tax_ore_per_kwh": _opt(options, CONF_ENERGY_TAX),
        "fixed_fee_sek_per_month": _opt(options, CONF_FIXED_GRID_FEE),
    }


def _total(payload: Any, *keys: str) -> float | None:
    total = payload.get("total") if isinstance(payload, dict) else None
    if not isinstance(total, dict):
        return None
    vals = [total[k] for k in keys if isinstance(total.get(k), (int, float))]
    return sum(vals) if vals else None


def net_cost_month(data: dict[str, Any], options: Mapping[str, Any]) -> float | None:
    """Green Hero import cost + grid fees − export earnings, this month."""
    supplier = _total(data.get("cost_month"), "G_L")
    fees = grid_fees(data, options)
    if supplier is None or fees is None:
        return None
    earned = _total(data.get("cost_month"), "P_G", "B_G") or 0.0
    return round(supplier + fees - earned, 2)


def net_cost_attrs(data: dict[str, Any], options: Mapping[str, Any]) -> dict[str, Any]:
    supplier = _total(data.get("cost_month"), "G_L")
    earned = _total(data.get("cost_month"), "P_G", "B_G")
    return {
        "electricity_cost": round(supplier, 2) if supplier is not None else None,
        "grid_fees": grid_fees(data, options),
        "export_earnings": round(earned, 2) if earned is not None else None,
    }
