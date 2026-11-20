"""Test, pause and resume buttons."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WaterReminderConfigEntry
from .entity import WaterReminderEntity
from .reminder import WaterReminder

# key -> hours (None = rest of today, 0 = resume)
BUTTONS: dict[str, float | None] = {
    "pause_1h": 1,
    "pause_3h": 3,
    "pause_today": None,
    "resume": 0,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WaterReminderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    reminder = entry.runtime_data
    async_add_entities(
        [
            TestButton(reminder, "test"),
            *(PauseButton(reminder, key, hours) for key, hours in BUTTONS.items()),
        ]
    )


class TestButton(WaterReminderEntity, ButtonEntity):
    """Send a reminder now; refused (with the reason) while quiet, paused or off."""

    async def async_press(self) -> None:
        await self.reminder.async_test()


class PauseButton(WaterReminderEntity, ButtonEntity):
    def __init__(self, reminder: WaterReminder, key: str, hours: float | None) -> None:
        super().__init__(reminder, key)
        self._hours = hours

    async def async_press(self) -> None:
        if self._hours == 0:
            self.reminder.resume()
        else:
            self.reminder.pause(self._hours)
