"""Behavioral regression tests for HYD-HA-01 fail-closed containment."""

from __future__ import annotations

import asyncio
from contextlib import ExitStack
import hashlib
import importlib
import json
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
CONF_PATH = "path"
DISABLED_MESSAGE = (
    "nowaControl product file writes and caller-controlled path writes are disabled; "
    "security commissioning is required."
)
_MISSING = object()


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


class _FlowBase:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()

    def __init__(self):
        self.unique_id = None

    async def async_set_unique_id(self, unique_id):
        self.unique_id = unique_id

    def _abort_if_unique_id_configured(self):
        return None

    def async_create_entry(self, *, title, data):
        return {"type": "create_entry", "title": title, "data": data}

    def async_show_form(self, *, step_id, data_schema):
        return {"type": "form", "step_id": step_id, "data_schema": data_schema}


def _install_dependency_stubs() -> list[list[object]]:
    """Install the minimal HA/voluptuous surface needed for behavioral tests."""
    notifications: list[object] = []
    issue_events: list[object] = []

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
    config_entries.ConfigFlow = _FlowBase
    config_entries.OptionsFlow = _FlowBase
    const = ModuleType("homeassistant.const")
    const.CONF_PATH = "path"
    core = ModuleType("homeassistant.core")
    core.HomeAssistant = object
    core.ServiceCall = type("ServiceCall", (), {})
    data_entry_flow = ModuleType("homeassistant.data_entry_flow")
    data_entry_flow.FlowResult = dict

    helpers = ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    config_validation = ModuleType("homeassistant.helpers.config_validation")
    config_validation.string = lambda value: value
    config_validation.boolean = lambda value: bool(value)
    issue_registry = ModuleType("homeassistant.helpers.issue_registry")
    issue_registry.IssueSeverity = _IssueSeverity

    def async_create_issue(hass, domain, issue_id, **kwargs):
        hass.issue_registry[(domain, issue_id)] = dict(kwargs)
        issue_events.append(("create", domain, issue_id, dict(kwargs)))

    def async_delete_issue(hass, domain, issue_id):
        hass.issue_registry.pop((domain, issue_id), None)
        issue_events.append(("delete", domain, issue_id, {}))

    issue_registry.async_create_issue = async_create_issue
    issue_registry.async_delete_issue = async_delete_issue

    modules = {
        "voluptuous": voluptuous,
        "homeassistant": homeassistant,
        "homeassistant.components": components,
        "homeassistant.components.persistent_notification": persistent_notification,
        "homeassistant.components.repairs": repairs_component,
        "homeassistant.config_entries": config_entries,
        "homeassistant.const": const,
        "homeassistant.core": core,
        "homeassistant.data_entry_flow": data_entry_flow,
        "homeassistant.helpers": helpers,
        "homeassistant.helpers.config_validation": config_validation,
        "homeassistant.helpers.issue_registry": issue_registry,
    }
    sys.modules.update(modules)
    homeassistant.config_entries = config_entries
    components.persistent_notification = persistent_notification
    helpers.config_validation = config_validation
    helpers.issue_registry = issue_registry
    return [notifications, issue_events]


class _FakeServices:
    def __init__(self):
        self.registered: dict[tuple[str, str], tuple[object, object]] = {}

    def has_service(self, domain, service):
        return (domain, service) in self.registered

    def async_register(self, domain, service, handler, schema=None):
        self.registered[(domain, service)] = (handler, schema)

    async def async_call(self, domain, service, data=None):
        handler, _schema = self.registered[(domain, service)]
        return await handler(SimpleNamespace(data=data or {}))


class _FakeConfigEntries:
    def __init__(self, entries=None):
        self._entries = list(entries or [])
        self.flow_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        self.flow = SimpleNamespace(async_init=self._async_init)

    async def _async_init(self, *args, **kwargs):
        self.flow_calls.append((args, kwargs))
        return {"type": "create_entry", "data": kwargs.get("data", {})}

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
        self.issue_registry: dict[tuple[str, str], dict[str, object]] = {}
        self.tasks: list[asyncio.Task] = []

    async def async_add_executor_job(self, function):
        return function()

    def async_create_task(self, coroutine):
        task = asyncio.create_task(coroutine)
        self.tasks.append(task)
        return task


