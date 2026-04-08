"""Repairs support for nowaControl Hydraulic Sensor."""

from __future__ import annotations

from homeassistant.components.repairs import ConfirmRepairFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import CONF_PATH, DOMAIN, ISSUE_QUIRK_MISSING, ISSUE_RESTART_REQUIRED
from .services import async_install_quirk, get_active_settings


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
):
    """Create a repairs flow for a known issue."""
    if issue_id == ISSUE_QUIRK_MISSING:
        return InstallQuirkRepairFlow()
    return None


class InstallQuirkRepairFlow(ConfirmRepairFlow):
    """Repair flow to install the packaged ZHA quirk."""

    def __init__(self) -> None:
        super().__init__()
        self._issue_id = ISSUE_QUIRK_MISSING

    async def async_step_confirm(self, user_input=None):
        """Install the packaged quirk and mark restart required."""
        if user_input is not None:
            settings = get_active_settings(self.hass)
            _, changed = await async_install_quirk(
                self.hass,
                settings[CONF_PATH],
                overwrite=False,
            )
            ir.async_delete_issue(self.hass, DOMAIN, ISSUE_QUIRK_MISSING)
            if changed:
                ir.async_create_issue(
                    self.hass,
                    DOMAIN,
                    ISSUE_RESTART_REQUIRED,
                    is_fixable=False,
                    severity=ir.IssueSeverity.WARNING,
                    translation_key=ISSUE_RESTART_REQUIRED,
                )
            return self.async_create_entry(title="", data={})

        return await super().async_step_confirm(user_input)
