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

Green Hero logs in through Auth0. When you add the integration you get two options:

### Log in with browser (recommended)

1. The setup dialog shows a **Sign in to Green Hero** link. Open it and sign in
   (Google works).
2. You'll be redirected to `app.greenhero.com` with `?code=...` in the URL. The
   page may show an error — that's expected and harmless.
3. Copy the **full URL** from the address bar and paste it into the dialog.

Home Assistant exchanges that code for its **own** refresh token (a separate
token family from the web/phone apps), then mints short-lived access tokens from
it automatically and rotates it in the background. You log in once.

This flow uses its own PKCE `state`, so the Green Hero web app cannot consume the
authorization code — it stays valid for Home Assistant.

### Paste a refresh token (advanced)

Pull the `refresh_token` from a logged-in web session (browser console, the
`@@auth0spajs@@` localStorage entry) and paste it. **Caveat:** refresh tokens
rotate and are single-use. If the web app keeps running it will rotate the shared
token and break Home Assistant, so prefer the browser login above. Do **not**
run the `tools/` scripts with a token you also give Home Assistant — that
consumes it.

## Development helpers

The `tools/` directory contains standalone scripts used to explore the API
(no Home Assistant required): `client.py`, `try_it.py`, `pkce_login.py`, `refresh_login.py`,
`device_login.py`. They use only the public Auth0 client id.

## Disclaimer

Provided as-is under the MIT License. Use at your own risk.
