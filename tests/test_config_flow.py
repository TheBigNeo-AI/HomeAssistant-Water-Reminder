"""Config and options flow tests."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.water_reminder.const import (
    CONF_ALARM_ENTITY,
    CONF_CLEAR_AFTER,
    CONF_NOTIFY_SERVICE,
    CONF_QUIET_ALARM_STATES,
    DOMAIN,
)

from .conftest import ALARM, NOTIFY


async def test_user_flow(hass: HomeAssistant, sent) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NOTIFY_SERVICE: NOTIFY,
            CONF_ALARM_ENTITY: ALARM,
            CONF_QUIET_ALARM_STATES: ["armed_night"],
            CONF_CLEAR_AFTER: 60.0,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CLEAR_AFTER] == 60
    assert result["data"][CONF_NOTIFY_SERVICE] == NOTIFY

    # Same service twice is rejected.
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NOTIFY_SERVICE: NOTIFY}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_unknown_service(hass: HomeAssistant, sent) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NOTIFY_SERVICE: "notify.does_not_exist"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_NOTIFY_SERVICE: "unknown_service"}


async def test_options_flow(hass: HomeAssistant, entry) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_QUIET_ALARM_STATES: ["armed_night", "armed_home"], CONF_CLEAR_AFTER: 0},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.quiet_alarm_states == ["armed_night", "armed_home"]
    assert entry.runtime_data.clear_after == 0
