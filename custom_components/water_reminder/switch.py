"""Switches: reminder on/off and focus quiet (for iOS Shortcuts)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WaterReminderConfigEntry
from .entity import WaterReminderEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WaterReminderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    reminder = entry.runtime_data
    async_add_entities(
        [EnabledSwitch(reminder, "enabled"), FocusQuietSwitch(reminder, "focus_quiet")]
    )


class EnabledSwitch(WaterReminderEntity, SwitchEntity):
    _attr_name = None  # main entity, takes the device name

    @property
    def is_on(self) -> bool:
        return self.reminder.enabled

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.reminder.set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.reminder.set_enabled(False)


class FocusQuietSwitch(WaterReminderEntity, SwitchEntity):
    @property
    def is_on(self) -> bool:
        return self.reminder.focus_quiet

    async def async_turn_on(self, **kwargs: Any) -> None:
        self.reminder.set_focus_quiet(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self.reminder.set_focus_quiet(False)
