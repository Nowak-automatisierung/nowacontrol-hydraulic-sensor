"""Static governance guards for HYD-BASELINE-01B-TOOLCHAIN-LOCK."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_ROOT = REPOSITORY_ROOT / "docs/governance"
PROVENANCE_MANIFEST = GOVERNANCE_ROOT / "hydraulic-firmware-provenance.yaml"
INVARIANTS_DOCUMENT = GOVERNANCE_ROOT / "hydraulic-firmware-invariants.md"
BUILD_CONTRACT = GOVERNANCE_ROOT / "hydraulic-reproducible-build-contract.md"
WORKFLOW = REPOSITORY_ROOT / ".github/workflows/validate-homeassistant.yml"

PROVENANCE_FILES = {
    Path(
        "sensor-platform/firmware/applications/zigbee-ha/cmake_gcc/"
        "nowacontrol-zigbee-ha.cmake"
    ): "9305e1ea3e91557a798b3a6a49eba946bf410bbcd92c5ee853d4aa506def1ca1",
    Path(
        "sensor-platform/firmware/applications/zigbee-ha/config/zcl/"
        "slc_args.json"
    ): "6765d71b80b2422a573be2ece4f6badfa612636eef59c5af2bf9c449b6a76785",
    Path(
        "sensor-platform/firmware/applications/zigbee-ha/config/zcl/"
        "zcl_config.zap"
    ): "86cd07da180edbd79af37efde22c2e5909d8da9b7b07bec42074170d3b8f3889",
}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _assert_scalar(
    test_case: unittest.TestCase, text: str, key: str, expected: str
) -> None:
    pattern = rf"(?m)^{re.escape(key)}:\s*['\"]?{re.escape(expected)}['\"]?\s*$"
    test_case.assertRegex(text, pattern, f"missing {key}: {expected}")


class HydBaseline01BToolchainLockTests(unittest.TestCase):
    def test_provenance_files_exist_with_locked_sha256(self) -> None:
        for relative_path, expected_hash in PROVENANCE_FILES.items():
            with self.subTest(path=relative_path):
                source = REPOSITORY_ROOT / relative_path
                self.assertTrue(source.is_file())
                self.assertEqual(
                    hashlib.sha256(source.read_bytes()).hexdigest(), expected_hash
                )

    def test_manifest_records_owner_decisions_without_selecting_an_sdk(self) -> None:
        manifest = _read(PROVENANCE_MANIFEST)
        expected_scalars = {
            "schema_version": "1.0.0",
            "baseline_commit": "9a3e88454fb95ce600e2fbb1049718e137e6b35b",
            "authoritative_sdk_version": "unresolved",
            "generated_tree_authority": "forensic_reference",
            "byte_identity_status": "not_demonstrable",
            "semantic_identity_status": "not_demonstrable",
            "security_migration_status": "blocked_separate_change",
            "installed_device_population": "unknown",
            "firmware_build_status": "blocked",
            "release_status": "blocked",
            "repository_transfer_status": "blocked",
        }
        for key, value in expected_scalars.items():
            _assert_scalar(self, manifest, key, value)

        self.assertIn("observed_sdk_versions:", manifest)
        self.assertRegex(manifest, r"(?m)^\s+- ['\"]?2025\.12\.1['\"]?\s*$")
        self.assertRegex(manifest, r"(?m)^\s+- ['\"]?2025\.12\.2['\"]?\s*$")
        self.assertNotRegex(
            manifest,
            r"(?m)^authoritative_sdk_version:\s*['\"]?2025\.12\.[12]",
        )

        for section in (
            "provenance_files:",
            "verified_tool_versions:",
            "inferred_values:",
            "unknown_values:",
            "known_semantic_conflicts:",
            "required_follow_up_gates:",
        ):
            self.assertIn(section, manifest)
        for relative_path, expected_hash in PROVENANCE_FILES.items():
            self.assertIn(relative_path.as_posix(), manifest)
            self.assertIn(expected_hash, manifest)
        self.assertRegex(
            manifest,
            r"(?ms)^location_evidence:\s*\n\s+mannheim:\s*test_evidence_only\s*$",
        )

    def test_unknown_values_are_never_claimed_as_verified(self) -> None:
        manifest = _read(PROVENANCE_MANIFEST)
        match = re.search(
            r"(?ms)^unknown_values:\s*\n(?P<body>.*?)(?=^[a-z][a-z0-9_]*:|\Z)",
            manifest,
        )
        self.assertIsNotNone(match)
        unknown_block = match.group("body")
        unknown_items = re.findall(r"(?m)^\s+- name:\s*\S+\s*$", unknown_block)
        unknown_statuses = re.findall(r"(?m)^\s+status:\s*unknown\s*$", unknown_block)
        self.assertGreaterEqual(len(unknown_items), 6)
        self.assertEqual(len(unknown_items), len(unknown_statuses))
        self.assertNotRegex(unknown_block, r"(?i)status:\s*verified")

    def test_invariants_preserve_behavior_and_expose_conflicts(self) -> None:
        invariants = _read(INVARIANTS_DOCUMENT)
        for status in ("VERIFIED", "REQUIRED", "UNKNOWN", "PROPOSED"):
            self.assertIn(status, invariants)
        for required_text in (
            "EFR32MG24B220F1536IM48",
            "XIAO MG24",
            "38.4 MHz",
            "39 MHz",
            "PB5",
            "PB4",
            "+10 dBm",
            "+3 dBm",
            "0x07FFF800",
            "2026.04.01-1.0",
            "CURRENT_SECURITY_BEHAVIOR = PRESERVE",
            "ZIGBEE_3_MIGRATION = SEPARATE_CHANGE",
            "INSTALLED_DEVICE_POPULATION = UNKNOWN",
            "LEGACY_GENERATED_TREE = FORENSIC_REFERENCE",
            "SEMANTIC_COMPATIBILITY = MANDATORY",
            "FIRMWARE_BUILD = BLOCKED",
            "RELEASE = BLOCKED",
        ):
            self.assertIn(required_text, invariants)
        self.assertRegex(invariants, r"(?i)endpoint.+conflict")
        self.assertRegex(invariants, r"(?i)cluster.+conflict")
        self.assertRegex(invariants, r"(?i)attribute.+conflict")
        self.assertRegex(invariants, r"(?i)reporting.+conflict")

    def test_reproducible_build_contract_requires_all_release_evidence(self) -> None:
        contract = _read(BUILD_CONTRACT)
        for required_text in (
            "authoritative SDK version",
            "SDK content checksums",
            "Simplicity Studio",
            "SLC",
            "ZAP",
            "CMake",
            "compiler",
            "Ninja",
            "generator command",
            "isolated container",
            "two independent clean builds",
            "complete generated-tree diff",
            "SBOM",
            "firmware hash",
            "map file",
            "build log",
            "ZCL invariants",
            "HIL",
            "RF",
            "bootloader",
            "signing",
            "OTA",
            "rollback",
            "Home Assistant contract",
        ):
            self.assertIn(required_text, contract)
        self.assertIn("NO GENERATOR RUN", contract)
        self.assertIn("NO FIRMWARE BUILD", contract)

    def test_location_and_platform_boundaries_are_explicit_and_portable(self) -> None:
        governance_text = "\n".join(
            _read(path)
            for path in (PROVENANCE_MANIFEST, INVARIANTS_DOCUMENT, BUILD_CONTRACT)
        )
        for required_text in (
            "MANNHEIM = TEST_EVIDENCE_ONLY",
            "SENSOR_STANDALONE = REQUIRED",
            "SMARTHOME = OPTIONAL_CONSUMER",
            "MFH = OPTIONAL_CONSUMER",
            "NO_DIRECT_REPOSITORY_COUPLING = REQUIRED",
            "NO_LIVE_SYSTEM_SOURCE_OF_TRUTH = REQUIRED",
        ):
            self.assertIn(required_text, governance_text)

        banned_fragments = (
            "C:" + "/" + "Users" + "/",
            "C:" + "\\" + "Users" + "\\",
            "/" + "Users" + "/",
            "file:" + "//",
            "m" + "nowak",
        )
        for fragment in banned_fragments:
            self.assertNotIn(fragment, governance_text)
        self.assertNotRegex(
            governance_text,
            r"(?i)(?:https?://|\.\.?[/\\])[^\s)]*(?:nowaControl-SmartHome|nowaControl-MFH)",
        )

    def test_governance_paths_trigger_validation(self) -> None:
        workflow = _read(WORKFLOW)
        self.assertEqual(workflow.count('- "docs/governance/**"'), 2)
        self.assertEqual(workflow.count('- "tests/**"'), 2)


if __name__ == "__main__":
    unittest.main()
