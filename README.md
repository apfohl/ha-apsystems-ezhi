# APsystems EZHI for Home Assistant

Local, cloud-free Home Assistant integration for the APsystems EZHI hybrid
microinverter/battery (EZHI ANL), built directly from the vendor's local API
document.

Polls `http://{ip}/getOutputData`, `/getAlarm` and `/getPower` every 15s over
plain HTTP on your LAN. No cloud account, no API key.

## Entities created

**Sensors**
- Battery status (idle/charging/discharging/fault/shutdown/no_communication)
- Battery state of charge / state of health / temperature
- Device temperature
- PV power + total PV energy
- Battery power + total charge/discharge energy
- On-grid power + total input/output energy
- Off-grid power + total input/output energy

**Binary sensors (diagnostic, "problem" class)**
- All 20 alarm flags from `getAlarm` (battery temp/voltage/current
  protections, device errors, PV wiring/voltage/overcurrent, off-grid
  short circuit, battery calibration, voltage recovery, etc.)

**Number**
- On-grid power limit (0–800 W), read via `getPower`, written via
  `setPower?p=...`

## Requirements

- The EZHI must be reachable on your LAN at a fixed/reserved IP.
- **Local mode must be enabled for the device in the APsystems app** before
  the on-grid power limit `number` entity's writes actually take effect.
  Without it, `setPower` calls are accepted but silently ignored by the
  device.

## Installation

### HACS (custom repository)
1. HACS → Integrations → ⋮ → Custom repositories
2. Add this repo URL, category "Integration"
3. Install "APsystems EZHI", restart Home Assistant

### Manual
Copy `custom_components/apsystems_ezhi` into your HA `config/custom_components/`
directory and restart Home Assistant.

## Setup

Settings → Devices & Services → Add Integration → "APsystems EZHI" → enter
the device's IP address.

## Notes / design choices

- Single `DataUpdateCoordinator` fetches all three endpoints together each
  cycle (15s) — they're small local calls, so a second coordinator/interval
  for the alarm endpoint wasn't worth the complexity.
- All numeric fields from the API arrive as strings (including negative
  battery/grid power values) and are cast defensively in `sensor.py`.
- No third-party dependencies beyond what Home Assistant core already
  ships (`aiohttp`, `voluptuous`).
