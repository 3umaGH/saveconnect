"""Constants for the SaveConnect integration."""

DOMAIN = "saveconnect"

CONF_HOST = "host"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_SCAN_INTERVAL = 30

# Register map requested from the device, encoded verbatim into the /mread
# query string (values here are register counts expected by the device, not
# the readings themselves).
QUERY_REGISTERS = {
    "3021": 1,
    "11000": 7,
    "11100": 6,
    "11200": 6,
    "12100": 8,
    "12135": 1,
    "12150": 6,
    "12160": 6,
    "12400": 2,
    "12542": 1,
    "12543": 1,
    # Control registers (select / number entities)
    "1100": 1,
    "1101": 1,
    "1102": 1,
    "1103": 1,
    "1104": 1,
    "1130": 1,
    "1160": 1,
    "1161": 1,
    "2000": 1,
    "2504": 1,
    "16100": 1,
    "7004": 1,
    "7005": 1,
}

# Sensor register keys
KEY_OAT = "12101"  # Outdoor air temperature
KEY_SAT = "12102"  # Supply air temperature
KEY_OHT = "12107"  # Overheat temperature sensor
KEY_EAT = "12543"  # Extract air temperature
KEY_HUMIDITY = "12135"  # Humidity
KEY_SUPPLY_FAN_RPM = "12400"  # Supply air fan level
KEY_EXTRACT_FAN_RPM = "12401"  # Extract air fan level

# Control registers
KEY_USER_MODE_ACTIVE = "1160"  # read-only: currently active user mode, 0-indexed
KEY_USER_MODE_REQUEST = "1161"  # write: requested user mode, 1-indexed
KEY_TEMPERATURE_SETPOINT = "2000"  # value is degrees C * 10
KEY_ECO_MODE = "2504"
# Likely a one-time setup-wizard-complete flag. Captured real traffic shows
# the web UI always writes this as literal 0 on every mode-affecting write,
# regardless of its current value - so we do the same rather than preserving
# whatever we last read.
KEY_UNKNOWN_16100 = "16100"

# Registers the SaveConnect web UI always re-submits together whenever any
# one of them changes (confirmed from captured mwrite traffic). 1130 and 2000
# and 2504 are sent with their current cached value; 16100 is always 0.
MODE_WRITE_BUNDLE_KEYS = ("1130", KEY_USER_MODE_REQUEST, KEY_TEMPERATURE_SETPOINT, KEY_ECO_MODE)

# Register 1160 (read/status) is 0-indexed: confirmed against the
# systemair_modbus integration's SaveModel.STATUS_MODE_TO_LABEL, which
# targets the same VSR300 register map over native Modbus.
STATUS_USER_MODES = {
    0: "Auto",
    1: "Manual",
    2: "Crowded",
    3: "Refresh",
    4: "Fireplace",
    5: "Away",
    6: "Holiday",
}

# Register 1161 (write/request) is 1-indexed, matching the <select id="1161">
# options in the web UI and SaveModel.COMMAND_MODE_OPTIONS.
REQUEST_USER_MODES = {
    "Auto": 1,
    "Manual": 2,
    "Crowded": 3,
    "Refresh": 4,
    "Fireplace": 5,
    "Away": 6,
    "Holiday": 7,
}

# Timed "boost" registers: writing a duration here atomically switches to
# that mode for the given duration, then reverts automatically. Units
# confirmed against systemair_modbus's SaveModel.REGISTERS (per-register
# `unit` field) - note Crowded and Away are HOURS, not minutes.
KEY_BOOST_HOLIDAY = "1100"  # days
KEY_BOOST_AWAY = "1101"  # hours
KEY_BOOST_FIREPLACE = "1102"  # minutes
KEY_BOOST_REFRESH = "1103"  # minutes
KEY_BOOST_CROWDED = "1104"  # hours

# Remaining time to filter replacement: a 32-bit seconds value split across
# two 16-bit registers, low word first (7004 = low, 7005 = high). Confirmed
# against a live sample: 7004=48407, 7005=123 -> ~93.9 days (~3 months),
# matching the device's own displayed estimate.
KEY_FILTER_TIME_REMAINING_LOW = "7004"
KEY_FILTER_TIME_REMAINING_HIGH = "7005"
