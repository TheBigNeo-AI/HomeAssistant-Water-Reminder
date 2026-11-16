"""Config and options flow tests."""

from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.water_reminder.const import (
    CONF_ALARM_ENTITY,
    CONF_CLEAR_AFTER,
    CONF_NOTIFY_SERVICES,
    CONF_QUIET_ALARM_STATES,
    CONF_TITLE,
    DOMAIN,
)

from .conftest import ALARM, NOTIFY

IPAD = "notify.mobile_app_test_ipad"


async def _start(hass: HomeAssistant):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def test_user_flow(hass: HomeAssistant, sent) -> None:
    hass.services.async_register("notify", "mobile_app_test_ipad", lambda call: None)
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["description_placeholders"]["default_title"] == "💧 Drink"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NOTIFY_SERVICES: [NOTIFY, IPAD],
            CONF_ALARM_ENTITY: ALARM,
            CONF_QUIET_ALARM_STATES: ["armed_night"],
            CONF_CLEAR_AFTER: 60.0,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_CLEAR_AFTER] == 60
    assert result["data"][CONF_NOTIFY_SERVICES] == [IPAD, NOTIFY]

    # The same set of targets twice is rejected.
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NOTIFY_SERVICES: [NOTIFY, IPAD]}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_unknown_service(hass: HomeAssistant, sent) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NOTIFY_SERVICES: [NOTIFY, "notify.does_not_exist"]}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_NOTIFY_SERVICES: "unknown_service"}


async def test_no_service(hass: HomeAssistant, sent) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NOTIFY_SERVICES: []}
    )
    assert result["errors"] == {CONF_NOTIFY_SERVICES: "no_service"}


async def test_non_mobile_service_rejected(hass: HomeAssistant, sent) -> None:
    hass.services.async_register("notify", "telegram", lambda call: None)
    result = await _start(hass)
    schema_options = result["data_schema"].schema[CONF_NOTIFY_SERVICES].config["options"]
    assert schema_options == [NOTIFY]
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_NOTIFY_SERVICES: ["notify.telegram"]}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_NOTIFY_SERVICES: "not_mobile_app"}


async def test_options_clear_alarm_and_texts(hass: HomeAssistant, sent) -> None:
    """Fields set during setup can be cleared again in the options."""
    hass.states.async_set(ALARM, "armed_night")
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={CONF_NOTIFY_SERVICES: [NOTIFY], CONF_ALARM_ENTITY: ALARM, CONF_TITLE: "Old"},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.alarm_entity == ALARM

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NOTIFY_SERVICES: [NOTIFY],
            CONF_QUIET_ALARM_STATES: ["armed_night"],
            CONF_CLEAR_AFTER: 60,
            CONF_TITLE: "",
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    reminder = entry.runtime_data
    assert reminder.alarm_entity is None
    assert reminder.notify_services == [NOTIFY]
    assert reminder.status == "active"
    assert CONF_TITLE not in reminder._opts


async def test_options_flow(hass: HomeAssistant, entry) -> None:
    hass.services.async_register("notify", "mobile_app_test_ipad", lambda call: None)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_NOTIFY_SERVICES: [NOTIFY, IPAD],
            CONF_QUIET_ALARM_STATES: ["armed_night", "armed_home"],
            CONF_CLEAR_AFTER: 0,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.runtime_data.notify_services == [IPAD, NOTIFY]
    assert entry.runtime_data.quiet_alarm_states == ["armed_night", "armed_home"]
    assert entry.runtime_data.clear_after == 0
