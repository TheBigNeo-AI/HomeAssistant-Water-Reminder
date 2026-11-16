"""Sensors: status, next push, paused until."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WaterReminderConfigEntry
from .const import STATUSES
from .entity import WaterReminderEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WaterReminderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    reminder = entry.runtime_data
    async_add_entities(
        [
            StatusSensor(reminder, "status"),
            NextPushSensor(reminder, "next_push"),
            PausedUntilSensor(reminder, "paused_until"),
        ]
    )


class StatusSensor(WaterReminderEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUSES

    @property
    def native_value(self) -> str:
        return self.reminder.status


class NextPushSensor(WaterReminderEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        return self.reminder.next_push


class PausedUntilSensor(WaterReminderEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> datetime | None:
        return self.reminder.paused_until
