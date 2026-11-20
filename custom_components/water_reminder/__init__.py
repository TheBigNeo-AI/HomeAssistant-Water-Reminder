"""Water Reminder: periodic hydration push notifications."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_NOTIFY_SERVICE, CONF_NOTIFY_SERVICES
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
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        # Flush a pending delayed save so a reload does not load stale state.
        await entry.runtime_data.async_save()
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, entry: WaterReminderConfigEntry) -> bool:
    """v1 had one notify service; v2 stores a list of targets."""
    if entry.version > 2:
        return False
    if entry.version == 1:

        def _upgrade(values: dict) -> dict:
            values = dict(values)
            if service := values.pop(CONF_NOTIFY_SERVICE, None):
                values[CONF_NOTIFY_SERVICES] = [service]
            return values

        options = _upgrade(entry.options)
        if options:
            options.setdefault(CONF_NOTIFY_SERVICES, _upgrade(entry.data)[CONF_NOTIFY_SERVICES])
        hass.config_entries.async_update_entry(
            entry, data=_upgrade(entry.data), options=options, version=2
        )
    return True


async def _async_reload(hass: HomeAssistant, entry: WaterReminderConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
