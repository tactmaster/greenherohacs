"""Spot-price helpers shared by the sensor/binary_sensor platforms.

Defensive: tolerates [timestamp, value] pairs or dict entries, with or without
timezone, so it keeps working if the API shape shifts slightly.
"""
from __future__ import annotations

import datetime as dt
from typing import Any


def iter_prices(data: dict[str, Any]):
    """Yield (aware-datetime, float) from the spot-prices payload."""
    sp = data.get("spot_prices") or {}
    rows = sp.get("prices") or sp.get("values") or []
    for item in rows:
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
            if t.tzinfo is None:
                t = t.astimezone()
            yield t, float(val)
        except (ValueError, TypeError):
            continue


def sorted_prices(data: dict[str, Any]) -> list[tuple[dt.datetime, float]]:
    return sorted(iter_prices(data), key=lambda p: p[0])


def current_price(data: dict[str, Any]) -> float | None:
    now = dt.datetime.now().astimezone()
    best = None
    for t, v in iter_prices(data):
        if t <= now and (best is None or t > best[0]):
            best = (t, v)
    return best[1] if best else None


def _by_day(data: dict[str, Any], day: dt.date) -> list[tuple[dt.datetime, float]]:
    return [(t, v) for t, v in sorted_prices(data) if t.astimezone().date() == day]


def day_rows(data: dict[str, Any], offset: int = 0) -> list[dict[str, Any]]:
    """Prices for today (offset 0) or tomorrow (offset 1) as [{start, price}]."""
    day = dt.date.today() + dt.timedelta(days=offset)
    return [{"start": t.isoformat(), "price": v} for t, v in _by_day(data, day)]


def stats_today(data: dict[str, Any]) -> dict[str, float]:
    vals = [v for _, v in _by_day(data, dt.date.today())]
    if not vals:
        # fall back to payload-level stats if present
        sp = data.get("spot_prices") or {}
        return {k: sp[k] for k in ("min", "max", "average") if k in sp}
    return {"min": min(vals), "max": max(vals), "average": round(sum(vals) / len(vals), 4)}


def cheapest_today(data: dict[str, Any]) -> tuple[dt.datetime, float] | None:
    rows = _by_day(data, dt.date.today())
    return min(rows, key=lambda p: p[1]) if rows else None


def peak_today(data: dict[str, Any]) -> tuple[dt.datetime, float] | None:
    rows = _by_day(data, dt.date.today())
    return max(rows, key=lambda p: p[1]) if rows else None


def is_cheap_now(data: dict[str, Any]) -> bool | None:
    """True when the current price is at/below today's average."""
    cur = current_price(data)
    avg = stats_today(data).get("average")
    if cur is None or avg is None:
        return None
    return cur <= avg
