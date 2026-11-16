"""Fixtures for Water Reminder tests."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant, ServiceCall
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.water_reminder.const import CONF_ALARM_ENTITY, CONF_NOTIFY_SERVICE, DOMAIN

ALARM = "alarm_control_panel.home_alarm"
NOTIFY = "notify.mobile_app_test_iphone"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in all tests."""


@pytest.fixture
def sent(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Register a fake mobile_app notify service and record its calls."""
    calls: list[dict[str, Any]] = []

    async def _handle(call: ServiceCall) -> None:
        calls.append(dict(call.data))

    hass.services.async_register("notify", "mobile_app_test_iphone", _handle)
    return calls


@pytest.fixture
async def entry(hass: HomeAssistant, sent: list[dict[str, Any]]) -> MockConfigEntry:
    """Set up one reminder with an alarm panel."""
    hass.states.async_set(ALARM, "disarmed")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Water Reminder",
        unique_id=NOTIFY,
        data={CONF_NOTIFY_SERVICE: NOTIFY, CONF_ALARM_ENTITY: ALARM},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry
