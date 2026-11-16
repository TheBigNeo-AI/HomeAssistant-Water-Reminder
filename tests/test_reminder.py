"""Behaviour tests: schedule, quiet rules, pause, clear."""

from __future__ import annotations

from datetime import timedelta

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.water_reminder.const import (
    ACTION_PAUSE_1H,
    ACTION_PAUSE_TODAY,
    CONF_NOTIFY_SERVICE,
    DOMAIN,
)

from .conftest import ALARM, NOTIFY

SWITCH = "switch.water_reminder"
FOCUS = "switch.water_reminder_quiet_focus"
INTERVAL = "number.water_reminder_interval"
STATUS = "sensor.water_reminder_status"
NEXT = "sensor.water_reminder_next_reminder"
PAUSED = "sensor.water_reminder_paused_until"


async def _advance(hass: HomeAssistant, freezer: FrozenDateTimeFactory, **delta) -> None:
    freezer.tick(timedelta(**delta))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


def _pushes(sent):
    return [c for c in sent if c["message"] != "clear_notification"]


def _clears(sent):
    return [c for c in sent if c["message"] == "clear_notification"]


async def test_entities_created(hass: HomeAssistant, entry) -> None:
    for entity_id in (SWITCH, FOCUS, INTERVAL, STATUS, NEXT, PAUSED):
        assert hass.states.get(entity_id), entity_id
    assert hass.states.get(SWITCH).state == "on"
    assert hass.states.get(INTERVAL).state == "30"
    assert hass.states.get(STATUS).state == "active"
    buttons = {s.entity_id for s in hass.states.async_all("button")}
    assert buttons == {
        "button.water_reminder_pause_1_h",
        "button.water_reminder_pause_3_h",
        "button.water_reminder_pause_today",
        "button.water_reminder_resume",
    }


async def test_push_and_clear(hass: HomeAssistant, entry, sent, freezer) -> None:
    await _advance(hass, freezer, minutes=29)
    assert sent == []
    await _advance(hass, freezer, minutes=1, seconds=1)
    assert len(_pushes(sent)) == 1
    push = _pushes(sent)[0]
    assert push["data"]["tag"] == "water_reminder"
    assert push["data"]["actions"][0]["action"] == f"{ACTION_PAUSE_1H}_{entry.entry_id}"
    assert _clears(sent) == []
    await _advance(hass, freezer, seconds=61)
    assert len(_clears(sent)) == 1
    # Next cycle.
    await _advance(hass, freezer, minutes=30)
    assert len(_pushes(sent)) == 2


async def test_interval_change_reschedules(hass: HomeAssistant, entry, sent, freezer) -> None:
    await hass.services.async_call(
        "number", "set_value", {"entity_id": INTERVAL, "value": 10}, blocking=True
    )
    await _advance(hass, freezer, minutes=10, seconds=1)
    assert len(_pushes(sent)) == 1


async def test_alarm_quiet(hass: HomeAssistant, entry, sent, freezer) -> None:
    hass.states.async_set(ALARM, "armed_night")
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "quiet_alarm"
    await _advance(hass, freezer, minutes=31)
    assert _pushes(sent) == []
    hass.states.async_set(ALARM, "armed_home")  # not quiet by default
    await _advance(hass, freezer, minutes=30)
    assert len(_pushes(sent)) == 1


async def test_focus_quiet(hass: HomeAssistant, entry, sent, freezer) -> None:
    await hass.services.async_call("switch", "turn_on", {"entity_id": FOCUS}, blocking=True)
    assert hass.states.get(STATUS).state == "quiet_focus"
    await _advance(hass, freezer, minutes=31)
    assert _pushes(sent) == []


async def test_disabled(hass: HomeAssistant, entry, sent, freezer) -> None:
    await hass.services.async_call("switch", "turn_off", {"entity_id": SWITCH}, blocking=True)
    assert hass.states.get(STATUS).state == "off"
    assert hass.states.get(NEXT).state == "unknown"
    await _advance(hass, freezer, minutes=90)
    assert sent == []


async def test_pause_button_and_expiry(hass: HomeAssistant, entry, sent, freezer) -> None:
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.water_reminder_pause_1_h"}, blocking=True
    )
    assert hass.states.get(STATUS).state == "paused"
    await _advance(hass, freezer, minutes=31)
    assert _pushes(sent) == []
    await _advance(hass, freezer, minutes=30)  # pause ends at 60 min, same as 2nd tick
    assert hass.states.get(STATUS).state == "active"
    assert hass.states.get(PAUSED).state == "unknown"
    assert len(_pushes(sent)) == 1


async def test_resume_button(hass: HomeAssistant, entry, sent, freezer) -> None:
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.water_reminder_pause_today"}, blocking=True
    )
    assert hass.states.get(STATUS).state == "paused"
    await hass.services.async_call(
        "button", "press", {"entity_id": "button.water_reminder_resume"}, blocking=True
    )
    assert hass.states.get(STATUS).state == "active"


async def test_notification_actions(hass: HomeAssistant, entry, sent) -> None:
    # Foreign actions and taps meant for another entry are ignored.
    for action in ("OTHER", ACTION_PAUSE_TODAY, f"{ACTION_PAUSE_TODAY}_other_entry"):
        hass.bus.async_fire("mobile_app_notification_action", {"action": action})
        await hass.async_block_till_done()
    assert entry.runtime_data.paused_until is None
    assert _clears(sent) == []

    hass.bus.async_fire(
        "mobile_app_notification_action", {"action": f"{ACTION_PAUSE_TODAY}_{entry.entry_id}"}
    )
    await hass.async_block_till_done()
    paused = entry.runtime_data.paused_until
    assert paused == dt_util.start_of_local_day() + timedelta(days=1)
    assert len(_clears(sent)) == 1


async def test_state_persists(hass: HomeAssistant, entry, sent, freezer) -> None:
    await hass.services.async_call(
        "number", "set_value", {"entity_id": INTERVAL, "value": 45}, blocking=True
    )
    await hass.services.async_call("switch", "turn_on", {"entity_id": FOCUS}, blocking=True)
    await _advance(hass, freezer, seconds=2)  # delayed save
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(INTERVAL).state == "45"
    assert hass.states.get(FOCUS).state == "on"


async def test_reload_keeps_unsaved_state(hass: HomeAssistant, entry, sent) -> None:
    """A reload right after a change must not load stale state from disk."""
    await hass.services.async_call("switch", "turn_on", {"entity_id": FOCUS}, blocking=True)
    assert await hass.config_entries.async_reload(entry.entry_id)  # within the save delay
    await hass.async_block_till_done()
    assert hass.states.get(FOCUS).state == "on"


async def test_unload(hass: HomeAssistant, entry, sent, freezer) -> None:
    assert await hass.config_entries.async_unload(entry.entry_id)
    await _advance(hass, freezer, minutes=31)
    assert sent == []


async def test_without_alarm(hass: HomeAssistant, sent, freezer) -> None:
    e = MockConfigEntry(domain=DOMAIN, unique_id=NOTIFY, data={CONF_NOTIFY_SERVICE: NOTIFY})
    e.add_to_hass(hass)
    assert await hass.config_entries.async_setup(e.entry_id)
    await hass.async_block_till_done()
    await _advance(hass, freezer, minutes=31)
    assert len(_pushes(sent)) == 1
