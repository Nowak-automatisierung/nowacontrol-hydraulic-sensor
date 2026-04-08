"""Home Assistant helper integration for nowaControl Hydraulic Sensor."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.const import CONF_PATH
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv

from .const import DEFAULT_CUSTOM_QUIRKS_DIR, DOMAIN
from .services import async_register_services, quirk_exists

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_PATH, default=DEFAULT_CUSTOM_QUIRKS_DIR): cv.string,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the helper integration via YAML."""
    domain_config = config.get(DOMAIN, {})
    custom_quirks_path = domain_config.get(CONF_PATH, DEFAULT_CUSTOM_QUIRKS_DIR)

    await async_register_services(hass, custom_quirks_path)

    if not quirk_exists(hass, custom_quirks_path):
        persistent_notification.async_create(
            hass,
            (
                "nowaControl Hydraulic Sensor ist installiert, aber der ZHA-Quirk "
                "liegt noch nicht unter /config/custom_zha_quirks/. "
                "Nutze den Service "
                "`nowacontrol_hydraulic_sensor.install_zha_quirk`, "
                "starte Home Assistant neu und lerne den Sensor danach erneut an."
            ),
            title="nowaControl ZHA-Quirk fehlt",
            notification_id="nowacontrol_hydraulic_sensor_quirk_missing",
        )
    else:
        _LOGGER.debug("nowaControl ZHA quirk already present at %s", custom_quirks_path)

    return True
