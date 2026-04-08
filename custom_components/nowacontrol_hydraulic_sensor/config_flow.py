"""Config flow for nowaControl Hydraulic Sensor."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PATH
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_AUTO_INSTALL_QUIRK,
    CONF_SHOW_NOTIFICATIONS,
    DEFAULT_AUTO_INSTALL_QUIRK,
    DEFAULT_CUSTOM_QUIRKS_DIR,
    DEFAULT_SHOW_NOTIFICATIONS,
    DOMAIN,
    TITLE,
)


def _config_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_PATH, default=defaults[CONF_PATH]): str,
            vol.Required(
                CONF_AUTO_INSTALL_QUIRK,
                default=defaults[CONF_AUTO_INSTALL_QUIRK],
            ): bool,
            vol.Required(
                CONF_SHOW_NOTIFICATIONS,
                default=defaults[CONF_SHOW_NOTIFICATIONS],
            ): bool,
        }
    )


class NowaControlHydraulicSensorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for nowaControl Hydraulic Sensor."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "NowaControlHydraulicSensorOptionsFlow":
        """Return the options flow."""
        return NowaControlHydraulicSensorOptionsFlow(config_entry)

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial setup flow."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        defaults = {
            CONF_PATH: DEFAULT_CUSTOM_QUIRKS_DIR,
            CONF_AUTO_INSTALL_QUIRK: DEFAULT_AUTO_INSTALL_QUIRK,
            CONF_SHOW_NOTIFICATIONS: DEFAULT_SHOW_NOTIFICATIONS,
        }

        if user_input is not None:
            return self.async_create_entry(title=TITLE, data=user_input)

        return self.async_show_form(step_id="user", data_schema=_config_schema(defaults))

    async def async_step_import(self, import_config: dict[str, Any]) -> FlowResult:
        """Import settings from YAML once for backward compatibility."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=TITLE, data=import_config)


class NowaControlHydraulicSensorOptionsFlow(config_entries.OptionsFlow):
    """Handle nowaControl Hydraulic Sensor options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Manage the integration options."""
        defaults = {
            CONF_PATH: self.config_entry.options.get(
                CONF_PATH,
                self.config_entry.data.get(CONF_PATH, DEFAULT_CUSTOM_QUIRKS_DIR),
            ),
            CONF_AUTO_INSTALL_QUIRK: self.config_entry.options.get(
                CONF_AUTO_INSTALL_QUIRK,
                self.config_entry.data.get(
                    CONF_AUTO_INSTALL_QUIRK, DEFAULT_AUTO_INSTALL_QUIRK
                ),
            ),
            CONF_SHOW_NOTIFICATIONS: self.config_entry.options.get(
                CONF_SHOW_NOTIFICATIONS,
                self.config_entry.data.get(
                    CONF_SHOW_NOTIFICATIONS, DEFAULT_SHOW_NOTIFICATIONS
                ),
            ),
        }

        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(step_id="init", data_schema=_config_schema(defaults))
