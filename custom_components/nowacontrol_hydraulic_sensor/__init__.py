"""Home Assistant integration for nowaControl Hydraulic Sensor."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PATH
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import issue_registry as ir

from .const import (
    CONF_AUTO_INSTALL_QUIRK,
    CONF_SHOW_NOTIFICATIONS,
    DEFAULT_AUTO_INSTALL_QUIRK,
    DEFAULT_CUSTOM_QUIRKS_DIR,
    DEFAULT_SHOW_NOTIFICATIONS,
    DOMAIN,
    ISSUE_QUIRK_MISSING,
    ISSUE_RESTART_REQUIRED,
    ISSUE_ZHA_PATH,
)
from .services import (
    async_install_quirk,
    async_register_services,
    get_active_settings,
    quirk_exists,
    ui_quirks_path,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_PATH, default=DEFAULT_CUSTOM_QUIRKS_DIR): cv.string,
                vol.Optional(
                    CONF_AUTO_INSTALL_QUIRK, default=DEFAULT_AUTO_INSTALL_QUIRK
                ): cv.boolean,
                vol.Optional(
                    CONF_SHOW_NOTIFICATIONS, default=DEFAULT_SHOW_NOTIFICATIONS
                ): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


def _ensure_domain_data(hass: HomeAssistant) -> dict[str, Any]:
    domain_data = hass.data.setdefault(DOMAIN, {})
    domain_data.setdefault("yaml", {})
    domain_data.setdefault("entries", {})
    return domain_data


def _zha_custom_quirks_path(config: dict[str, Any]) -> str | None:
    zha_config = config.get("zha", {})
    if isinstance(zha_config, dict):
        return zha_config.get(CONF_PATH)
    return None


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration and import YAML defaults if present."""
    domain_data = _ensure_domain_data(hass)
    yaml_config = config.get(DOMAIN, {})
    domain_data["yaml"] = {
        CONF_PATH: yaml_config.get(CONF_PATH, DEFAULT_CUSTOM_QUIRKS_DIR),
        CONF_AUTO_INSTALL_QUIRK: yaml_config.get(
            CONF_AUTO_INSTALL_QUIRK, DEFAULT_AUTO_INSTALL_QUIRK
        ),
        CONF_SHOW_NOTIFICATIONS: yaml_config.get(
            CONF_SHOW_NOTIFICATIONS, DEFAULT_SHOW_NOTIFICATIONS
        ),
        "zha_custom_quirks_path": _zha_custom_quirks_path(config),
    }

    await async_register_services(hass)

    if DOMAIN in config and not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "import"},
                data=yaml_config,
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the integration from a config entry."""
    domain_data = _ensure_domain_data(hass)
    settings = get_active_settings(hass, entry)
    domain_data["entries"][entry.entry_id] = settings

    await async_register_services(hass)

    zha_path = domain_data.get("yaml", {}).get("zha_custom_quirks_path")
    configured_path = settings[CONF_PATH]

    if not zha_path:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_ZHA_PATH,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=ISSUE_ZHA_PATH,
            learn_more_url="https://www.home-assistant.io/integrations/zha/",
            translation_placeholders={"path": ui_quirks_path(configured_path)},
        )
    elif zha_path not in {configured_path, f"/config/{configured_path}"}:
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_ZHA_PATH,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=ISSUE_ZHA_PATH,
            learn_more_url="https://www.home-assistant.io/integrations/zha/",
            translation_placeholders={"path": ui_quirks_path(configured_path)},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_ZHA_PATH)

    if settings[CONF_AUTO_INSTALL_QUIRK]:
        deployed_path, changed = await async_install_quirk(
            hass,
            configured_path,
            overwrite=False,
        )
        _LOGGER.debug("nowaControl quirk available at %s", deployed_path)
        if changed:
            ir.async_create_issue(
                hass,
                DOMAIN,
                ISSUE_RESTART_REQUIRED,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_RESTART_REQUIRED,
            )
            if settings[CONF_SHOW_NOTIFICATIONS]:
                persistent_notification.async_create(
                    hass,
                    (
                        "Der nowaControl-ZHA-Quirk ist installiert. "
                        "Bitte Home Assistant neu starten und den Sensor danach in ZHA neu anlernen."
                    ),
                    title="nowaControl ZHA-Quirk bereit",
                    notification_id="nowacontrol_hydraulic_sensor_restart_required",
                )

    if not quirk_exists(hass, configured_path):
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_QUIRK_MISSING,
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_QUIRK_MISSING,
            learn_more_url="https://www.home-assistant.io/integrations/zha/",
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_QUIRK_MISSING)
        if not settings[CONF_AUTO_INSTALL_QUIRK]:
            ir.async_delete_issue(hass, DOMAIN, ISSUE_RESTART_REQUIRED)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    domain_data = _ensure_domain_data(hass)
    domain_data["entries"].pop(entry.entry_id, None)
    return True
