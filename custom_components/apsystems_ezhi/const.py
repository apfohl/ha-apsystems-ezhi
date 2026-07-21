"""Constants for the APsystems EZHI integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "apsystems_ezhi"

CONF_HOST = "host"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=15)
ALARM_SCAN_INTERVAL = timedelta(seconds=60)

# Battery status codes returned by getOutputData -> "batS"
BATTERY_STATUS = {
    "1": "idle",
    "2": "charging",
    "3": "discharging",
    "4": "fault",
    "5": "shutdown",
    "6": "no_communication",
}

# Alarm keys returned by getAlarm, mapped to a human-readable name.
# "0" == no alarm, anything else == active. We treat any non-"0" value as "on".
ALARMS = {
    "BatHTP": "Battery High Temperature Protection",
    "BatLTP": "Battery Low Temperature Protection",
    "BatCE": "Battery Communication Error",
    "BatHV": "Battery Overvoltage",
    "BatLV": "Battery Undervoltage",
    "BatHI": "Battery Overcurrent",
    "BatE": "Battery Error",
    "DTP": "Device Temperature Protection",
    "EE": "Device Error",
    "SBS": "Battery Shutdown",
    "ACA": "AC Abnormal",
    "OfOI": "Off-grid Overcurrent",
    "PvHV": "PV High Voltage",
    "PvOC": "PV Overcurrent",
    "IRDE": "IRD Error",
    "PVWE": "PV Wiring Error",
    "OfGS": "Off-grid Short Circuit",
    "VRP": "Voltage Reset Protection",
    # Meaning unconfirmed - not in the vendor's local API manual as of this
    # writing, seen on newer firmware. Update these once confirmed.
    "BCC": "BCC (unconfirmed)",
    "BCI": "BCI (unconfirmed)",
}

MIN_ON_GRID_POWER = 0
MAX_ON_GRID_POWER = 800
