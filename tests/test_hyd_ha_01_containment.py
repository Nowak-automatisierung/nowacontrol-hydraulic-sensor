"""Focused regression tests for HYD-HA-01 fail-closed containment."""

from __future__ import annotations

import asyncio
import hashlib
import importlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DOMAIN = "nowacontrol_hydraulic_sensor"
DISABLED_MESSAGE = (
    "Home Assistant file writes are disabled; security commissioning is required."
)


class _Schema:
    def __init__(self, schema, *args, **kwargs):
        self.schema = schema

    def __call__(self, value):
        return value


class _IssueSeverity:
    ERROR = "error"
    WARNING = "warning"


class _ConfirmRepairFlow:
    def __init__(self):
        self.hass = None

    async def async_step_confirm(self, user_input=None):
        return {"type": "form", "user_input": user_input}

    def async_create_entry(self, *, title, data):
        return {"type": "create_entry", "title": title, "data": data}


def _install_dependency_stubs() -> list[tuple[object, str, dict[str, object]]]:
    """Install the minimal HA/voluptuous surface needed for import tests."""
    notifications: list[tuple[object, str, dict[str, object]]] = []
    issues: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    voluptuous = ModuleType("voluptuous")
    voluptuous.Schema = _Schema
    voluptuous.Optional = lambda key, default=None: key
    voluptuous.Required = lambda key, default=None: key
    voluptuous.ALLOW_EXTRA = object()

    homeassistant = ModuleType("homeassistant")
    homeassistant.__path__ = []
    components = ModuleType("homeassistant.components")
    components.__path__ = []
    persistent_notification = ModuleType(
        "homeassistant.components.persistent_notification"
    )

    def async_create(hass, message, **kwargs):
        notifications.append((hass, message, kwargs))

    persistent_notification.async_create = async_create

    repairs_component = ModuleType("homeassistant.components.repairs")
    repairs_component.ConfirmRepairFlow = _ConfirmRepairFlow

    config_entries = ModuleType("homeassistant.config_entries")
    config_entries.ConfigEntry = type("ConfigEntry", (), {})
    const = ModuleType("homeassistant.const")
    const.CONF_PATH = "path"
    core = ModuleType("homeassistant.core")
    core.HomeAssistant = object
    core.ServiceCall = type("ServiceCall", (), {})

    helpers = ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    config_validation = ModuleType("homeassistant.helpers.config_validation")
    config_validation.string = lambda value: value
    config_validation.boolean = lambda value: bool(value)
    issue_registry = ModuleType("homeassistant.helpers.issue_registry")
    issue_registry.IssueSeverity = _IssueSeverity
    issue_registry.async_create_issue = (
        lambda *args, **kwargs: issues.append(("create", args, kwargs))
    )
    issue_registry.async_delete_issue = (
        lambda *args, **kwargs: issues.append(("delete", args, kwargs))
    )

    modules = {
        "voluptuous": voluptuous,
        "homeassistant": homeassistant,
        "homeassistant.components": components,
        "homeassistant.components.persistent_notification": persistent_notification,
        "homeassistant.components.repairs": repairs_component,
        "homeassistant.config_entries": config_entries,
        "homeassistant.const": const,
        "homeassistant.core": core,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.config_validation": config_validation,
        "homeassistant.helpers.issue_registry": issue_registry,
    }
    sys.modules.update(modules)
    components.persistent_notification = persistent_notification
    helpers.config_validation = config_validation
    helpers.issue_registry = issue_registry
    return notifications, issues


class _FakeServices:
    def __init__(self):
        self.registered: dict[tuple[str, str], tuple[object, object]] = {}

    def has_service(self, domain, service):
        return (domain, service) in self.registered

    def async_register(self, domain, service, handler, schema=None):
        self.registered[(domain, service)] = (handler, schema)


class _FakeConfigEntries:
    def __init__(self, entries=None):
        self._entries = list(entries or [])
        self.flow = SimpleNamespace(async_init=self._async_init)

    async def _async_init(self, *args, **kwargs):
        return None

    def async_entries(self, domain):
        return self._entries if domain == DOMAIN else []


