"""Home Assistant integration for nowaControl Hydraulic Sensor."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol
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
    ZHA_CONF_CUSTOM_QUIRKS_PATH,
)
from .services import (
    active_quirks_path_is_valid,
    async_register_services,
    get_active_settings,
    quirk_exists,
)

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


def _zha_custom_quirks_path(config: dict[str, Any]) -> object | None:
    zha_config = config.get("zha", {})
    if isinstance(zha_config, Mapping):
        return zha_config.get(ZHA_CONF_CUSTOM_QUIRKS_PATH)
    return None


def _normalize_quirks_path(path: object) -> str | None:
    """Normalize quirk paths for comparison in HA UI and config."""
    if not isinstance(path, str):
        return None
    path = path.strip()
    if not path:
        return None
    normalized = path.replace("\\", "/").rstrip("/")
    if normalized.startswith("/config/"):
        return normalized
    if normalized == "custom_zha_quirks":
        return "/config/custom_zha_quirks"
    return f"/config/{normalized.lstrip('/')}"


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the integration and import YAML defaults if present."""
    domain_data = _ensure_domain_data(hass)
    yaml_config = config.get(DOMAIN, {})
    if not isinstance(yaml_config, Mapping):
        yaml_config = {}
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

    # HA framework persistence (entries/issues/notifications) remains allowed.
    # No product file writer or caller-controlled filesystem target is reached.

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

    zha_path = _normalize_quirks_path(domain_data.get("yaml", {}).get("zha_custom_quirks_path"))
    configured_path = settings[CONF_PATH]
    normalized_configured_path = _normalize_quirks_path(configured_path)
    configured_path_is_valid = active_quirks_path_is_valid(hass, entry)

    # A stale restart issue can only describe a previous writer state. Auto-install
    # is effectively disabled, so clean it up regardless of the read-only file state.
    ir.async_delete_issue(hass, DOMAIN, ISSUE_RESTART_REQUIRED)

    if (
        not configured_path_is_valid
        or not zha_path
        or zha_path != normalized_configured_path
    ):
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_ZHA_PATH,
            is_fixable=False,
            severity=ir.IssueSeverity.ERROR,
            translation_key=ISSUE_ZHA_PATH,
            learn_more_url="https://www.home-assistant.io/integrations/zha/",
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_ZHA_PATH)

    if not quirk_exists(hass, configured_path):
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_QUIRK_MISSING,
            is_fixable=False,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_QUIRK_MISSING,
            learn_more_url="https://www.home-assistant.io/integrations/zha/",
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, ISSUE_QUIRK_MISSING)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    domain_data = _ensure_domain_data(hass)
    domain_data["entries"].pop(entry.entry_id, None)
    return True