class _Entry:
    def __init__(self, data=None, options=None):
        self.entry_id = "hyd-ha-01-test-entry"
        self.data = dict(data or {})
        self.options = dict(options or {})


class _StringTrap:
    def __str__(self):
        raise AssertionError("implicit str() conversion attempted")


def _filesystem_manifest(root: Path) -> tuple[tuple[object, ...], ...]:
    """Return paths, types, sizes, hashes, symlinks and directories for root."""
    entries: list[tuple[object, ...]] = []
    for path in [root, *sorted(root.rglob("*"), key=lambda item: item.as_posix())]:
        relative = "." if path == root else path.relative_to(root).as_posix()
        stat_result = path.lstat()
        if path.is_symlink():
            kind = "symlink"
            digest = hashlib.sha256(os.readlink(path).encode()).hexdigest()
        elif path.is_dir():
            kind = "directory"
            digest = None
        elif path.is_file():
            kind = "file"
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            kind = "other"
            digest = None
        entries.append((relative, kind, stat_result.st_size, digest))
    return tuple(entries)


class HydHa01ContainmentTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.notifications, cls.issue_events = _install_dependency_stubs()
        cls.integration = importlib.import_module(
            "custom_components.nowacontrol_hydraulic_sensor"
        )
        cls.const = importlib.import_module(
            "custom_components.nowacontrol_hydraulic_sensor.const"
        )
        cls.services = importlib.import_module(
            "custom_components.nowacontrol_hydraulic_sensor.services"
        )
        cls.config_flow = importlib.import_module(
            "custom_components.nowacontrol_hydraulic_sensor.config_flow"
        )

    def setUp(self):
        external_root = Path(os.environ["HYD_HA_01_TEST_TMPDIR"]).resolve()
        external_root.mkdir(parents=True, exist_ok=True)
        self.temp_dir = tempfile.TemporaryDirectory(
            prefix="case-", dir=external_root
        )
        self.temp_path = Path(self.temp_dir.name).resolve()
        self.notifications.clear()
        self.issue_events.clear()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _settings(self, *, yaml=_MISSING, data=_MISSING, options=_MISSING):
        entry_data = {} if data is _MISSING else {CONF_PATH: data}
        entry_options = (
            {} if options is _MISSING else {CONF_PATH: options}
        )
        entry = _Entry(entry_data, entry_options)
        hass = _FakeHass(self.temp_path, [entry])
        yaml_data = {} if yaml is _MISSING else {CONF_PATH: yaml}
        hass.data[DOMAIN] = {"yaml": yaml_data}
        return self.services.get_active_settings(hass, entry), hass, entry

    def _writer_targets(self):
        external_target = self.temp_path / "external-target"
        external_target.mkdir()
        symlink_target = self.temp_path / "linked-quirks"
        symlink_target.symlink_to(external_target, target_is_directory=True)
        return (
            str(self.temp_path / "absolute-target"),
            "../parent-traversal",
            str(symlink_target),
            "/Volumes/external-mount-like/custom-zha-quirks",
            "/config/custom-zha-quirks",
            None,
            True,
            123,
            [],
            {},
            "",
            "   ",
        )

    async def _assert_denied_before_sinks(self, operation):
        manifest_before = _filesystem_manifest(self.temp_path)
        patchers = (
            mock.patch.object(
                self.services,
                "_target_dir",
                side_effect=AssertionError("_target_dir reached"),
            ),
            mock.patch.object(
                self.services,
                "_target_quirk_path",
                side_effect=AssertionError("_target_quirk_path reached"),
            ),
            mock.patch.object(
                Path, "resolve", side_effect=AssertionError("Path.resolve reached")
            ),
            mock.patch.object(
                Path, "mkdir", side_effect=AssertionError("mkdir reached")
            ),
            mock.patch.object(
                shutil, "copy", side_effect=AssertionError("copy reached")
            ),
            mock.patch.object(
                shutil, "copy2", side_effect=AssertionError("copy2 reached")
            ),
            mock.patch.object(
                os, "replace", side_effect=AssertionError("os.replace reached")
            ),
            mock.patch.object(
                Path, "replace", side_effect=AssertionError("Path.replace reached")
            ),
            mock.patch.object(
                Path, "unlink", side_effect=AssertionError("unlink reached")
            ),
        )
        with ExitStack() as stack:
            sentinels = [stack.enter_context(patcher) for patcher in patchers]
            with self.assertRaises(PermissionError) as raised:
                await operation()
        self.assertEqual(str(raised.exception), DISABLED_MESSAGE)
        for sentinel in sentinels:
            sentinel.assert_not_called()
        self.assertEqual(_filesystem_manifest(self.temp_path), manifest_before)

    def _seed_yaml_state(self, hass, zha_path=_MISSING):
        yaml_state = {}
        if zha_path is not _MISSING:
            yaml_state["zha_custom_quirks_path"] = zha_path
        hass.data[DOMAIN] = {"yaml": yaml_state, "entries": {}}

    def _create_default_quirk(self):
        target = self.temp_path / self.const.DEFAULT_CUSTOM_QUIRKS_DIR
        target.mkdir(parents=True, exist_ok=True)
        (target / self.const.QUIRK_FILENAME).write_bytes(b"read-only fixture")

    def test_auto_install_is_forced_off_for_all_configuration_sources(self):
        cases = (
            ("missing", {}, {}, {}),
            ("yaml_old_true", {self.const.CONF_AUTO_INSTALL_QUIRK: True}, {}, {}),
            ("entry_old_true", {}, {self.const.CONF_AUTO_INSTALL_QUIRK: True}, {}),
            ("options_old_true", {}, {}, {self.const.CONF_AUTO_INSTALL_QUIRK: True}),
            (
                "all_conflicting",
                {self.const.CONF_AUTO_INSTALL_QUIRK: True},
                {self.const.CONF_AUTO_INSTALL_QUIRK: False},
                {self.const.CONF_AUTO_INSTALL_QUIRK: True},
            ),
            ("yaml_null", {self.const.CONF_AUTO_INSTALL_QUIRK: None}, {}, {}),
            ("entry_wrong_type", {}, {self.const.CONF_AUTO_INSTALL_QUIRK: []}, {}),
            ("options_wrong_type", {}, {}, {self.const.CONF_AUTO_INSTALL_QUIRK: {}}),
        )
        for name, yaml_data, entry_data, entry_options in cases:
            with self.subTest(name=name):
                entry = _Entry(entry_data, entry_options)
                hass = _FakeHass(self.temp_path, [entry])
                hass.data[DOMAIN] = {"yaml": yaml_data}
                settings = self.services.get_active_settings(hass, entry)
                self.assertIs(settings[self.const.CONF_AUTO_INSTALL_QUIRK], False)

    def test_invalid_paths_from_each_source_fall_back_without_exceptions(self):
        cases = (
            ("yaml_none", {"yaml": None}),
            ("entry_none", {"data": None}),
            ("options_none", {"options": None}),
            ("yaml_integer", {"yaml": 123}),
            ("entry_list", {"data": []}),
            ("options_mapping", {"options": {}}),
            ("empty", {"options": ""}),
            ("whitespace", {"options": " \t "}),
        )
        for name, values in cases:
            with self.subTest(name=name):
                settings, hass, entry = self._settings(**values)
                self.assertEqual(
                    settings[CONF_PATH],
                    self.const.DEFAULT_CUSTOM_QUIRKS_DIR,
                )
                self.assertFalse(
                    self.services.active_quirks_path_is_valid(hass, entry)
                )

    def test_path_precedence_and_valid_strings_are_deterministic(self):
        settings, hass, entry = self._settings(
            yaml="yaml-quirks",
            data="entry-quirks",
            options="options-quirks",
        )
        self.assertEqual(settings[CONF_PATH], "options-quirks")
        self.assertTrue(self.services.active_quirks_path_is_valid(hass, entry))

        for value, expected in (
            ("relative-quirks", "relative-quirks"),
            ("/config/custom-zha-quirks", "/config/custom-zha-quirks"),
            ("  relative-quirks  ", "relative-quirks"),
        ):
            with self.subTest(value=value):
                settings, hass, entry = self._settings(options=value)
                self.assertEqual(settings[CONF_PATH], expected)
                self.assertTrue(
                    self.services.active_quirks_path_is_valid(hass, entry)
                )

        settings, hass, entry = self._settings(
            yaml="yaml-quirks", data="entry-quirks", options=None
        )
        self.assertEqual(
            settings[CONF_PATH], self.const.DEFAULT_CUSTOM_QUIRKS_DIR
        )
        self.assertFalse(self.services.active_quirks_path_is_valid(hass, entry))

    def test_path_helpers_reject_wrong_types_without_implicit_string_coercion(self):
        for value in (None, True, 123, [], {}, "", " \n ", _StringTrap()):
            with self.subTest(value_type=type(value).__name__):
                self.assertIsNone(self.integration._normalize_quirks_path(value))
                self.assertEqual(
                    self.services.ui_quirks_path(value),
                    "configured ZHA custom quirks directory",
                )

        self.assertEqual(
            self.integration._normalize_quirks_path("relative-quirks"),
            "/config/relative-quirks",
        )
        self.assertEqual(
            self.integration._normalize_quirks_path("/config/relative-quirks/"),
            "/config/relative-quirks",
        )

    def test_quirk_exists_uses_controlled_default_for_corrupt_values(self):
        self._create_default_quirk()
        hass = _FakeHass(self.temp_path)
        for value in (None, True, 123, [], {}, "", " \t ", _StringTrap()):
            with self.subTest(value_type=type(value).__name__):
                self.assertTrue(self.services.quirk_exists(hass, value))
        self.assertFalse(self.services.quirk_exists(hass, "other-quirks"))

    async def test_install_is_denied_before_every_path_or_write_sink(self):
        hass = _FakeHass(self.temp_path)
        for target in self._writer_targets():
            with self.subTest(target_type=type(target).__name__, target=target):
                await self._assert_denied_before_sinks(
                    lambda target=target: self.services.async_install_quirk(
                        hass, target, overwrite=False
                    )
                )

    async def test_overwrite_is_denied_before_every_path_or_write_sink(self):
        hass = _FakeHass(self.temp_path)
        for target in self._writer_targets():
            with self.subTest(target_type=type(target).__name__, target=target):
                await self._assert_denied_before_sinks(
                    lambda target=target: self.services.async_install_quirk(
                        hass, target, overwrite=True
                    )
                )

    async def test_remove_is_denied_before_every_path_or_write_sink(self):
        hass = _FakeHass(self.temp_path)
        for target in self._writer_targets():
            with self.subTest(target_type=type(target).__name__, target=target):
                await self._assert_denied_before_sinks(
                    lambda target=target: self.services._remove_quirk(hass, target)
                )

    async def test_old_writing_service_calls_are_unregistered_and_side_effect_free(self):
        hass = _FakeHass(self.temp_path)
        manifest_before = _filesystem_manifest(self.temp_path)
        await self.services.async_register_services(hass)

        for service in (
            self.const.SERVICE_INSTALL_QUIRK,
            self.const.SERVICE_REMOVE_QUIRK,
        ):
            with self.subTest(service=service):
                with self.assertRaises(KeyError):
                    await hass.services.async_call(DOMAIN, service, {})

        self.assertEqual(_filesystem_manifest(self.temp_path), manifest_before)
        self.assertEqual(
            set(hass.services.registered),
            {(DOMAIN, self.const.SERVICE_SHOW_QUIRK_STATUS)},
        )

    async def test_repair_flow_is_none_and_side_effect_free(self):
        repairs = importlib.import_module(
            "custom_components.nowacontrol_hydraulic_sensor.repairs"
        )
        hass = _FakeHass(self.temp_path)
        manifest_before = _filesystem_manifest(self.temp_path)
        self.assertIsNone(
            await repairs.async_create_fix_flow(
                hass, self.const.ISSUE_QUIRK_MISSING
            )
        )
        self.assertEqual(_filesystem_manifest(self.temp_path), manifest_before)

    async def test_yaml_import_uses_framework_flow_without_product_file_write(self):
        target = str(self.temp_path / "caller-selected-target")
        hass = _FakeHass(self.temp_path)
        config = {
            DOMAIN: {
                CONF_PATH: target,
                self.const.CONF_AUTO_INSTALL_QUIRK: True,
            },
            "zha": {self.const.ZHA_CONF_CUSTOM_QUIRKS_PATH: target},
        }
        manifest_before = _filesystem_manifest(self.temp_path)
        self.assertTrue(await self.integration.async_setup(hass, config))
        if hass.tasks:
            await asyncio.gather(*hass.tasks)

        self.assertEqual(_filesystem_manifest(self.temp_path), manifest_before)
        self.assertEqual(len(hass.config_entries.flow_calls), 1)
        _args, kwargs = hass.config_entries.flow_calls[0]
        self.assertEqual(kwargs["context"], {"source": "import"})
        self.assertEqual(kwargs["data"], config[DOMAIN])
        self.assertFalse(
            self.services.get_active_settings(hass)[
                self.const.CONF_AUTO_INSTALL_QUIRK
            ]
        )

    async def test_config_entry_setup_never_reaches_product_writer(self):
        entry = _Entry(
            data={
                CONF_PATH: "entry-quirks",
                self.const.CONF_AUTO_INSTALL_QUIRK: True,
            }
        )
        hass = _FakeHass(self.temp_path, [entry])
        self._seed_yaml_state(hass, "entry-quirks")
        manifest_before = _filesystem_manifest(self.temp_path)

        with (
            mock.patch.object(
                self.services,
                "async_install_quirk",
                new=mock.AsyncMock(
                    side_effect=AssertionError("install writer reached")
                ),
            ) as install_writer,
            mock.patch.object(
                self.services,
                "_remove_quirk",
                new=mock.AsyncMock(
                    side_effect=AssertionError("remove writer reached")
                ),
            ) as remove_writer,
        ):
            self.assertTrue(await self.integration.async_setup_entry(hass, entry))

        install_writer.assert_not_awaited()
        remove_writer.assert_not_awaited()
        self.assertEqual(_filesystem_manifest(self.temp_path), manifest_before)

    async def test_config_and_options_flows_persist_but_cannot_activate_writer(self):
        caller_path = str(self.temp_path / "flow-selected-target")
        user_input = {
            CONF_PATH: caller_path,
            self.const.CONF_AUTO_INSTALL_QUIRK: True,
            self.const.CONF_SHOW_NOTIFICATIONS: True,
        }
        manifest_before = _filesystem_manifest(self.temp_path)

        config_flow = self.config_flow.NowaControlHydraulicSensorConfigFlow()
        config_result = await config_flow.async_step_user(dict(user_input))
        self.assertEqual(config_result["data"], user_input)
        config_entry = _Entry(data=config_result["data"])
        config_hass = _FakeHass(self.temp_path, [config_entry])
        self.assertFalse(
            self.services.get_active_settings(config_hass, config_entry)[
                self.const.CONF_AUTO_INSTALL_QUIRK
            ]
        )

        options_flow = self.config_flow.NowaControlHydraulicSensorOptionsFlow(
            config_entry
        )
        options_result = await options_flow.async_step_init(dict(user_input))
        self.assertEqual(options_result["data"], user_input)
        options_entry = _Entry(data=config_entry.data, options=options_result["data"])
        options_hass = _FakeHass(self.temp_path, [options_entry])
        self.assertFalse(
            self.services.get_active_settings(options_hass, options_entry)[
                self.const.CONF_AUTO_INSTALL_QUIRK
            ]
        )
        self.assertEqual(_filesystem_manifest(self.temp_path), manifest_before)

    async def test_present_quirk_clears_restart_and_missing_issues(self):
        self._create_default_quirk()
        entry = _Entry(data={self.const.CONF_AUTO_INSTALL_QUIRK: False})
        hass = _FakeHass(self.temp_path, [entry])
        self._seed_yaml_state(hass, self.const.DEFAULT_CUSTOM_QUIRKS_DIR)
        hass.issue_registry[(DOMAIN, self.const.ISSUE_RESTART_REQUIRED)] = {
            "legacy": True
        }
        hass.issue_registry[(DOMAIN, self.const.ISSUE_QUIRK_MISSING)] = {
            "is_fixable": True
        }
        manifest_before = _filesystem_manifest(self.temp_path)

        await self.integration.async_setup_entry(hass, entry)

        self.assertNotIn(
            (DOMAIN, self.const.ISSUE_RESTART_REQUIRED), hass.issue_registry
        )
        self.assertNotIn((DOMAIN, self.const.ISSUE_QUIRK_MISSING), hass.issue_registry)
        self.assertNotIn((DOMAIN, self.const.ISSUE_ZHA_PATH), hass.issue_registry)
        self.assertEqual(_filesystem_manifest(self.temp_path), manifest_before)

    async def test_missing_quirk_clears_restart_and_sets_read_only_issue(self):
        entry = _Entry(data={self.const.CONF_AUTO_INSTALL_QUIRK: False})
        hass = _FakeHass(self.temp_path, [entry])
        self._seed_yaml_state(hass, self.const.DEFAULT_CUSTOM_QUIRKS_DIR)
        hass.issue_registry[(DOMAIN, self.const.ISSUE_RESTART_REQUIRED)] = {
            "legacy": True
        }
        manifest_before = _filesystem_manifest(self.temp_path)

        await self.integration.async_setup_entry(hass, entry)

        self.assertNotIn(
            (DOMAIN, self.const.ISSUE_RESTART_REQUIRED), hass.issue_registry
        )
        missing_issue = hass.issue_registry[
            (DOMAIN, self.const.ISSUE_QUIRK_MISSING)
        ]
        self.assertIs(missing_issue["is_fixable"], False)
        self.assertEqual(_filesystem_manifest(self.temp_path), manifest_before)

    async def test_missing_or_mismatched_zha_path_sets_generic_issue(self):
        self._create_default_quirk()
        for zha_path in (_MISSING, "different-quirks"):
            with self.subTest(zha_path=zha_path):
                entry = _Entry(data={self.const.CONF_AUTO_INSTALL_QUIRK: False})
                hass = _FakeHass(self.temp_path, [entry])
                self._seed_yaml_state(hass, zha_path)
                await self.integration.async_setup_entry(hass, entry)
                issue = hass.issue_registry[(DOMAIN, self.const.ISSUE_ZHA_PATH)]
                self.assertNotIn("translation_placeholders", issue)

    async def test_corrupt_configured_path_is_generic_and_read_only(self):
        raw_marker = "customer-site-a/private-quirks"
        entry = _Entry(
            data={
                CONF_PATH: {"nested": raw_marker},
                self.const.CONF_AUTO_INSTALL_QUIRK: False,
            }
        )
        hass = _FakeHass(self.temp_path, [entry])
        self._seed_yaml_state(hass, self.const.DEFAULT_CUSTOM_QUIRKS_DIR)
        manifest_before = _filesystem_manifest(self.temp_path)

        await self.integration.async_setup_entry(hass, entry)

        self.assertIn((DOMAIN, self.const.ISSUE_ZHA_PATH), hass.issue_registry)
        serialized = repr(hass.issue_registry)
        self.assertNotIn(raw_marker, serialized)
        self.assertEqual(_filesystem_manifest(self.temp_path), manifest_before)

    async def test_old_fixable_issue_is_deterministically_replaced(self):
        repairs = importlib.import_module(
            "custom_components.nowacontrol_hydraulic_sensor.repairs"
        )
        entry = _Entry(data={self.const.CONF_AUTO_INSTALL_QUIRK: False})
        hass = _FakeHass(self.temp_path, [entry])
        self._seed_yaml_state(hass, self.const.DEFAULT_CUSTOM_QUIRKS_DIR)
        hass.issue_registry[(DOMAIN, self.const.ISSUE_QUIRK_MISSING)] = {
            "is_fixable": True,
            "legacy": True,
        }

        await self.integration.async_setup_entry(hass, entry)

        issue = hass.issue_registry[(DOMAIN, self.const.ISSUE_QUIRK_MISSING)]
        self.assertEqual(issue["is_fixable"], False)
        self.assertNotIn("legacy", issue)
        self.assertIsNone(
            await repairs.async_create_fix_flow(
                hass, self.const.ISSUE_QUIRK_MISSING
            )
        )

    async def test_repeated_setup_is_idempotent(self):
        entry = _Entry(data={self.const.CONF_AUTO_INSTALL_QUIRK: False})
        hass = _FakeHass(self.temp_path, [entry])
        self._seed_yaml_state(hass, self.const.DEFAULT_CUSTOM_QUIRKS_DIR)
        manifest_before = _filesystem_manifest(self.temp_path)

        await self.integration.async_setup_entry(hass, entry)
        first_issues = dict(hass.issue_registry)
        first_services = dict(hass.services.registered)
        first_entry_state = dict(hass.data[DOMAIN]["entries"])
        await self.integration.async_setup_entry(hass, entry)

        self.assertEqual(hass.issue_registry, first_issues)
        self.assertEqual(hass.services.registered, first_services)
        self.assertEqual(hass.data[DOMAIN]["entries"], first_entry_state)
        self.assertEqual(_filesystem_manifest(self.temp_path), manifest_before)

    async def test_status_notification_is_framework_state_and_path_free(self):
        raw_marker = "customer-site-b/private-quirks"
        entry = _Entry(data={CONF_PATH: raw_marker})
        hass = _FakeHass(self.temp_path, [entry])
        hass.data[DOMAIN] = {
            "yaml": {CONF_PATH: raw_marker},
            "entries": {},
        }
        manifest_before = _filesystem_manifest(self.temp_path)
        await self.services.async_register_services(hass)
        await hass.services.async_call(DOMAIN, self.const.SERVICE_SHOW_QUIRK_STATUS)

        self.assertEqual(len(self.notifications), 1)
        _notification_hass, message, metadata = self.notifications[0]
        self.assertEqual(message, DISABLED_MESSAGE)
        self.assertNotIn(raw_marker, message)
        self.assertNotIn(str(self.temp_path), message)
        self.assertIn("disabled", metadata["title"])
        self.assertEqual(_filesystem_manifest(self.temp_path), manifest_before)

    def test_translation_diagnostics_are_consistent_and_path_free(self):
        component = REPOSITORY_ROOT / "custom_components" / DOMAIN
        strings = json.loads((component / "strings.json").read_text(encoding="utf-8"))
        de = json.loads(
            (component / "translations" / "de.json").read_text(encoding="utf-8")
        )
        en = json.loads(
            (component / "translations" / "en.json").read_text(encoding="utf-8")
        )
        self.assertEqual(strings, de)
        self.assertEqual(set(strings["issues"]), set(en["issues"]))
        for payload in (strings, de, en):
            issue_text = json.dumps(payload["issues"], ensure_ascii=True)
            self.assertNotIn("{path}", issue_text)
            self.assertNotRegex(issue_text, r"/[U]sers/")
            self.assertNotRegex(issue_text, r"[A-Z]:\\\\[U]sers\\\\")

    def test_runbooks_describe_containment_without_installing_fallback(self):
        runbooks = (
            "github-public-hacs-cutover.md",
            "homeassistant-instance-setup.md",
            "homeassistant-hacs-rollout.md",
        )
        combined = "\n".join(
            (REPOSITORY_ROOT / "docs" / "runbooks" / name).read_text(
                encoding="utf-8"
            )
            for name in runbooks
        )
        self.assertNotIn("nowacontrol_hydraulic_sensor.install_zha_quirk", combined)
        self.assertNotIn("nowacontrol_hydraulic_sensor.remove_zha_quirk", combined)
        self.assertNotIn("Integration installiert den Quirk automatisch", combined)
        self.assertNotIn("Wenn Auto-Install aktiv ist", combined)
        self.assertGreaterEqual(combined.count("Dateiwriter ist deaktiviert"), 3)
        self.assertGreaterEqual(combined.count("Commissioning-Freigabe"), 3)

    def test_service_metadata_exposes_only_read_only_status(self):
        component = REPOSITORY_ROOT / "custom_components" / DOMAIN
        metadata = (
            REPOSITORY_ROOT
            / "custom_components/nowacontrol_hydraulic_sensor/services.yaml"
        ).read_text(encoding="utf-8")
        readme = (component / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("install_zha_quirk:", metadata)
        self.assertNotIn("remove_zha_quirk:", metadata)
        self.assertIn("show_quirk_status:", metadata)
        self.assertIn("NO_PRODUCT_FILE_WRITE", readme)
        self.assertIn("NO_CALLER_CONTROLLED_PATH_WRITE", readme)
        self.assertIn("Config\nEntries, Options und Issue Registry", readme)

    def test_ci_runs_changed_tests_with_external_artifact_paths_and_read_only_token(self):
        workflow = (
            REPOSITORY_ROOT / ".github/workflows/validate-homeassistant.yml"
        ).read_text(encoding="utf-8")
        self.assertIn('- "tests/**"', workflow)
        self.assertIn("${{ runner.temp }}/hyd-ha-01/pycache", workflow)
        self.assertIn("${{ runner.temp }}/hyd-ha-01/artifacts", workflow)
        self.assertIn("permissions:\n  contents: read", workflow)
        self.assertNotRegex(workflow, r"(?m)^\s+[^#\n]*:\s*write\s*$")

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