class _FakeHass:
    def __init__(self, config_root: Path, entries=None):
        self.data = {}
        self.services = _FakeServices()
        self.config_entries = _FakeConfigEntries(entries)
        self.config = SimpleNamespace(
            path=lambda relative="": str(config_root / relative)
        )

    async def async_add_executor_job(self, function):
        return function()

    def async_create_task(self, coroutine):
        return asyncio.create_task(coroutine)


class _Entry:
    def __init__(self, data=None, options=None):
        self.entry_id = "hyd-ha-01-test-entry"
        self.data = dict(data or {})
        self.options = dict(options or {})


class HydHa01ContainmentTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.notifications, cls.issues = _install_dependency_stubs()
        cls.integration = importlib.import_module(
            "custom_components.nowacontrol_hydraulic_sensor"
        )
        cls.const = importlib.import_module(
            "custom_components.nowacontrol_hydraulic_sensor.const"
        )
        cls.services = importlib.import_module(
            "custom_components.nowacontrol_hydraulic_sensor.services"
        )

    def setUp(self):
        external_root = Path(os.environ["HYD_HA_01_TEST_TMPDIR"]).resolve()
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="case-", dir=external_root
        )
        self.temp_path = Path(self.temp_dir.name).resolve()
        self.notifications.clear()
        self.issues.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_auto_install_default_off_for_new_install(self):
        self.assertIs(self.const.DEFAULT_AUTO_INSTALL_QUIRK, False)
        hass = _FakeHass(self.temp_path)
        settings = self.services.get_active_settings(hass)
        self.assertIs(settings[self.const.CONF_AUTO_INSTALL_QUIRK], False)

    def test_upgrade_configuration_cannot_reenable_writes(self):
        entry = _Entry(
            data={self.const.CONF_AUTO_INSTALL_QUIRK: True},
            options={self.const.CONF_AUTO_INSTALL_QUIRK: True},
        )
        hass = _FakeHass(self.temp_path, [entry])
        hass.data[DOMAIN] = {
            "yaml": {self.const.CONF_AUTO_INSTALL_QUIRK: True}
        }
        settings = self.services.get_active_settings(hass, entry)
        self.assertIs(settings[self.const.CONF_AUTO_INSTALL_QUIRK], False)

    async def test_new_and_upgraded_entries_initialize_without_writer(self):
        for auto_install in (None, True):
            with self.subTest(auto_install=auto_install):
                data = {"path": str(self.temp_path / "quirks")}
                if auto_install is not None:
                    data[self.const.CONF_AUTO_INSTALL_QUIRK] = auto_install
                entry = _Entry(data=data)
                hass = _FakeHass(self.temp_path, [entry])
                await self.integration.async_setup(hass, {})
                with mock.patch.object(
                    self.integration,
                    "async_install_quirk",
                    new=mock.AsyncMock(
                        side_effect=AssertionError("writer must not run")
                    ),
                ) as writer:
                    self.assertTrue(
                        await self.integration.async_setup_entry(hass, entry)
                    )
                writer.assert_not_awaited()

    async def test_write_and_overwrite_are_deterministically_denied(self):
        external_target = self.temp_path / "external-target"
        external_target.mkdir()
        symlink_target = self.temp_path / "linked-quirks"
        symlink_target.symlink_to(external_target, target_is_directory=True)
        targets = (
            "/config/custom_zha_quirks",
            "/config/.storage/forbidden",
            "../parent-traversal",
            str(symlink_target),
            "/Volumes/external-mount/custom_zha_quirks",
        )

        for overwrite in (False, True):
            for target in targets:
                with self.subTest(overwrite=overwrite, target=target):
                    with (
                        mock.patch.object(
                            Path,
                            "mkdir",
                            side_effect=AssertionError("mkdir attempted"),
                        ),
                        mock.patch.object(
                            shutil,
                            "copy2",
                            side_effect=AssertionError("copy attempted"),
                        ),
                    ):
                        with self.assertRaisesRegex(
                            PermissionError, f"^{DISABLED_MESSAGE}$"
                        ):
                            await self.services.async_install_quirk(
                                _FakeHass(self.temp_path), target, overwrite
                            )

    async def test_remove_is_deterministically_denied(self):
        target_dir = self.temp_path / "remove-target"
        target_dir.mkdir()
        target_file = target_dir / self.const.QUIRK_FILENAME
        original = b"preserve-me"
        target_file.write_bytes(original)

        with mock.patch.object(
            Path, "unlink", side_effect=AssertionError("unlink attempted")
        ):
            with self.assertRaisesRegex(
                PermissionError, f"^{DISABLED_MESSAGE}$"
            ):
                await self.services._remove_quirk(
                    _FakeHass(self.temp_path), str(target_dir)
                )

        self.assertEqual(target_file.read_bytes(), original)

    async def test_writing_services_and_repair_flow_are_not_exposed(self):
        repairs = importlib.import_module(
            "custom_components.nowacontrol_hydraulic_sensor.repairs"
        )
        hass = _FakeHass(self.temp_path)
        await self.services.async_register_services(hass)

        self.assertNotIn(
            (DOMAIN, self.const.SERVICE_INSTALL_QUIRK), hass.services.registered
        )
        self.assertNotIn(
            (DOMAIN, self.const.SERVICE_REMOVE_QUIRK), hass.services.registered
        )
        self.assertIn(
            (DOMAIN, self.const.SERVICE_SHOW_QUIRK_STATUS), hass.services.registered
        )
        self.assertIsNone(
            await repairs.async_create_fix_flow(
                hass, self.const.ISSUE_QUIRK_MISSING
            )
        )

    async def test_status_is_clear_and_does_not_disclose_paths(self):
        hass = _FakeHass(self.temp_path)
        await self.services.async_register_services(hass)
        handler, _ = hass.services.registered[
            (DOMAIN, self.const.SERVICE_SHOW_QUIRK_STATUS)
        ]
        await handler(SimpleNamespace(data={}))

        self.assertEqual(len(self.notifications), 1)
        message = self.notifications[0][1]
        self.assertEqual(message, DISABLED_MESSAGE)
        for forbidden in (
            "/config",
            ".storage",
            "custom_zha_quirks",
            str(self.temp_path),
        ):
            self.assertNotIn(forbidden, message)

    def test_service_metadata_exposes_only_read_only_status(self):
        metadata = (
            REPOSITORY_ROOT
            / "custom_components/nowacontrol_hydraulic_sensor/services.yaml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("install_zha_quirk:", metadata)
        self.assertNotIn("remove_zha_quirk:", metadata)
        self.assertIn("show_quirk_status:", metadata)

    def test_sensor_read_path_is_byte_identical_to_baseline(self):
        expected = {
            "custom_components/nowacontrol_hydraulic_sensor/quirks/nowacontrol_hydraulic_sensor_v1.py": "3f7b1958f9463de89db2a0f887a7ea7e92b999dd78dfb29d2900492dd26a5452",
            "homeassistant/zha_quirks/nowacontrol_hydraulic_sensor_v1.py": "609dbee498e55119a3f8c403d8bd2df3a751f851347612a8da1577205011fa97",
        }
        for relative_path, expected_digest in expected.items():
            with self.subTest(path=relative_path):
                source = (REPOSITORY_ROOT / relative_path).read_bytes()
                self.assertEqual(hashlib.sha256(source).hexdigest(), expected_digest)
                self.assertGreaterEqual(source.count(b".sensor("), 5)

    def test_test_artifacts_are_isolated_from_productive_paths(self):
        self.assertFalse(self.temp_path.is_relative_to(REPOSITORY_ROOT))
        self.assertFalse(self.temp_path.is_relative_to(Path("/config")))
        self.assertNotIn(".storage", self.temp_path.parts)


if __name__ == "__main__":
    unittest.main()
