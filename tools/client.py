"""Unofficial Python client for the Green Hero web app API (app.greenhero.com).

Reverse-engineered from the public SPA bundle. Read-only usage.

Auth: the app uses Auth0 (tenant greenhero.eu.auth0.com). For now you paste a
short-lived Bearer access token grabbed from your own browser session
(DevTools -> Network -> any /api/v0/* request -> copy the Authorization header).
The token is opaque, so we set X-OpenID-Issuer explicitly to the known tenant.
"""

from __future__ import annotations

from typing import Any

import requests

BASE_URL = "https://app.greenhero.com/api"
ISSUER = "https://greenhero.eu.auth0.com/"


class GreenHeroError(requests.HTTPError):
    """HTTPError that keeps the response body (422s name the missing fields)."""


class GreenHeroClient:
    def __init__(self, token: str, base_url: str = BASE_URL,
                 issuer: str = ISSUER, timeout: float = 10.0):
        token = token.strip()
        if token.lower().startswith("bearer "):
            token = token[7:].strip()
        self.token = token
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "X-OpenID-Issuer": issuer,
            "Accept": "application/json",
            "User-Agent": "greenhero-python/0.1",
        })

    def get(self, path: str, **params) -> Any:
        """GET a path; return parsed JSON (or bytes). Raises GreenHeroError
        with the response body attached on HTTP errors."""
        r = self.session.get(f"{self.base_url}{path}",
                              params=params or None, timeout=self.timeout)
        if not r.ok:
            body = r.text[:1000]
            raise GreenHeroError(
                f"{r.status_code} {r.reason} for {path} -> {body}", response=r)
        ctype = r.headers.get("content-type", "")
        return r.json() if "application/json" in ctype else r.content

    # --- endpoints (params confirmed from the bundle) ---
    def user(self):   return self.get("/v0/user")
    def places(self): return self.get("/v0/places")
    def sites(self):  return self.get("/v0/sites")
    def weather(self, **p): return self.get("/v0/weather", **p)

    def overview(self, place_id, mode="day", quantity="currency",
                 date=None, time_zone="Europe/Stockholm"):
        # server requires exactly one of date/timestamp; default to today
        if date is None:
            import datetime as _dt
            date = _dt.date.today().isoformat()
        return self.get(f"/v0/overview/{mode}",
                        place_id=place_id, quantity=quantity, date=date)

    def spot_prices(self, electricity_area, from_date=None, to_date=None,
                    interval=60, time_zone="Europe/Stockholm"):
        import datetime as _dt
        today = _dt.date.today()
        return self.get(
            "/v0/spot-prices",
            from_date=from_date or today.isoformat(),
            to_date=to_date or (today + _dt.timedelta(days=1)).isoformat(),
            interval=interval, electricity_area=electricity_area)

    def battery_status(self, place_id=None):
        return self.get("/v0/battery-status", **({"place_id": place_id} if place_id else {}))

    def battery_history(self, place_id, period="day"):
        return self.get(f"/v0/battery-history/{period}", place_id=place_id)

    def invoices(self):        return self.get("/v0/invoices")
    def invoices_status(self): return self.get("/v0/invoices/status")
    def notifications(self):   return self.get("/v0/notifications")
