"""Async Green Hero API client (read-only). Mirrors the SPA's /api/v0 surface."""
from __future__ import annotations

import datetime as dt
from typing import Any

import aiohttp

from .auth import TokenStore
from .const import API_BASE, OPENID_ISSUER


class GreenHeroApiError(Exception):
    """API call failed."""


class GreenHeroApi:
    def __init__(self, session: aiohttp.ClientSession, tokens: TokenStore) -> None:
        self._session = session
        self._tokens = tokens

    async def _get(self, path: str, **params: Any) -> Any:
        token = await self._tokens.async_get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "X-OpenID-Issuer": OPENID_ISSUER,
            "Accept": "application/json",
        }
        async with self._session.get(
            f"{API_BASE}{path}",
            params={k: v for k, v in params.items() if v is not None} or None,
            headers=headers,
        ) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise GreenHeroApiError(f"{resp.status} {path}: {text[:300]}")
            if "application/json" in resp.headers.get("content-type", ""):
                return await resp.json()
            return text

    async def user(self) -> dict:
        return await self._get("/v0/user")

    async def places(self) -> list[dict]:
        return await self._get("/v0/places")

    async def battery_status(self, place_id: str | None = None) -> dict:
        return await self._get("/v0/battery-status", place_id=place_id)

    async def spot_prices_day(
        self, electricity_area: str, date: str, interval: int = 15
    ) -> dict:
        """Prices for a single day (the web app calls with from_date == to_date)."""
        return await self._get(
            "/v0/spot-prices",
            electricity_area=electricity_area,
            from_date=date,
            to_date=date,
            interval=interval,
        )

    async def overview(
        self, place_id: str, mode: str = "day",
        quantity: str = "currency", date: str | None = None,
    ) -> dict:
        return await self._get(
            f"/v0/overview/{mode}",
            place_id=place_id,
            quantity=quantity,
            date=date or dt.date.today().isoformat(),
        )
