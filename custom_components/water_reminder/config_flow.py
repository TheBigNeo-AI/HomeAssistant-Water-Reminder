"""Config and options flow for Water Reminder."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    ALARM_STATES,
    CONF_ALARM_ENTITY,
    CONF_CLEAR_AFTER,
    CONF_MESSAGE,
    CONF_NOTIFY_SERVICE,
    CONF_QUIET_ALARM_STATES,
    CONF_TITLE,
    DEFAULT_CLEAR_AFTER,
    DEFAULT_QUIET_ALARM_STATES,
    DOMAIN,
)

MOBILE_APP_PREFIX = "mobile_app_"


def _notify_services(hass: HomeAssistant) -> list[str]:
    """Mobile app notify services (tag, actions and clearing need the companion app)."""
    names = sorted(hass.services.async_services_for_domain("notify"))
    return [f"notify.{n}" for n in names if n.startswith(MOBILE_APP_PREFIX)]


def _schema(hass: HomeAssistant, values: dict[str, Any], with_notify: bool) -> vol.Schema:
    fields: dict[Any, Any] = {}
    if with_notify:
        fields[
            vol.Required(
                CONF_NOTIFY_SERVICE, default=values.get(CONF_NOTIFY_SERVICE, vol.UNDEFINED)
            )
        ] = selector.SelectSelector(
            selector.SelectSelectorConfig(options=_notify_services(hass), custom_value=True)
        )
    alarm = values.get(CONF_ALARM_ENTITY)
    fields[vol.Optional(CONF_ALARM_ENTITY, description={"suggested_value": alarm})] = (
        selector.EntitySelector(selector.EntitySelectorConfig(domain="alarm_control_panel"))
    )
    fields[
        vol.Optional(
            CONF_QUIET_ALARM_STATES,
            default=values.get(CONF_QUIET_ALARM_STATES, DEFAULT_QUIET_ALARM_STATES),
        )
    ] = selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=ALARM_STATES,
            multiple=True,
            translation_key=CONF_QUIET_ALARM_STATES,
        )
    )
    fields[
        vol.Optional(CONF_CLEAR_AFTER, default=values.get(CONF_CLEAR_AFTER, DEFAULT_CLEAR_AFTER))
    ] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0, max=900, step=10, unit_of_measurement="s", mode=selector.NumberSelectorMode.BOX
        )
    )
    for key in (CONF_TITLE, CONF_MESSAGE):
        fields[vol.Optional(key, description={"suggested_value": values.get(key)})] = (
            selector.TextSelector()
        )
    return vol.Schema(fields)


def _clean(user_input: dict[str, Any]) -> dict[str, Any]:
    data = {k: v for k, v in user_input.items() if v not in (None, "")}
    if CONF_CLEAR_AFTER in data:
        data[CONF_CLEAR_AFTER] = int(data[CONF_CLEAR_AFTER])
    return data


class WaterReminderConfigFlow(ConfigFlow, domain=DOMAIN):
    """Set up a reminder for one notify target."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = _clean(user_input)
            service = data[CONF_NOTIFY_SERVICE]
            domain, _, name = service.partition(".")
            if domain != "notify" or not self.hass.services.has_service(domain, name):
                errors[CONF_NOTIFY_SERVICE] = "unknown_service"
            elif not name.startswith(MOBILE_APP_PREFIX):
                errors[CONF_NOTIFY_SERVICE] = "not_mobile_app"
            else:
                await self.async_set_unique_id(service)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Water Reminder", data=data)
        return self.async_show_form(
            step_id="user",
            data_schema=_schema(self.hass, user_input or {}, with_notify=True),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return WaterReminderOptionsFlow()


class WaterReminderOptionsFlow(OptionsFlow):
    """Change alarm, clear delay and texts."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=_clean(user_input))
        values = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_schema(self.hass, values, with_notify=False)
        )
