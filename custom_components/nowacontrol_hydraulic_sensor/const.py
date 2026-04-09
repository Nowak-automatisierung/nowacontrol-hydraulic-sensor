"""Constants for the nowaControl Hydraulic Sensor helper integration."""

from __future__ import annotations

DOMAIN = "nowacontrol_hydraulic_sensor"
TITLE = "nowaControl Hydraulic Sensor"
QUIRK_FILENAME = "nowacontrol_hydraulic_sensor_v1.py"
QUIRK_README_FILENAME = "README.md"
DEFAULT_CUSTOM_QUIRKS_DIR = "custom_zha_quirks"
ZHA_CONF_CUSTOM_QUIRKS_PATH = "custom_quirks_path"
SERVICE_INSTALL_QUIRK = "install_zha_quirk"
SERVICE_REMOVE_QUIRK = "remove_zha_quirk"
SERVICE_SHOW_QUIRK_STATUS = "show_quirk_status"
CONF_AUTO_INSTALL_QUIRK = "auto_install_quirk"
CONF_SHOW_NOTIFICATIONS = "show_notifications"
ISSUE_ZHA_PATH = "zha_custom_quirks_path"
ISSUE_QUIRK_MISSING = "quirk_not_installed"
ISSUE_RESTART_REQUIRED = "restart_required"
DEFAULT_AUTO_INSTALL_QUIRK = True
DEFAULT_SHOW_NOTIFICATIONS = True
