"""Fail-closed service and quirk helpers for nowaControl Hydraulic Sensor."""

from __future__ import annotations

from pathlib import Path
from typing import Any, NoReturn

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PATH
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    CONF_AUTO_INSTALL_QUIRK,
    CONF_SHOW_NOTIFICATIONS,
    DEFAULT_AUTO_INSTALL_QUIRK,
    DEFAULT_CUSTOM_QUIRKS_DIR,
    DEFAULT_SHOW_NOTIFICATIONS,
    DOMAIN,
    FILE_WRITES_DISABLED_MESSAGE,
    QUIRK_FILENAME,
    SERVICE_SHOW_QUIRK_STATUS,
)


class FileWriteDisabledError(PermissionError):
    """Raised whenever a contained Home Assistant file write is requested."""


def _deny_file_write() -> NoReturn:
    raise FileWriteDisabledError(FILE_WRITES_DISABLED_MESSAGE)


def _target_dir(hass: HomeAssistant, custom_quirks_path: str) -> Path:
    target = Path(custom_quirks_path)
    if target.is_absolute():
        return target
    return Path(hass.config.path(custom_quirks_path))


def _target_quirk_path(hass: HomeAssistant, custom_quirks_path: str) -> Path:
    return _target_dir(hass, custom_quirks_path) / QUIRK_FILENAME


def ui_quirks_path(custom_quirks_path: str) -> str:
    """Return a user-facing quirk path for HA documentation."""
    return (
        custom_quirks_path
        if custom_quirks_path.startswith("/config/")
        else f"/config/{custom_quirks_path}"
    )


def quirk_exists(hass: HomeAssistant, custom_quirks_path: str = DEFAULT_CUSTOM_QUIRKS_DIR) -> bool:
    """Return True if the deployed quirk file exists in HA config."""
    return _target_quirk_path(hass, custom_quirks_path).exists()


def get_active_settings(hass: HomeAssistant, entry: ConfigEntry | None = None) -> dict[str, Any]:
    """Return settings with file-writing auto-install forced off."""
    yaml_data = hass.data.get(DOMAIN, {}).get("yaml", {})

    if entry is None:
        entries = hass.config_entries.async_entries(DOMAIN)
        entry = entries[0] if entries else None

    data = dict(yaml_data)
    if entry is not None:
        data.update(entry.data)
        data.update(entry.options)

    data.setdefault(CONF_PATH, DEFAULT_CUSTOM_QUIRKS_DIR)
    data[CONF_AUTO_INSTALL_QUIRK] = DEFAULT_AUTO_INSTALL_QUIRK
    data.setdefault(CONF_SHOW_NOTIFICATIONS, DEFAULT_SHOW_NOTIFICATIONS)
    return data


async def async_install_quirk(
    hass: HomeAssistant,
    custom_quirks_path: str,
    overwrite: bool,
) -> tuple[str, bool]:
    """Reject install and overwrite attempts while containment is active."""
    _deny_file_write()


async def _remove_quirk(hass: HomeAssistant, custom_quirks_path: str) -> bool:
    """Reject remove attempts while containment is active."""
    _deny_file_write()


async def async_register_services(hass: HomeAssistant) -> None:
    """Register only the read-only containment status service."""
    if hass.services.has_service(DOMAIN, SERVICE_SHOW_QUIRK_STATUS):
        return

    async def async_handle_status(_call: ServiceCall) -> None:
        persistent_notification.async_create(
            hass,
            FILE_WRITES_DISABLED_MESSAGE,
            title="nowaControl file writes disabled",
            notification_id="nowacontrol_hydraulic_sensor_writes_disabled",
        )

    hass.services.async_register(DOMAIN, SERVICE_SHOW_QUIRK_STATUS, async_handle_status)
