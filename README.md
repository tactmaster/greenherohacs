# Green Hero for Home Assistant

Unofficial [HACS](https://hacs.xyz/) custom integration for the
[Green Hero](https://www.greenhero.com/en/app/) energy app (Green Hero AB, Sweden).

It reads your data from the same private API the Green Hero web app uses
(`app.greenhero.com/api/v0`) and exposes it as Home Assistant sensors.

> **Unofficial & unsupported.** Not affiliated with or endorsed by Green Hero AB.
> The API is private and may change or break at any time. Read-only usage only.

## Sensors

| Sensor | Description |
|---|---|
| Battery charge | Battery state of charge (%) |
| Battery power | Battery charge/discharge power (kW) |
| Spot price now | Nord Pool spot price for the current hour (SEK/kWh) |

More (consumption/cost overview, grid import/export, spot min/max/avg) can be added.

## Installation (HACS custom repository)

1. HACS → ⋮ → **Custom repositories**.
2. Add `https://github.com/tactmaster/greenherohacs` as an **Integration**.
3. Install **Green Hero**, then restart Home Assistant.
4. **Settings → Devices & Services → Add Integration → Green Hero**.

## Authentication

Green Hero logs in through Auth0. This integration authenticates with a
**refresh token** that you obtain once from a logged-in browser session; Home
Assistant then mints short-lived access tokens from it automatically (the
refresh token rotates on each use and the integration stores the latest one).

### Getting your refresh token

1. Log in at [app.greenhero.com](https://app.greenhero.com).
2. Open the browser console (F12 → Console) and run:

   ```js
   Object.keys(localStorage)
     .filter(k => k.startsWith('@@auth0spajs@@'))
     .forEach(k => {
       try { console.log(JSON.parse(localStorage.getItem(k)).body?.refresh_token); }
       catch (e) {}
     });
   ```

   If it prints a value, that's your refresh token.
3. If it prints nothing, use the **Network** tab instead: find the
   `POST login.greenhero.com/oauth/token` request and copy `refresh_token`
   from its JSON **response**.
4. Paste it into the integration's setup dialog.

> Note: using the refresh token in Home Assistant may log the **web** app out on
> its next token refresh (token rotation). The mobile app is unaffected.

## Development helpers

The `tools/` directory contains standalone scripts used to explore the API
(no Home Assistant required): `client.py`, `try_it.py`, `refresh_login.py`,
`device_login.py`. They use only the public Auth0 client id.

## Disclaimer

Provided as-is under the MIT License. Use at your own risk.
