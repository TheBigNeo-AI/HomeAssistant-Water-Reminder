"""Constants for Water Reminder."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "water_reminder"

CONF_NOTIFY_SERVICE: Final = "notify_service"
CONF_ALARM_ENTITY: Final = "alarm_entity"
CONF_QUIET_ALARM_STATES: Final = "quiet_alarm_states"
CONF_CLEAR_AFTER: Final = "clear_after"
CONF_TITLE: Final = "title"
CONF_MESSAGE: Final = "message"

DEFAULT_QUIET_ALARM_STATES: Final = ["armed_night"]
DEFAULT_CLEAR_AFTER: Final = 60  # seconds, 0 = keep notification
DEFAULT_INTERVAL: Final = 30  # minutes
MIN_INTERVAL: Final = 5
MAX_INTERVAL: Final = 240

ALARM_STATES: Final = [
    "armed_home",
    "armed_away",
    "armed_night",
    "armed_vacation",
    "armed_custom_bypass",
]

NOTIFICATION_TAG: Final = "water_reminder"

# Actionable notification ids (event mobile_app_notification_action).
ACTION_PAUSE_1H: Final = "WATER_REMINDER_PAUSE_1H"
ACTION_PAUSE_3H: Final = "WATER_REMINDER_PAUSE_3H"
ACTION_PAUSE_TODAY: Final = "WATER_REMINDER_PAUSE_TODAY"

# Status sensor values.
STATUS_OFF: Final = "off"
STATUS_ACTIVE: Final = "active"
STATUS_PAUSED: Final = "paused"
STATUS_QUIET_ALARM: Final = "quiet_alarm"
STATUS_QUIET_FOCUS: Final = "quiet_focus"
STATUSES: Final = [
    STATUS_OFF,
    STATUS_ACTIVE,
    STATUS_PAUSED,
    STATUS_QUIET_ALARM,
    STATUS_QUIET_FOCUS,
]
