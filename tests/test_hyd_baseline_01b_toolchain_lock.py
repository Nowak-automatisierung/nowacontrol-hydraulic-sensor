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


def _strip_markdown_comments(markdown: str) -> str:
    return re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL)


def _normative_markdown_section(markdown: str, title: str) -> str:
    """Return direct content of exactly one level-two normative section."""

    uncommented = _strip_markdown_comments(markdown)
    heading_pattern = re.compile(r"(?m)^(#{1,6})\s+(.+?)\s*#*\s*$")
    headings = list(heading_pattern.finditer(uncommented))
    matches = [
        (index, heading)
        for index, heading in enumerate(headings)
        if len(heading.group(1)) == 2
        and heading.group(2).strip().casefold() == title.casefold()
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one normative section: {title}")

    index, heading = matches[0]
    end = len(uncommented)
    for following in headings[index + 1 :]:
        if len(following.group(1)) <= 2:
            end = following.start()
            break
    section = uncommented[heading.end() : end]

    nested_heading = heading_pattern.search(section)
    if nested_heading:
        section = section[: nested_heading.start()]
    return section.strip()


def _ordered_list_items(section: str) -> list[str]:
    item_pattern = re.compile(
        r"(?ms)^\s*\d+[.)]\s+(.*?)(?=^\s*\d+[.)]\s+|\Z)"
    )
    return [
        re.sub(r"\s+", " ", item.group(1)).strip()
        for item in item_pattern.finditer(section)
    ]


def _assert_sdk_authority_policy(
    test_case: unittest.TestCase, section: str, *, document: str
) -> None:
    items = _ordered_list_items(section)
    if items:
        candidates = [
            item for item in items if "authoritative sdk version" in item.casefold()
        ]
    else:
        normalized_section = re.sub(r"\s+", " ", section).strip()
        candidates = (
            [normalized_section]
            if "authoritative sdk version" in normalized_section.casefold()
            else []
        )
    test_case.assertEqual(
        len(candidates), 1, f"{document}: exactly one SDK authority condition required"
    )
    policy = candidates[0].casefold()

    policy_sentences = [
        sentence.strip()
        for sentence in re.split(r"[.!?](?:\s+|$)", policy)
        if sentence.strip()
    ]
    combined_conditions = [
        sentence
        for sentence in policy_sentences
        if "authoritative sdk version" in sentence
        and "approved owner decision" in sentence
        and "approved primary evidence" in sentence
        and re.search(r"\b(?:must|required|requires)\b", sentence)
        and (
            " and " in sentence
            or "together with" in sentence
            or "both" in sentence
        )
    ]
    test_case.assertEqual(
        len(combined_conditions),
        1,
        f"{document}: owner decision and primary evidence must be one binding condition",
    )
    test_case.assertNotRegex(
        combined_conditions[0],
        r"\b(?:must not|not required|need not|optional|either)\b",
        f"{document}: combined SDK condition is negated or weakened",
    )
    for contradiction in (
        "not binding",
        "not mandatory",
        "not necessary",
        "not needed",
        "not required",
        "need not",
        "may be omitted",
        "can be omitted",
        "non-binding",
        "illustrative",
        "optional",
        "owner decision is sufficient",
        "owner decision alone is sufficient",
        "without approved primary evidence",
    ):
        test_case.assertNotIn(
            contradiction, policy, f"{document}: contradictory SDK condition"
        )

    for insufficient_basis in (
        "owner decision alone",
        "conflict resolution alone",
        "repository history alone",
        "legacy generated tree alone",
        "mannheim test evidence alone",
        "live-system state alone",
        "inference",
        "sdk version number alone",
    ):
        test_case.assertIn(
            insufficient_basis, policy, f"{document}: missing insufficient basis"
        )
    test_case.assertTrue(
        any(
            "owner decision alone" in sentence and "insufficient" in sentence
            for sentence in policy_sentences
        ),
        f"{document}: owner decision alone must be explicitly insufficient",
    )
    for evidence_requirement in (
        "traceable, approved vendor or toolchain source",
        "unambiguously tied to the selected sdk version",
        "verifiable and version-controlled",
        "local installation",
        "filename",
        "derived version statement",
    ):
        test_case.assertIn(
            evidence_requirement, policy, f"{document}: incomplete evidence policy"
        )


def _assert_build_contract_sdk_entry(
    test_case: unittest.TestCase, markdown: str
) -> None:
    entry_conditions = _normative_markdown_section(markdown, "Entry conditions")
    _assert_sdk_authority_policy(
        test_case, entry_conditions, document="build contract Entry conditions"
    )


def _yaml_mapping(text: str, key: str) -> dict[str, str]:
    match = re.search(
        rf"(?m)^{re.escape(key)}:\s*\n(?P<body>(?:^[ \t]+[^\n]*\n?)*)",
        text,
    )
    if not match:
        raise AssertionError(f"missing YAML mapping: {key}")
    mapping: dict[str, str] = {}
    for line in match.group("body").splitlines():
        scalar = re.fullmatch(
            r"\s+([a-z][a-z0-9_]*):\s*['\"]?([^'\"]+?)['\"]?\s*", line
        )
        if scalar:
            mapping[scalar.group(1)] = scalar.group(2)
    return mapping


def _yaml_list_item(text: str, item_id: str) -> dict[str, str]:
    match = re.search(
        rf"(?m)^  - id:\s*{re.escape(item_id)}\s*\n"
        rf"(?P<body>(?:^    [^\n]*\n?)*)",
        text,
    )
    if not match:
        raise AssertionError(f"missing YAML list item: {item_id}")
    item: dict[str, str] = {"id": item_id}
    for line in match.group("body").splitlines():
        scalar = re.fullmatch(
            r"\s+([a-z][a-z0-9_]*):\s*['\"]?([^'\"]+?)['\"]?\s*", line
        )
        if scalar:
            item[scalar.group(1)] = scalar.group(2)
    return item


VALID_SDK_ENTRY = """## Entry conditions

1. The authoritative SDK version must be selected by an approved owner decision
   and supported by approved primary evidence. Approved primary evidence is a
   traceable, approved vendor or toolchain source unambiguously tied to the
   selected SDK version, verifiable and version-controlled. An owner decision
   alone, conflict resolution alone, repository history alone, the legacy
   generated tree alone, Mannheim test evidence alone, live-system state alone,
   inference, or an SDK version number alone is insufficient. A local
   installation, filename, or derived version statement is also insufficient.
"""


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

    def test_authoritative_sdk_requires_owner_decision_and_primary_evidence(
        self,
    ) -> None:
        _assert_build_contract_sdk_entry(self, _read(BUILD_CONTRACT))

    def test_sdk_entry_condition_guard_rejects_non_normative_mutations(
        self,
    ) -> None:
        valid_body = VALID_SDK_ENTRY.removeprefix("## Entry conditions\n")
        invalid_mutations = {
            "comment_only": (
                "# Contract\n\n<!--\n" + VALID_SDK_ENTRY + "\n-->\n\n"
                "## Entry conditions\n\n1. SDK selection remains unresolved.\n"
            ),
            "appendix_only": (
                "# Contract\n\n## Entry conditions\n\n"
                "1. SDK selection remains unresolved.\n\n## Appendix\n\n"
                + valid_body
            ),
            "negated": VALID_SDK_ENTRY
            + "\nThis requirement is illustrative and is not binding.\n",
            "owner_decision_only": (
                "# Contract\n\n## Entry conditions\n\n"
                "1. The authoritative SDK version requires an approved owner "
                "decision alone.\n"
            ),
            "primary_evidence_only": (
                "# Contract\n\n## Entry conditions\n\n"
                "1. The authoritative SDK version requires approved primary "
                "evidence alone.\n"
            ),
            "rationale_only": (
                "# Contract\n\n## Entry conditions\n\n"
                "1. SDK selection remains unresolved.\n\n## Rationale\n\n"
                + valid_body
            ),
            "example_only": (
                "# Contract\n\n## Entry conditions\n\n"
                "1. SDK selection remains unresolved.\n\n## Example\n\n"
                + valid_body
            ),
            "notes_only": (
                "# Contract\n\n## Entry conditions\n\n"
                "1. SDK selection remains unresolved.\n\n### Notes\n\n"
                + valid_body
            ),
        }
        for mutation, document in invalid_mutations.items():
            with self.subTest(mutation=mutation):
                with self.assertRaises(AssertionError):
                    _assert_build_contract_sdk_entry(self, document)

        _assert_build_contract_sdk_entry(self, VALID_SDK_ENTRY)
        reordered_and_rewrapped = """# Contract

## Entry conditions

1. Approved primary evidence, together with an approved owner decision, is
   required to select the authoritative SDK version. A local installation,
   filename, or derived version statement is insufficient. An SDK version number
   alone, inference, live-system state alone, Mannheim test evidence alone, the
   legacy generated tree alone, repository history alone, conflict resolution
   alone, and an owner decision alone are insufficient. The evidence is
   verifiable and version-controlled, unambiguously tied to the selected SDK
   version, and comes from a traceable, approved vendor or toolchain source.
"""
        _assert_build_contract_sdk_entry(self, reordered_and_rewrapped)

    def test_sdk_authority_entry_condition_is_consistent_across_documents(
        self,
    ) -> None:
        contract = _read(BUILD_CONTRACT)
        invariants = _read(INVARIANTS_DOCUMENT)
        manifest = _read(PROVENANCE_MANIFEST)
        _assert_build_contract_sdk_entry(self, contract)
        invariant_policy = _normative_markdown_section(
            invariants, "Binding owner decisions"
        )
        _assert_sdk_authority_policy(
            self, invariant_policy, document="firmware invariants"
        )
        self.assertEqual(
            _yaml_mapping(manifest, "sdk_authority_entry_condition"),
            {
                "approved_owner_decision": "required",
                "approved_primary_evidence": "required",
                "combination": "all",
                "owner_decision_alone": "insufficient",
                "authoritative_sdk_version": "unresolved",
            },
        )
        manifest_requirement = _yaml_list_item(manifest, "sdk_authority")[
            "requirement"
        ].casefold()
        for required_text in (
            "approved owner decision",
            "approved primary evidence",
            "both are required",
            "owner decision alone is insufficient",
        ):
            self.assertIn(required_text, manifest_requirement)
        for document in (contract, invariants):
            self.assertIn("AUTHORITATIVE_SDK_VERSION = UNRESOLVED", document)

    def test_documentation_rollback_covers_complete_pr_and_squash_merge(
        self,
    ) -> None:
        contract = _read(BUILD_CONTRACT)
        for required_text in (
            "Before merge",
            "Finding correction commit",
            "fdd493f0f9e049ad4411b90fcd11e625756e1400",
            "001aad1d38ad2f39f00253a2a9a36208bf3f96e7",
            "reverse order",
            "After a squash merge",
            "resulting squash-merge commit",
        ):
            self.assertIn(required_text, contract)
        self.assertNotIn(
            "requires only reverting its documentation/test commit", contract
        )

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
