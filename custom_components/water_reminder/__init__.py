"""Water Reminder: periodic hydration push notifications."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .reminder import WaterReminder

PLATFORMS = [Platform.BUTTON, Platform.NUMBER, Platform.SENSOR, Platform.SWITCH]

type WaterReminderConfigEntry = ConfigEntry[WaterReminder]


async def async_setup_entry(hass: HomeAssistant, entry: WaterReminderConfigEntry) -> bool:
    """Set up Water Reminder from a config entry."""
    reminder = WaterReminder(hass, entry)
    await reminder.async_start()
    entry.runtime_data = reminder
    entry.async_on_unload(reminder.async_stop)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: WaterReminderConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload(hass: HomeAssistant, entry: WaterReminderConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
