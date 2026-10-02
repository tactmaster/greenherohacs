"""Validate the refresh-token flow end to end (no Home Assistant needed).

1) Log into app.greenhero.com in your browser.
2) DevTools -> Network -> find POST login.greenhero.com/oauth/token
   -> open the RESPONSE -> copy the "refresh_token" value.
3) Run:  python3 refresh_login.py <REFRESH_TOKEN>

It exchanges the refresh token for an access token, prints lifetime info,
then calls /v0/user and /v0/battery-status to prove the token works.
"""
import sys

import requests

from client import GreenHeroClient  # reuse the sync client

TOKEN_URL = "https://login.greenhero.com/oauth/token"
CLIENT_ID = "s37BNkGesz6HLgWo8vLtVZcFl3iL5eUa"


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 refresh_login.py <REFRESH_TOKEN>")
    refresh_token = sys.argv[1].strip()

    r = requests.post(TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
    }, timeout=20)
    if not r.ok:
        sys.exit(f"Refresh failed: {r.status_code} {r.text}")
    tok = r.json()
    print("access_token (first 25):", tok["access_token"][:25], "...")
    print("expires_in (seconds):", tok.get("expires_in"), f"(~{tok.get('expires_in',0)/3600:.1f} h)")
    print("new refresh_token returned (rotation):", "refresh_token" in tok)
    print("scope:", tok.get("scope"))
    if "refresh_token" in tok:
        open("refresh_token.txt", "w").write(tok["refresh_token"])
        print("saved rotated refresh_token -> refresh_token.txt")

    gh = GreenHeroClient(tok["access_token"])
    print("\n/v0/user ok:", bool(gh.user().get("given_name")))
    places = gh.places()
    db = (places[0].get("db_place", places[0]) if places else {})
    place_id = db.get("place_id")
    print("/v0/battery-status:", gh.battery_status(place_id=place_id))


if __name__ == "__main__":
    main()
