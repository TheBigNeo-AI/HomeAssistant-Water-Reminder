"""Reminder engine: scheduling, quiet rules, notifications and persisted state."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.event import (
    async_call_later,
    async_track_point_in_utc_time,
    async_track_state_change_event,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    ACTION_OK,
    ACTION_PAUSE_1H,
    ACTION_PAUSE_3H,
    ACTION_PAUSE_TODAY,
    CONF_ALARM_ENTITY,
    CONF_CLEAR_AFTER,
    CONF_MESSAGE,
    CONF_NOTIFY_SERVICES,
    CONF_QUIET_ALARM_STATES,
    CONF_TITLE,
    DEFAULT_CLEAR_AFTER,
    DEFAULT_INTERVAL,
    DEFAULT_QUIET_ALARM_STATES,
    DOMAIN,
    NOTIFICATION_TAG,
    STATUS_ACTIVE,
    STATUS_OFF,
    STATUS_PAUSED,
    STATUS_QUIET_ALARM,
    STATUS_QUIET_FOCUS,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


# Action button labels; OK comes first so the Watch shows a way to dismiss.
ACTION_LABELS: dict[str, dict[str, str]] = {
    "de": {
        ACTION_OK: "OK",
        ACTION_PAUSE_1H: "1 h pausieren",
        ACTION_PAUSE_3H: "3 h pausieren",
        ACTION_PAUSE_TODAY: "Heute pausieren",
    },
    "en": {
        ACTION_OK: "OK",
        ACTION_PAUSE_1H: "Pause for 1 h",
        ACTION_PAUSE_3H: "Pause for 3 h",
        ACTION_PAUSE_TODAY: "Pause for today",
    },
}


def action_labels(language: str) -> dict[str, str]:
    """Return the action labels for the instance language."""
    return ACTION_LABELS["de" if language.startswith("de") else "en"]


def default_texts(language: str) -> tuple[str, str]:
    """Return default (title, message) for the instance language."""
    if language.startswith("de"):
        return "💧 Trinken", "Zeit für ein Glas Wasser."
    return "💧 Drink", "Time for a glass of water."


class WaterReminder:
    """Holds the state of one reminder and sends the notifications."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{DOMAIN}.{entry.entry_id}"
        )
        self.enabled = True
        self.interval = DEFAULT_INTERVAL
        self.focus_quiet = False
        self.paused_until: datetime | None = None
        self.next_push: datetime | None = None
        self._listeners: list[CALLBACK_TYPE] = []
        self._unsub_tick: CALLBACK_TYPE | None = None
        self._unsub_clear: CALLBACK_TYPE | None = None
        self._unsub_event: CALLBACK_TYPE | None = None
        self._unsub_alarm: CALLBACK_TYPE | None = None
        self._unsub_pause_end: CALLBACK_TYPE | None = None

    # ----- options -----------------------------------------------------------

    @property
    def _opts(self) -> dict[str, Any]:
        # The options flow saves the full set of settings, so once options
        # exist they replace the setup data (a cleared field must stay cleared).
        if self.entry.options:
            return {
                CONF_NOTIFY_SERVICES: self.entry.data[CONF_NOTIFY_SERVICES],
                **self.entry.options,
            }
        return dict(self.entry.data)

    def _action(self, base: str) -> str:
        """Action id unique to this entry, so a tap only pauses this reminder."""
        return f"{base}_{self.entry.entry_id}"

    @property
    def notify_services(self) -> list[str]:
        return list(self._opts[CONF_NOTIFY_SERVICES])

    @property
    def alarm_entity(self) -> str | None:
        return self._opts.get(CONF_ALARM_ENTITY) or None

    @property
    def quiet_alarm_states(self) -> list[str]:
        return self._opts.get(CONF_QUIET_ALARM_STATES, DEFAULT_QUIET_ALARM_STATES)

    @property
    def clear_after(self) -> int:
        return int(self._opts.get(CONF_CLEAR_AFTER, DEFAULT_CLEAR_AFTER))

    # ----- lifecycle ---------------------------------------------------------

    async def async_start(self) -> None:
        """Load persisted state, listen for notification actions, schedule."""
        if data := await self._store.async_load():
            self.enabled = data.get("enabled", True)
            self.interval = data.get("interval", DEFAULT_INTERVAL)
            self.focus_quiet = data.get("focus_quiet", False)
            if paused := data.get("paused_until"):
                self.paused_until = dt_util.parse_datetime(paused)
        self._unsub_event = self.hass.bus.async_listen(
            "mobile_app_notification_action", self._handle_action
        )
        if self.alarm_entity:
            self._unsub_alarm = async_track_state_change_event(
                self.hass, self.alarm_entity, self._handle_alarm_change
            )
        self._track_pause_end()
        self._schedule()

    @callback
    def async_stop(self) -> None:
        """Cancel timers and listeners."""
        for unsub in (
            self._unsub_tick,
            self._unsub_clear,
            self._unsub_event,
            self._unsub_alarm,
            self._unsub_pause_end,
        ):
            if unsub:
                unsub()
        self._unsub_tick = self._unsub_clear = self._unsub_event = None
        self._unsub_alarm = self._unsub_pause_end = None

    async def async_save(self) -> None:
        """Write state now (replaces a pending delayed save)."""
        await self._store.async_save(self._data())

    @callback
    def async_add_listener(self, update: CALLBACK_TYPE) -> Callable[[], None]:
        """Register an entity update callback."""
        self._listeners.append(update)
        return lambda: self._listeners.remove(update)

    @callback
    def _handle_alarm_change(self, _event: Event) -> None:
        self._refresh()

    @callback
    def _refresh(self) -> None:
        """Tell entities to re-read state (status may have changed)."""
        for update in list(self._listeners):
            update()

    @callback
    def _changed(self) -> None:
        self._store.async_delay_save(self._data, 1)
        self._refresh()

    @callback
    def _track_pause_end(self) -> None:
        """Refresh entities when a pause runs out."""
        if self._unsub_pause_end:
            self._unsub_pause_end()
            self._unsub_pause_end = None
        if self.paused_until and self.paused_until > dt_util.utcnow():
            self._unsub_pause_end = async_track_point_in_utc_time(
                self.hass, self._handle_pause_end, self.paused_until
            )

    @callback
    def _handle_pause_end(self, _now: datetime) -> None:
        self._unsub_pause_end = None
        self.paused_until = None
        self._changed()

    def _data(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "interval": self.interval,
            "focus_quiet": self.focus_quiet,
            "paused_until": self.paused_until.isoformat() if self.paused_until else None,
        }

    # ----- setters (entities, buttons, notification actions) ----------------

    @callback
    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self._schedule()
        self._changed()

    @callback
    def set_interval(self, minutes: int) -> None:
        self.interval = minutes
        self._schedule()
        self._changed()

    @callback
    def set_focus_quiet(self, quiet: bool) -> None:
        self.focus_quiet = quiet
        self._changed()

    @callback
    def pause(self, hours: float | None) -> None:
        """Pause for some hours, or for the rest of today when hours is None."""
        if hours is None:
            self.paused_until = dt_util.start_of_local_day() + timedelta(days=1)
        else:
            self.paused_until = dt_util.utcnow() + timedelta(hours=hours)
        self._track_pause_end()
        self._changed()

    @callback
    def resume(self) -> None:
        self.paused_until = None
        self._track_pause_end()
        self._changed()

    # ----- rules -------------------------------------------------------------

    @property
    def status(self) -> str:
        """Why the next push would (not) be sent."""
        if not self.enabled:
            return STATUS_OFF
        if self.paused_until and dt_util.utcnow() < self.paused_until:
            return STATUS_PAUSED
        alarm = self.hass.states.get(self.alarm_entity) if self.alarm_entity else None
        if alarm and alarm.state in self.quiet_alarm_states:
            return STATUS_QUIET_ALARM
        if self.focus_quiet:
            return STATUS_QUIET_FOCUS
        return STATUS_ACTIVE

    # ----- scheduling --------------------------------------------------------

    def _next_slot(self, after: datetime) -> datetime:
        """Next push time strictly after `after`, aligned to local midnight.

        With 30 min that is hh:00 and hh:30; intervals that do not divide a day
        restart at midnight, so the last slot of a day can be shorter.
        """
        midnight = dt_util.start_of_local_day(dt_util.as_local(after))
        elapsed = dt_util.as_local(after) - midnight
        slot = midnight + timedelta(minutes=self.interval) * (
            elapsed // timedelta(minutes=self.interval) + 1
        )
        return dt_util.as_utc(min(slot, midnight + timedelta(days=1)))

    @callback
    def _schedule(self, after: datetime | None = None) -> None:
        if self._unsub_tick:
            self._unsub_tick()
            self._unsub_tick = None
        self.next_push = None
        if self.enabled:
            self.next_push = self._next_slot(after or dt_util.utcnow())
            self._unsub_tick = async_track_point_in_utc_time(
                self.hass, self._handle_tick, self.next_push
            )

    async def _handle_tick(self, now: datetime) -> None:
        self._unsub_tick = None
        # Never schedule the slot that just fired again, even if the timer was early.
        self._schedule(max(now, dt_util.utcnow(), self.next_push or now))
        self._refresh()
        if self.status == STATUS_ACTIVE:
            await self.async_send()

    # ----- notifications -----------------------------------------------------

    async def async_test(self) -> None:
        """Send a reminder now, unless a quiet rule would suppress it."""
        if (status := self.status) != STATUS_ACTIVE:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key=f"test_{status}"
            )
        await self.async_send()

    async def async_send(self) -> None:
        """Send the reminder and schedule its removal."""
        default_title, default_message = default_texts(self.hass.config.language)
        await self._notify(
            {
                "title": self._opts.get(CONF_TITLE) or default_title,
                "message": self._opts.get(CONF_MESSAGE) or default_message,
                "data": {
                    "tag": NOTIFICATION_TAG,
                    "group": NOTIFICATION_TAG,
                    "actions": [
                        {"action": self._action(action), "title": title}
                        for action, title in action_labels(self.hass.config.language).items()
                    ],
                },
            }
        )
        if self._unsub_clear:
            self._unsub_clear()
            self._unsub_clear = None
        if self.clear_after > 0:
            self._unsub_clear = async_call_later(self.hass, self.clear_after, self._handle_clear)

    async def _handle_clear(self, _now: datetime) -> None:
        self._unsub_clear = None
        await self.async_clear()

    async def async_clear(self) -> None:
        await self._notify({"message": "clear_notification", "data": {"tag": NOTIFICATION_TAG}})

    async def _notify(self, data: dict[str, Any]) -> None:
        for target in self.notify_services:
            domain, _, service = target.partition(".")
            try:
                await self.hass.services.async_call(domain, service, data, blocking=True)
            except (HomeAssistantError, ValueError) as err:
                _LOGGER.warning("Sending via %s failed: %s", target, err)

    async def _handle_action(self, event: Event) -> None:
        action = event.data.get("action")
        hours = {
            self._action(ACTION_PAUSE_1H): 1,
            self._action(ACTION_PAUSE_3H): 3,
            self._action(ACTION_PAUSE_TODAY): None,
        }
        if action in hours:
            self.pause(hours[action])
        elif action != self._action(ACTION_OK):
            return
        await self.async_clear()
