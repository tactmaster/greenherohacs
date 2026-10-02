"""Browser login via Authorization Code + PKCE (HA's own token family).

Run it, open the printed URL, sign in, then paste the URL you're redirected to.
It saves a fresh refresh_token and dumps spot-prices so we can verify the shape.

    python3 tools/pkce_login.py
"""
import base64
import hashlib
import json
import secrets
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from client import GreenHeroClient

DOMAIN = "https://login.greenhero.com"
CLIENT_ID = "s37BNkGesz6HLgWo8vLtVZcFl3iL5eUa"
REDIRECT_URI = "https://app.greenhero.com"
SCOPE = "openid profile email offline_access"


def main():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()
    ).rstrip(b"=").decode()
    state = secrets.token_urlsafe(24)
    url = f"{DOMAIN}/authorize?" + urlencode({
        "client_id": CLIENT_ID, "response_type": "code",
        "redirect_uri": REDIRECT_URI, "scope": SCOPE,
        "code_challenge": challenge, "code_challenge_method": "S256",
        "state": state,
    })
    print("1) Open this URL and sign in:\n\n   ", url, "\n")
    print("2) You'll be redirected to app.greenhero.com (may show an error - fine).")
    pasted = input("3) Paste the full URL from the address bar here:\n> ").strip()

    code = parse_qs(urlparse(pasted).query).get("code", [pasted])[0]
    r = requests.post(f"{DOMAIN}/oauth/token", data={
        "grant_type": "authorization_code", "client_id": CLIENT_ID,
        "code": code, "code_verifier": verifier, "redirect_uri": REDIRECT_URI,
    }, timeout=20)
    if not r.ok:
        raise SystemExit(f"Exchange failed: {r.status_code} {r.text}")
    tok = r.json()
    print("\nSUCCESS. refresh_token present:", "refresh_token" in tok,
          "| expires_in:", tok.get("expires_in"))
    if "refresh_token" in tok:
        open("refresh_token.txt", "w").write(tok["refresh_token"])
        print("saved refresh_token -> refresh_token.txt")

    gh = GreenHeroClient(tok["access_token"])
    places = gh.places()
    db = (places[0].get("db_place", places[0]) if places else {})
    area = db.get("electricity_area")
    print("\nelectricity_area:", area)
    print("\n=== RAW /v0/spot-prices (interval=60) ===")
    try:
        print(json.dumps(gh.spot_prices(area, interval=60), indent=2)[:2500])
    except Exception as e:
        print("interval=60 failed:", e)
    print("\n=== RAW /v0/spot-prices (interval=15) ===")
    try:
        print(json.dumps(gh.spot_prices(area, interval=15), indent=2)[:1500])
    except Exception as e:
        print("interval=15 failed:", e)


if __name__ == "__main__":
    main()
