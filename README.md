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
- Cost today / this month / this year (SEK): what the electricity you took
  from the grid cost
- Energy today and Energy lifetime (kWh): total household use (grid + solar +
  battery). These are `total_increasing`, so they can be added to the native
  **Energy dashboard**
- Each one has the full breakdown as attributes: `from_grid`, `from_solar`,
  `from_battery`, `solar_to_battery`, `solar_to_grid`, `battery_to_grid`,
  `total_use`, `exported`

Spot prices come from the API in öre/kWh and are shown in SEK/kWh.

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

Use a browser on a computer (Chrome, Edge or Firefox).

1. **Sign in** (skip if you're already logged in to Green Hero in that
   browser): click **Sign in to Green Hero** in the dialog and sign in (Google
   works). You'll end on a blank page. That's expected.
2. **Get the code**: copy the line in the dialog that starts with
   `view-source:`, paste it into the address bar and press Enter. You'll see a
   short page of code.
3. Press **Ctrl+A**, **Ctrl+C** (Cmd on a Mac) and paste the whole page into
   the dialog.

Nothing redirects, so there's no rush. If it says the code expired, reload the
`view-source:` page and paste again; each load gives a fresh code.

Home Assistant exchanges that code for its **own** refresh token (a separate
token family from the web/phone apps), then mints short-lived access tokens from
it automatically and rotates it in the background. You log in once.

**Why `view-source:`?** Auth0 only allows this client to send the code back to
`app.greenhero.com`. Loading that page starts the Green Hero web app, which
moves to another page and loses the code before you can copy it. Instead, the
links use Auth0's `web_message` mode: Auth0 answers with a small page on
`login.greenhero.com` that holds the code and never redirects. With
`prompt=none`, a browser that's already signed in gets that page immediately,
and `view-source:` shows it as copyable text.

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
