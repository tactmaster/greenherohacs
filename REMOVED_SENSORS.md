# Removed sensors

Sensors that were added in v0.2.6 and removed in v0.2.7 because Green Hero
returns no data for them. Checked against the integration's diagnostics on a
live install (place in SE3) on 2026-10-17.

If Green Hero starts filling these fields, a sensor can come back by restoring
its `GreenHeroSensorDescription` in `sensor.py` (see git history for v0.2.6,
commit `9be1560`) and its name in `strings.json` / `translations/en.json`.
Check the raw data first: Settings → Devices & services → Green Hero → ⋮ →
*Download diagnostics*.

## Live power (from `/v0/battery-status`)

Green Hero only fills `soc` and `power`. Every other field is `null`:

```json
{"soc": 78.0, "power": -3.909,
 "grid_import_power": null, "grid_export_power": null,
 "load_power": null, "production_power": null,
 "sources": {"soc": "balans.fcr.flextools.733", "power": "balans.fcr.flextools.90"}}
```

| Sensor | Field |
|---|---|
| Solar power | `production_power` |
| House power | `load_power` |
| Grid import power | `grid_import_power` |
| Grid export power | `grid_export_power` |

The `sources` values suggest battery data comes from the battery's grid-balancing
(FCR) service, not from a meter, which would explain why there are no meter
readings here.

## Today (from `/v0/overview/day`)

Every flow in the day total is `null`, for both `currency` and `energy`:

```json
{"P_B": null, "P_L": null, "P_G": null, "B_L": null, "B_G": null, "G_L": null, "L": null}
```

The integration no longer requests the day overview at all.

| Sensor | Value used |
|---|---|
| Cost today | `G_L` (currency) |
| Energy today | `L`, or `G_L + P_L + B_L` |
| Grid import today | `G_L` (energy) |
| Grid export today | `P_G + B_G` (energy) |
| Solar production today | `P_L + P_B + P_G` (energy) |
| Export earnings today | `P_G + B_G` (currency) |

The month overview does contain a per-day list (`days`, e.g. 17 entries up to
the 17th), so a "yesterday" or "latest day" sensor could be built from that
instead if it's wanted.

## Solar and battery energy (from `/v0/overview/lifetime`)

Solar-to-home and every battery flow are `null` in every period, including all
27 months of lifetime data. Only grid import (`G_L`), export (`P_G`) and total
use (`L`) are reported.

| Sensor | Flows needed |
|---|---|
| Solar production lifetime | `P_L + P_B + P_G` |
| Battery charged lifetime | `P_B` |
| Battery discharged lifetime | `B_L + B_G` |

## Other observations (sensors kept)

- **Cost this month = Cost this year (621.63 SEK).** In the year data, grid cost
  (`G_L`) is `null` for every month before October 2026, so the year total only
  covers this month. Export earnings do go back further (1,612.88 SEK for the
  year), so this is Green Hero's data, not a parsing problem.
- **Energy lifetime = Grid import lifetime.** Green Hero's total use (`L`)
  equals grid import (`G_L`) because it doesn't report solar or battery
  supplying the home. Both are kept; use *Grid import lifetime* in the Energy
  dashboard.
- **Cheapest hour today** is really the cheapest 15-minute slot.
