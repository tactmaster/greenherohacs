"""Self-driving explorer. Usage:
    export GH_TOKEN="eyJ..."     # or: python3 try_it.py "eyJ..."
    python3 try_it.py
Fetches your places, then exercises the parameterized endpoints with real
place_id / electricity_area. Prints the 422 body when something's still off.
"""
import datetime as dt
import json
import os
import sys

from client import GreenHeroClient, GreenHeroError


def show(label, fn):
    try:
        data = fn()
        txt = json.dumps(data, indent=2, ensure_ascii=False) if not isinstance(data, bytes) else f"<{len(data)} bytes>"
        print(f"\n=== {label} ===\n{txt[:1800]}")
        return data
    except GreenHeroError as e:
        print(f"\n=== {label} ===\nHTTP ERROR: {e}")
    except Exception as e:
        print(f"\n=== {label} ===\nFAILED: {e}")


def main():
    token = (sys.argv[1] if len(sys.argv) > 1 else "") or os.environ.get("GH_TOKEN", "")
    if not token:
        sys.exit("No token. Set GH_TOKEN or pass it as arg 1.")
    gh = GreenHeroClient(token)

    show("user", gh.user)
    places = show("places", gh.places) or []

    # pull a place_id + electricity_area to drive the rest
    place_id = area = None
    if isinstance(places, list) and places:
        p0 = places[0]
        db = p0.get("db_place", p0)  # fields are nested under db_place
        place_id = db.get("place_id") or db.get("placeId")
        area = db.get("electricity_area") or db.get("electricityArea")
    print(f"\n[using place_id={place_id} electricity_area={area}]")


    if place_id:
        show("overview/day (currency)", lambda: gh.overview(place_id, "day", "currency"))
        show("overview/day (energy)",   lambda: gh.overview(place_id, "day", "energy"))
        show("battery-status",          lambda: gh.battery_status(place_id))
        show("battery-history/day",     lambda: gh.battery_history(place_id, "day"))

    if area:
        today = dt.date.today().isoformat()
        tomorrow = (dt.date.today() + dt.timedelta(days=1)).isoformat()
        show("spot-prices", lambda: gh.spot_prices(area, today, tomorrow, 60))

    show("notifications", gh.notifications)


if __name__ == "__main__":
    main()
