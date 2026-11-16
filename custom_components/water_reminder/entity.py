"""Base entity for Water Reminder."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .reminder import WaterReminder


class WaterReminderEntity(Entity):
    """Entity bound to one reminder; re-renders on every reminder change."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, reminder: WaterReminder, key: str) -> None:
        self.reminder = reminder
        self._attr_translation_key = key
        self._attr_unique_id = f"{reminder.entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, reminder.entry.entry_id)},
            name=reminder.entry.title,
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_added_to_hass(self) -> None:
        self.async_on_remove(self.reminder.async_add_listener(self.async_write_ha_state))
