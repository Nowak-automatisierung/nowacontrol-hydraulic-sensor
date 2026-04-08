"""Service and quirk deployment helpers for nowaControl Hydraulic Sensor."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PATH
from homeassistant.core import HomeAssistant, ServiceCall
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
    QUIRK_FILENAME,
    QUIRK_README_FILENAME,
    SERVICE_INSTALL_QUIRK,
    SERVICE_REMOVE_QUIRK,
    SERVICE_SHOW_QUIRK_STATUS,
)


def _package_root() -> Path:
    return Path(__file__).resolve().parent


def _packaged_quirk_path() -> Path:
    return _package_root() / "quirks" / QUIRK_FILENAME


def _packaged_quirk_readme_path() -> Path:
    return _package_root() / "quirks" / QUIRK_README_FILENAME


def _target_dir(hass: HomeAssistant, custom_quirks_path: str) -> Path:
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
    """Return effective settings from config entry first, then YAML defaults."""
    yaml_data = hass.data.get(DOMAIN, {}).get("yaml", {})

    if entry is None:
        entries = hass.config_entries.async_entries(DOMAIN)
        entry = entries[0] if entries else None

    data = dict(yaml_data)
    if entry is not None:
        data.update(entry.data)
        data.update(entry.options)

    data.setdefault(CONF_PATH, DEFAULT_CUSTOM_QUIRKS_DIR)
    data.setdefault(CONF_AUTO_INSTALL_QUIRK, DEFAULT_AUTO_INSTALL_QUIRK)
    data.setdefault(CONF_SHOW_NOTIFICATIONS, DEFAULT_SHOW_NOTIFICATIONS)
    return data


async def async_install_quirk(
    hass: HomeAssistant,
    custom_quirks_path: str,
    overwrite: bool,
) -> tuple[str, bool]:
    """Install the packaged quirk into the active ZHA quirk path."""
    target_dir = _target_dir(hass, custom_quirks_path)
    target_quirk = _target_quirk_path(hass, custom_quirks_path)
    target_readme = target_dir / QUIRK_README_FILENAME
    source_quirk = _packaged_quirk_path()
    source_readme = _packaged_quirk_readme_path()

    def _copy() -> bool:
        target_dir.mkdir(parents=True, exist_ok=True)
        if target_quirk.exists() and not overwrite:
            return False
        shutil.copy2(source_quirk, target_quirk)
        shutil.copy2(source_readme, target_readme)
        return True

    changed = await hass.async_add_executor_job(_copy)
    return str(target_quirk), changed


async def _remove_quirk(hass: HomeAssistant, custom_quirks_path: str) -> bool:
    target_quirk = _target_quirk_path(hass, custom_quirks_path)

    def _delete() -> bool:
        if not target_quirk.exists():
            return False
        target_quirk.unlink()
        return True

    return await hass.async_add_executor_job(_delete)


async def async_register_services(hass: HomeAssistant) -> None:
    """Register helper services for quirk deployment."""
    if hass.services.has_service(DOMAIN, SERVICE_INSTALL_QUIRK):
        return

    install_schema = vol.Schema({vol.Optional("overwrite", default=False): bool})

    async def async_handle_install(call: ServiceCall) -> None:
        settings = get_active_settings(hass)
        deployed_path, changed = await async_install_quirk(
            hass,
            settings[CONF_PATH],
            overwrite=call.data.get("overwrite", False),
        )
        ir.async_delete_issue(hass, DOMAIN, ISSUE_QUIRK_MISSING)
        if changed:
            ir.async_create_issue(
                hass,
                DOMAIN,
                ISSUE_RESTART_REQUIRED,
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_RESTART_REQUIRED,
            )
        persistent_notification.async_create(
            hass,
            (
                (
                    f"ZHA-Quirk wurde nach `{deployed_path}` kopiert.\n\n"
                    "Bitte Home Assistant neu starten und den Sensor danach in ZHA neu anlernen."
                )
                if changed
                else (
                    f"Der ZHA-Quirk liegt bereits unter `{deployed_path}`.\n\n"
                    "Wenn du die neue Quirk-Version erwartest, fuehre den Service mit `overwrite: true` aus."
                )
            ),
            title="nowaControl ZHA-Quirk installiert",
            notification_id="nowacontrol_hydraulic_sensor_quirk_installed",
        )

    async def async_handle_remove(call: ServiceCall) -> None:
        settings = get_active_settings(hass)
        removed = await _remove_quirk(hass, settings[CONF_PATH])
        ir.async_create_issue(
            hass,
            DOMAIN,
            ISSUE_QUIRK_MISSING,
            is_fixable=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key=ISSUE_QUIRK_MISSING,
        )
        message = (
            "Der ZHA-Quirk wurde aus dem Home-Assistant-Konfigurationspfad entfernt."
            if removed
            else "Kein installierter ZHA-Quirk zum Entfernen gefunden."
        )
        if removed:
            ir.async_delete_issue(hass, DOMAIN, ISSUE_RESTART_REQUIRED)
        persistent_notification.async_create(
            hass,
            message,
            title="nowaControl ZHA-Quirk Status",
            notification_id="nowacontrol_hydraulic_sensor_quirk_removed",
        )

    async def async_handle_status(call: ServiceCall) -> None:
        settings = get_active_settings(hass)
        target_quirk = _target_quirk_path(hass, settings[CONF_PATH])
        status = (
            f"Paketierter Quirk: `{_packaged_quirk_path()}`\n"
            f"Installationsziel: `{target_quirk}`\n"
            f"Vorhanden: `{target_quirk.exists()}`\n"
            f"Auto-Install: `{settings[CONF_AUTO_INSTALL_QUIRK]}`\n"
            f"Benachrichtigungen: `{settings[CONF_SHOW_NOTIFICATIONS]}`"
        )
        persistent_notification.async_create(
            hass,
            status,
            title="nowaControl ZHA-Quirk Status",
            notification_id="nowacontrol_hydraulic_sensor_quirk_status",
        )

    hass.services.async_register(DOMAIN, SERVICE_INSTALL_QUIRK, async_handle_install, schema=install_schema)
    hass.services.async_register(DOMAIN, SERVICE_REMOVE_QUIRK, async_handle_remove)
    hass.services.async_register(DOMAIN, SERVICE_SHOW_QUIRK_STATUS, async_handle_status)
