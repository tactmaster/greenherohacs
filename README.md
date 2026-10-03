# Green Hero for Home Assistant

Unofficial [HACS](https://hacs.xyz/) custom integration for the
[Green Hero](https://www.greenhero.com/en/app/) energy app (Green Hero AB, Sweden).

It reads your data from the same private API the Green Hero web app uses
(`app.greenhero.com/api/v0`) and exposes it as Home Assistant sensors.

> **Unofficial & unsupported.** Not affiliated with or endorsed by Green Hero AB.
> The API is private and may change or break at any time. Read-only usage only.

## Entities

**Battery**
- Battery charge (%) and Battery power (kW)

**Spot price (incl. future)**
- Spot price now (SEK/kWh) — with `prices_today` / `prices_tomorrow` arrays and
  `min` / `max` / `average` as attributes (the day-ahead prices live here)
- Cheapest / peak price today, and Cheapest hour today (a timestamp)
- `binary_sensor` **Electricity cheap now** — on when the current price is at or
  below today's average (handy for charging automations)

**Cost & energy** (from `/v0/overview`)
- Cost today / this month / this year (SEK)
- Energy today and Energy lifetime (kWh) — `total_increasing`, so they can be
  added to the native **Energy dashboard**

> Cost/energy field mapping is provisional until verified against a live
> `/v0/overview` response; unexpected shapes show as *Unknown* rather than erroring.

## Showing future (day-ahead) prices

Core Home Assistant history only plots the past, so day-ahead prices are exposed
as **attributes** on `sensor.green_hero_spot_price_now` and plotted with the
[ApexCharts card](https://github.com/RomRider/apexcharts-card) (HACS):

```yaml
type: custom:apexcharts-card
graph_span: 48h
span:
  start: day
now:
  show: true
  label: Now
header:
  show: true
  title: Spot price (today + tomorrow)
series:
  - entity: sensor.green_hero_spot_price_now
    name: Price
    type: column
    data_generator: |
      const t = entity.attributes.prices_today || [];
      const m = entity.attributes.prices_tomorrow || [];
      return [...t, ...m].map(p => [new Date(p.start).getTime(), p.price]);
```

Adjust the entity id to match your install.

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
2. You'll be redirected to `app.greenhero.com`, and the URL ends in
   `#/code=...&state=...`. The page may be blank or show an error. That's
   expected and harmless.
3. Copy the **full URL** from the address bar and paste it into the dialog.

Use the link from the dialog, not the normal Green Hero login. If your URL
contains `?code=`, it came from the Green Hero app's own login and won't work.

Home Assistant exchanges that code for its **own** refresh token (a separate
token family from the web/phone apps), then mints short-lived access tokens from
it automatically and rotates it in the background. You log in once.

The link asks Auth0 to return the code in the URL fragment (`#...`) rather than
the query string. The Green Hero web app only handles `?code=` callbacks; with
those it wipes the URL and starts its own login, which used to replace Home
Assistant's code with the web app's. With the fragment, the web app leaves the
code alone, so it stays in the address bar and valid for Home Assistant.

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
