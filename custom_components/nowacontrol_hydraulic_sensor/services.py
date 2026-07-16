"""Fail-closed service and quirk helpers for nowaControl Hydraulic Sensor."""

from __future__ import annotations

from collections.abc import Mapping
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


def _validated_quirks_path(value: object) -> str | None:
    """Return a non-empty string path without coercing arbitrary objects."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def ui_quirks_path(_custom_quirks_path: object) -> str:
    """Return a generic, path-free label for user-facing diagnostics."""
    return "configured ZHA custom quirks directory"


def quirk_exists(
    hass: HomeAssistant,
    custom_quirks_path: object = DEFAULT_CUSTOM_QUIRKS_DIR,
) -> bool:
    """Return True if the deployed quirk file exists in HA config."""
    safe_path = _validated_quirks_path(custom_quirks_path)
    if safe_path is None:
        safe_path = DEFAULT_CUSTOM_QUIRKS_DIR
    return _target_quirk_path(hass, safe_path).exists()


def _active_settings_data(
    hass: HomeAssistant,
    entry: ConfigEntry | None,
) -> tuple[dict[str, Any], bool]:
    """Return merged settings plus validity of the selected configured path."""
    domain_data = hass.data.get(DOMAIN, {})
    yaml_data = domain_data.get("yaml", {}) if isinstance(domain_data, Mapping) else {}

    if entry is None:
        entries = hass.config_entries.async_entries(DOMAIN)
        entry = entries[0] if entries else None

    data: dict[str, Any] = {}
    if isinstance(yaml_data, Mapping):
        data.update(yaml_data)
    if entry is not None:
        if isinstance(entry.data, Mapping):
            data.update(entry.data)
        if isinstance(entry.options, Mapping):
            data.update(entry.options)

    selected_path = data.get(CONF_PATH, DEFAULT_CUSTOM_QUIRKS_DIR)
    safe_path = _validated_quirks_path(selected_path)
    path_is_valid = safe_path is not None
    data[CONF_PATH] = safe_path or DEFAULT_CUSTOM_QUIRKS_DIR
    data[CONF_AUTO_INSTALL_QUIRK] = DEFAULT_AUTO_INSTALL_QUIRK
    data.setdefault(CONF_SHOW_NOTIFICATIONS, DEFAULT_SHOW_NOTIFICATIONS)
    return data, path_is_valid


def get_active_settings(hass: HomeAssistant, entry: ConfigEntry | None = None) -> dict[str, Any]:
    """Return settings with file-writing auto-install forced off."""
    return _active_settings_data(hass, entry)[0]


def active_quirks_path_is_valid(
    hass: HomeAssistant,
    entry: ConfigEntry | None = None,
) -> bool:
    """Return whether the selected YAML/entry/options path is a valid string."""
    return _active_settings_data(hass, entry)[1]


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
            title="nowaControl product file writes disabled",
            notification_id="nowacontrol_hydraulic_sensor_writes_disabled",
        )

    hass.services.async_register(DOMAIN, SERVICE_SHOW_QUIRK_STATUS, async_handle_status)
