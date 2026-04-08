"""Service helpers for nowaControl Hydraulic Sensor."""

from __future__ import annotations

import shutil
from pathlib import Path

import voluptuous as vol
from homeassistant.components import persistent_notification
from homeassistant.core import HomeAssistant, ServiceCall

from .const import (
    DEFAULT_CUSTOM_QUIRKS_DIR,
    DOMAIN,
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


def quirk_exists(hass: HomeAssistant, custom_quirks_path: str = DEFAULT_CUSTOM_QUIRKS_DIR) -> bool:
    """Return True if the deployed quirk file exists in HA config."""
    return _target_quirk_path(hass, custom_quirks_path).exists()


async def _install_quirk(hass: HomeAssistant, custom_quirks_path: str, overwrite: bool) -> str:
    target_dir = _target_dir(hass, custom_quirks_path)
    target_quirk = _target_quirk_path(hass, custom_quirks_path)
    target_readme = target_dir / QUIRK_README_FILENAME
    source_quirk = _packaged_quirk_path()
    source_readme = _packaged_quirk_readme_path()

    def _copy() -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        if target_quirk.exists() and not overwrite:
            return
        shutil.copy2(source_quirk, target_quirk)
        shutil.copy2(source_readme, target_readme)

    await hass.async_add_executor_job(_copy)
    return str(target_quirk)


async def _remove_quirk(hass: HomeAssistant, custom_quirks_path: str) -> bool:
    target_quirk = _target_quirk_path(hass, custom_quirks_path)

    def _delete() -> bool:
        if not target_quirk.exists():
            return False
        target_quirk.unlink()
        return True

    return await hass.async_add_executor_job(_delete)


async def async_register_services(hass: HomeAssistant, custom_quirks_path: str) -> None:
    """Register helper services for quirk deployment."""
    if hass.services.has_service(DOMAIN, SERVICE_INSTALL_QUIRK):
        return

    install_schema = vol.Schema({vol.Optional("overwrite", default=False): bool})

    async def async_handle_install(call: ServiceCall) -> None:
        deployed_path = await _install_quirk(
            hass,
            custom_quirks_path,
            overwrite=call.data.get("overwrite", False),
        )
        persistent_notification.async_create(
            hass,
            (
                f"ZHA-Quirk wurde nach `{deployed_path}` kopiert.\n\n"
                "Bitte pruefen:\n"
                "- configuration.yaml enthaelt `zha: custom_quirks_path: /config/custom_zha_quirks`\n"
                "- Home Assistant neu starten\n"
                "- Sensor in ZHA loeschen und neu anlernen"
            ),
            title="nowaControl ZHA-Quirk installiert",
            notification_id="nowacontrol_hydraulic_sensor_quirk_installed",
        )

    async def async_handle_remove(call: ServiceCall) -> None:
        removed = await _remove_quirk(hass, custom_quirks_path)
        message = (
            "Der ZHA-Quirk wurde aus dem Home-Assistant-Konfigurationspfad entfernt."
            if removed
            else "Kein installierter ZHA-Quirk zum Entfernen gefunden."
        )
        persistent_notification.async_create(
            hass,
            message,
            title="nowaControl ZHA-Quirk Status",
            notification_id="nowacontrol_hydraulic_sensor_quirk_removed",
        )

    async def async_handle_status(call: ServiceCall) -> None:
        target_quirk = _target_quirk_path(hass, custom_quirks_path)
        status = (
            f"Paketierter Quirk: `{_packaged_quirk_path()}`\n"
            f"Installationsziel: `{target_quirk}`\n"
            f"Vorhanden: `{target_quirk.exists()}`"
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
