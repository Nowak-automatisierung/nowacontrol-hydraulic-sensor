"""Contained repairs support for nowaControl Hydraulic Sensor."""

from __future__ import annotations

from homeassistant.core import HomeAssistant


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
):
    """Expose no file-writing repair flow while containment is active."""
    return None
