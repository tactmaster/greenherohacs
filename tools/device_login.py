"""Test the Auth0 Device Authorization flow for Green Hero.

Usage:
    python3 device_login.py CLIENT_ID [AUDIENCE]

CLIENT_ID / AUDIENCE are public values from your browser:
  DevTools -> Network -> request to login.greenhero.com/authorize (or /oauth/token)
  -> copy client_id (and audience, if present).

If device flow is NOT enabled for the client, Auth0 returns a clear error and
we fall back to the refresh-token method instead.
"""
import sys
import time

import requests

DOMAIN = "https://login.greenhero.com"
SCOPE = "openid profile email offline_access"


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 device_login.py CLIENT_ID [AUDIENCE]")
    client_id = sys.argv[1].strip()
    audience = sys.argv[2].strip() if len(sys.argv) > 2 else None

    # 1) request a device code
    body = {"client_id": client_id, "scope": SCOPE}
    if audience:
        body["audience"] = audience
    r = requests.post(f"{DOMAIN}/oauth/device/code", data=body, timeout=15)
    if not r.ok:
        print(f"Device code request failed ({r.status_code}): {r.text}")
        print("\n-> Device flow is likely NOT enabled for this client. "
              "We'll use the refresh-token method instead.")
        return
    dc = r.json()
    print("Open this URL in a browser and sign in with Google:\n")
    print("   ", dc.get("verification_uri_complete") or dc.get("verification_uri"))
    print("\nUser code:", dc.get("user_code"))
    interval = dc.get("interval", 5)
    device_code = dc["device_code"]

    # 2) poll the token endpoint
    print("\nWaiting for you to approve...")
    while True:
        time.sleep(interval)
        tr = requests.post(f"{DOMAIN}/oauth/token", data={
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": client_id,
        }, timeout=15)
        if tr.ok:
            tok = tr.json()
            print("\n*** SUCCESS ***")
            print("access_token (first 30):", tok["access_token"][:30], "...")
            print("refresh_token present:", "refresh_token" in tok)
            print("expires_in (seconds):", tok.get("expires_in"))
            print("token_type:", tok.get("token_type"))
            print("scope:", tok.get("scope"))
            # save refresh token for the HA integration / fallback
            if "refresh_token" in tok:
                open("refresh_token.txt", "w").write(tok["refresh_token"])
                print("\nSaved refresh_token -> refresh_token.txt")
            return
        err = tr.json().get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 2
            continue
        print(f"\nStopped: {err} -> {tr.text}")
        return


if __name__ == "__main__":
    main()
