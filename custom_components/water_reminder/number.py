"""Interval number."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import WaterReminderConfigEntry
from .const import MAX_INTERVAL, MIN_INTERVAL
from .entity import WaterReminderEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: WaterReminderConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    async_add_entities([IntervalNumber(entry.runtime_data, "interval")])


class IntervalNumber(WaterReminderEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = MIN_INTERVAL
    _attr_native_max_value = MAX_INTERVAL
    _attr_native_step = 5
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_mode = NumberMode.BOX

    @property
    def native_value(self) -> float:
        return self.reminder.interval

    async def async_set_native_value(self, value: float) -> None:
        self.reminder.set_interval(int(value))
