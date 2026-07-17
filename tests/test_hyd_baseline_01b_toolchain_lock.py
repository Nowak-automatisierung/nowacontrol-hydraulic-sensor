"""Static governance guards for HYD-BASELINE-01B-TOOLCHAIN-LOCK."""

from __future__ import annotations

import hashlib
from pathlib import Path
import re
import subprocess
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_ROOT = REPOSITORY_ROOT / "docs/governance"
PROVENANCE_MANIFEST = GOVERNANCE_ROOT / "hydraulic-firmware-provenance.yaml"
INVARIANTS_DOCUMENT = GOVERNANCE_ROOT / "hydraulic-firmware-invariants.md"
BUILD_CONTRACT = GOVERNANCE_ROOT / "hydraulic-reproducible-build-contract.md"
WORKFLOW = REPOSITORY_ROOT / ".github/workflows/validate-homeassistant.yml"
BASELINE_COMMIT = "9a3e88454fb95ce600e2fbb1049718e137e6b35b"
RE_AUDIT_START_HEAD = "31bd6b1190fe5e7a14d687cf8a94ed6cc4922c18"

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


def _strip_non_visible_markdown(markdown: str) -> str:
    """Remove fenced code and HTML comments, including unclosed constructs."""

    visible: list[str] = []
    in_comment = False
    fence: tuple[str, int] | None = None
    for raw_line in markdown.splitlines(keepends=True):
        if raw_line.endswith("\r\n"):
            body, line_ending = raw_line[:-2], "\r\n"
        elif raw_line.endswith("\n") or raw_line.endswith("\r"):
            body, line_ending = raw_line[:-1], raw_line[-1]
        else:
            body, line_ending = raw_line, ""

        if fence is not None:
            character, minimum_length = fence
            if re.fullmatch(
                rf" {{0,3}}{re.escape(character)}{{{minimum_length},}}[ \t]*",
                body,
            ):
                fence = None
            visible.append(line_ending)
            continue

        pieces: list[str] = []
        cursor = 0
        while cursor < len(body):
            if in_comment:
                comment_end = body.find("-->", cursor)
                if comment_end < 0:
                    cursor = len(body)
                else:
                    in_comment = False
                    cursor = comment_end + 3
                continue

            comment_start = body.find("<!--", cursor)
            if comment_start < 0:
                pieces.append(body[cursor:])
                cursor = len(body)
            else:
                pieces.append(body[cursor:comment_start])
                in_comment = True
                cursor = comment_start + 4

        visible_body = "".join(pieces)
        opener = re.fullmatch(r" {0,3}(`{3,}|~{3,})(.*)", visible_body)
        if opener and not (
            opener.group(1).startswith("`") and "`" in opener.group(2)
        ):
            marker = opener.group(1)
            fence = (marker[0], len(marker))
            visible.append(line_ending)
        else:
            visible.append(visible_body + line_ending)
    return "".join(visible)


def _normative_markdown_section(markdown: str, title: str) -> str:
    """Return direct content of exactly one level-two normative section."""

    visible = _strip_non_visible_markdown(markdown)
    heading_pattern = re.compile(r"(?m)^(#{1,6})\s+(.+?)\s*#*\s*$")
    headings = list(heading_pattern.finditer(visible))
    matches = [
        (index, heading)
        for index, heading in enumerate(headings)
        if len(heading.group(1)) == 2
        and heading.group(2).strip().casefold() == title.casefold()
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one normative section: {title}")

    index, heading = matches[0]
    end = len(visible)
    for following in headings[index + 1 :]:
        if len(following.group(1)) <= 2:
            end = following.start()
            break
    section = visible[heading.end() : end]
    nested_heading = heading_pattern.search(section)
    if nested_heading:
        section = section[: nested_heading.start()]
    return section.strip()


def _markdown_section_at_level(markdown: str, title: str, level: int) -> str:
    """Return one heading section, including its nested subsections."""

    visible = _strip_non_visible_markdown(markdown)
    heading_pattern = re.compile(r"(?m)^(#{1,6})\s+(.+?)\s*#*\s*$")
    headings = list(heading_pattern.finditer(visible))
    matches = [
        (index, heading)
        for index, heading in enumerate(headings)
        if len(heading.group(1)) == level
        and heading.group(2).strip().casefold() == title.casefold()
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one section: {title}")

    index, heading = matches[0]
    end = len(visible)
    for following in headings[index + 1 :]:
        if len(following.group(1)) <= level:
            end = following.start()
            break
    return visible[heading.end() : end].strip()


def _repository_manifest(revision: str) -> tuple[int, str]:
    """Reproduce the PR's Git-tree repository-manifest algorithm."""

    tree = subprocess.check_output(
        ["git", "ls-tree", "-rz", "--full-tree", revision],
        cwd=REPOSITORY_ROOT,
    )
    digest = hashlib.sha256()
    entries = 0
    for record in tree.rstrip(b"\0").split(b"\0"):
        metadata, path = record.split(b"\t", 1)
        mode, object_type, object_id = metadata.split()
        if object_type != b"blob":
            raise AssertionError(f"repository manifest encountered {object_type!r}")
        content = subprocess.check_output(
            ["git", "cat-file", "blob", object_id.decode("ascii")],
            cwd=REPOSITORY_ROOT,
        )
        digest.update(mode)
        digest.update(b"\t")
        digest.update(str(len(content)).encode("ascii"))
        digest.update(b"\t")
        digest.update(hashlib.sha256(content).hexdigest().encode("ascii"))
        digest.update(b"\t")
        digest.update(path)
        digest.update(b"\n")
        entries += 1
    return entries, digest.hexdigest()


def _assert_post_merge_rollback_contract(
    test_case: unittest.TestCase, markdown: str
) -> None:
    rollback = _markdown_section_at_level(markdown, "Documentation rollback", 2)
    post_merge = _markdown_section_at_level(rollback, "After merge", 3)
    test_case.assertIn("fail closed", post_merge.casefold())

    requirements = {
        "Squash merge": (
            "actual new squash commit on `main`",
            "observed after the merge",
            "`SQUASH_MAIN_SHA`",
            'git revert "$SQUASH_MAIN_SHA"',
        ),
        "Merge commit": (
            "actual merge commit on `main`",
            "exactly two parents",
            'first parent equals "$MAIN_BEFORE"',
            "mainline parent 1",
            'git revert -m 1 "$MERGE_MAIN_SHA"',
        ),
        "Rebase merge": (
            '"$MAIN_BEFORE" immediately before the merge',
            '"$MAIN_AFTER" immediately after the merge',
            "git merge-base --is-ancestor",
            'git rev-list --reverse --first-parent "$MAIN_BEFORE..$MAIN_AFTER"',
            "patch-id",
            "same count and order",
            "unexpected or foreign commit",
            "non-linear",
            "ambiguous",
            "reverse chronological order",
            "old feature-branch SHAs",
        ),
    }
    for heading, required_texts in requirements.items():
        method = _markdown_section_at_level(post_merge, heading, 4)
        normalized_method = re.sub(r"\s+", " ", method)
        for required_text in required_texts:
            test_case.assertIn(
                re.sub(r"\s+", " ", required_text),
                normalized_method,
                f"{heading}: incomplete post-merge rollback contract",
            )

    test_case.assertNotRegex(
        post_merge,
        r"\b[0-9a-f]{40}\b",
        "post-merge rollback must not predeclare or reuse a commit SHA",
    )


def _validated_rebase_rollback_order(
    *,
    before: str,
    after: str,
    parents: dict[str, tuple[str, ...]],
    patch_ids: dict[str, str],
    expected_patch_ids: tuple[str, ...],
    feature_branch_shas: set[str],
) -> tuple[str, ...]:
    """Validate a linear observed rebase span and return reverse revert order."""

    reverse_span: list[str] = []
    seen: set[str] = set()
    current = after
    while current != before:
        if current in seen or current not in parents:
            raise AssertionError("ambiguous rebase span")
        if current in feature_branch_shas:
            raise AssertionError("old feature-branch SHA used on main")
        seen.add(current)
        commit_parents = parents[current]
        if len(commit_parents) != 1:
            raise AssertionError("non-linear rebase span")
        reverse_span.append(current)
        current = commit_parents[0]

    chronological = tuple(reversed(reverse_span))
    actual_patch_ids = tuple(patch_ids.get(commit, "") for commit in chronological)
    if (
        not chronological
        or len(set(expected_patch_ids)) != len(expected_patch_ids)
        or actual_patch_ids != expected_patch_ids
    ):
        raise AssertionError("unexpected, foreign, or ambiguous rebase commit")
    return tuple(reverse_span)


def _ordered_list_items(section: str) -> list[str]:
    item_pattern = re.compile(
        r"(?ms)^ {0,3}(?:\d+[.)]|[-+*])\s+(.*?)"
        r"(?=^ {0,3}(?:\d+[.)]|[-+*])\s+|^(?=\S)|\Z)"
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
            item
            for item in items
            if "authoritative sdk version" in item.casefold()
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
    policy = re.sub(r"\s+", " ", candidates[0]).strip().casefold()
    normalized_section = re.sub(r"\s+", " ", section).strip().casefold()

    policy_sentences = [
        sentence.strip()
        for sentence in re.split(r"[.!?](?:\s+|$)", policy)
        if sentence.strip()
    ]
    combined_conditions: list[str] = []
    for sentence in policy_sentences:
        if not all(
            requirement in sentence
            for requirement in (
                "authoritative sdk version",
                "approved owner decision",
                "approved primary evidence",
            )
        ) or not re.search(r"\b(?:must|required|requires|mandatory)\b", sentence):
            continue
        owner_index = sentence.index("approved owner decision")
        evidence_index = sentence.index("approved primary evidence")
        connector = sentence[
            min(owner_index, evidence_index) : max(owner_index, evidence_index)
        ]
        jointly_required = bool(
            re.search(r"\b(?:and|together with|as well as)\b", connector)
            or re.search(r"\bboth\b.*\band\b", sentence)
        )
        disjunctive = bool(re.search(r"\b(?:either|or|alternative(?:ly)?)\b", connector))
        if jointly_required and not disjunctive:
            combined_conditions.append(sentence)
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
        "without an approved owner decision",
    ):
        test_case.assertNotIn(
            contradiction,
            normalized_section,
            f"{document}: contradictory SDK condition",
        )

    authority_subject = r"(?:approved\s+)?(?:owner decision|primary evidence)"
    weakening_patterns = (
        rf"\b{authority_subject}\b.{{0,80}}\b(?:is|are|be|becomes?|remains?)\s+"
        r"(?:merely\s+)?(?:an?\s+)?"
        r"(?:optional|alternative|unnecessary|dispensable)\b",
        rf"\b{authority_subject}\b.{{0,80}}\b(?:is|are)\s+not\s+"
        r"(?:required|mandatory|necessary|needed)\b",
        rf"\b{authority_subject}\b.{{0,80}}\b(?:may|can)\s+be\s+"
        r"(?:omitted|waived|replaced|optional|alternative|unnecessary|dispensable)\b",
        rf"\b{authority_subject}\b.{{0,80}}\bneed not\b",
    )
    for pattern in weakening_patterns:
        test_case.assertNotRegex(
            normalized_section,
            pattern,
            f"{document}: owner decision or primary evidence is weakened",
        )

    for sentence in re.split(r"[.!?](?:\s+|$)", normalized_section):
        if "owner decision" not in sentence or "primary evidence" not in sentence:
            continue
        owner_index = sentence.index("owner decision")
        evidence_index = sentence.index("primary evidence")
        connector = sentence[
            min(owner_index, evidence_index) : max(owner_index, evidence_index)
        ]
        test_case.assertNotRegex(
            connector,
            r"\b(?:either|or|alternative(?:ly)?)\b",
            f"{document}: owner decision and primary evidence are alternatives",
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

    def test_sdk_entry_condition_guard_rejects_confirmed_bypasses(self) -> None:
        misleading_entry = """## Entry conditions

1. The authoritative SDK version may be selected without both approvals.
"""
        invalid_mutations = {
            "valid_plus_contradictory_list_item": (
                VALID_SDK_ENTRY
                + "\n2. Approved primary evidence is optional.\n"
            ),
            "fenced_heading_only": (
                "# Contract\n\n```markdown\n" + VALID_SDK_ENTRY + "```\n"
            ),
            "closed_comment_heading_only": (
                "# Contract\n\n<!--\n" + VALID_SDK_ENTRY + "-->\n"
            ),
            "unclosed_comment_heading_only": (
                "# Contract\n\n<!--\n" + VALID_SDK_ENTRY
            ),
            "primary_evidence_optional": (
                VALID_SDK_ENTRY
                + "\n2. The approved primary evidence is optional.\n"
            ),
            "owner_decision_optional": (
                VALID_SDK_ENTRY
                + "\n2. The approved owner decision is optional.\n"
            ),
            "owner_decision_or_primary_evidence": (
                VALID_SDK_ENTRY
                + "\n2. An approved owner decision OR approved primary evidence "
                "is sufficient for SDK selection.\n"
            ),
            "two_competing_sdk_entries": VALID_SDK_ENTRY
            + "\n2. The authoritative SDK version may alternatively be selected "
            "by an approved owner decision alone.\n",
        }
        for mutation, document in invalid_mutations.items():
            with self.subTest(mutation=mutation):
                with self.assertRaises(AssertionError):
                    _assert_build_contract_sdk_entry(self, document)

        visible_plus_code = (
            VALID_SDK_ENTRY + "\n```markdown\n" + misleading_entry + "```\n"
        )
        visible_plus_comment = (
            VALID_SDK_ENTRY + "\n<!--\n" + misleading_entry + "-->\n"
        )
        _assert_build_contract_sdk_entry(self, visible_plus_code)
        _assert_build_contract_sdk_entry(self, visible_plus_comment)

    def test_sdk_entry_condition_guard_accepts_combined_reordered_wrapping(
        self,
    ) -> None:
        combined = """## Entry conditions

1. The authoritative SDK version requires both an approved owner decision and
   approved primary evidence. Approved primary evidence is a traceable, approved
   vendor or toolchain source unambiguously tied to the selected SDK version,
   verifiable and version-controlled. An owner decision alone, conflict
   resolution alone, repository history alone, the legacy generated tree alone,
   Mannheim test evidence alone, live-system state alone, inference, or an SDK
   version number alone is insufficient. A local installation, filename, or
   derived version statement is insufficient.
"""
        reordered = """## Entry conditions

1. Approved primary evidence together with an approved owner decision is
   required before selecting the authoritative SDK version. A filename, derived
   version statement, or local installation is insufficient. An SDK version
   number alone, inference, live-system state alone, Mannheim test evidence
   alone, the legacy generated tree alone, repository history alone, conflict
   resolution alone, and an owner decision alone are insufficient. The evidence
   must be verifiable and version-controlled, unambiguously tied to the selected
   SDK version, and from a traceable, approved vendor or toolchain source.
"""
        _assert_build_contract_sdk_entry(self, combined)
        _assert_build_contract_sdk_entry(self, reordered)

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

    def test_repository_manifest_algorithm_reproduces_independent_values(
        self,
    ) -> None:
        self.assertEqual(
            _repository_manifest(BASELINE_COMMIT),
            (
                203,
                "6684b47e667eac871f0ce73d412f9eeb0a77c97f375bfcd93d3a81f930ff01d3",
            ),
        )
        self.assertEqual(
            _repository_manifest(RE_AUDIT_START_HEAD),
            (
                207,
                "28c6c0bdc55cd5bc071441aaec4b99b2d63e73f278c5408161c850a4457bb356",
            ),
        )

    def test_documentation_rollback_covers_complete_pr_and_all_merge_methods(
        self,
    ) -> None:
        contract = _read(BUILD_CONTRACT)
        for required_text in (
            "Before merge",
            "Finding correction commit",
            "fdd493f0f9e049ad4411b90fcd11e625756e1400",
            "001aad1d38ad2f39f00253a2a9a36208bf3f96e7",
            "reverse order",
        ):
            self.assertIn(required_text, contract)
        self.assertNotIn(
            "requires only reverting its documentation/test commit", contract
        )
        _assert_post_merge_rollback_contract(self, contract)

    def test_documentation_rollback_mutations_fail_closed(self) -> None:
        contract = _read(BUILD_CONTRACT)
        _assert_post_merge_rollback_contract(self, contract)
        invalid_mutations = {
            "only_two_merge_methods": re.sub(
                r"(?ms)^#### Rebase merge\n.*\Z", "", contract
            ),
            "rebase_forward_order": contract.replace(
                "reverse chronological order", "chronological order"
            ),
            "foreign_commit_not_rejected": contract.replace(
                "unexpected or foreign commit", "unexpected commit"
            ),
            "non_linear_not_rejected": contract.replace("non-linear", "unusual"),
            "ambiguous_not_rejected": contract.replace("ambiguous", "unclear"),
            "invented_future_sha": contract
            + "\n0000000000000000000000000000000000000001\n",
            "old_feature_sha": contract
            + "\n31bd6b1190fe5e7a14d687cf8a94ed6cc4922c18\n",
        }
        for mutation, document in invalid_mutations.items():
            with self.subTest(mutation=mutation):
                with self.assertRaises(AssertionError):
                    _assert_post_merge_rollback_contract(self, document)

    def test_rebase_rollback_simulation_reverts_in_reverse_order(self) -> None:
        rollback_order = _validated_rebase_rollback_order(
            before="main-before",
            after="main-r3",
            parents={
                "main-r1": ("main-before",),
                "main-r2": ("main-r1",),
                "main-r3": ("main-r2",),
            },
            patch_ids={
                "main-r1": "patch-1",
                "main-r2": "patch-2",
                "main-r3": "patch-3",
            },
            expected_patch_ids=("patch-1", "patch-2", "patch-3"),
            feature_branch_shas={"feature-1", "feature-2", "feature-3"},
        )
        self.assertEqual(rollback_order, ("main-r3", "main-r2", "main-r1"))

    def test_rebase_rollback_simulation_rejects_foreign_or_ambiguous_history(
        self,
    ) -> None:
        valid_parents = {
            "main-r1": ("main-before",),
            "main-r2": ("main-r1",),
            "main-r3": ("main-r2",),
        }
        valid_patch_ids = {
            "main-r1": "patch-1",
            "main-r2": "patch-2",
            "main-r3": "patch-3",
        }
        cases = {
            "foreign_commit": {
                "parents": valid_parents,
                "patch_ids": {**valid_patch_ids, "main-r2": "foreign-patch"},
                "after": "main-r3",
                "feature_branch_shas": set(),
            },
            "non_linear": {
                "parents": {**valid_parents, "main-r2": ("main-r1", "side")},
                "patch_ids": valid_patch_ids,
                "after": "main-r3",
                "feature_branch_shas": set(),
            },
            "ambiguous_cycle": {
                "parents": {**valid_parents, "main-r1": ("main-r3",)},
                "patch_ids": valid_patch_ids,
                "after": "main-r3",
                "feature_branch_shas": set(),
            },
            "old_feature_sha": {
                "parents": {**valid_parents, "main-r2": ("main-r1",)},
                "patch_ids": valid_patch_ids,
                "after": "main-r3",
                "feature_branch_shas": {"main-r2"},
            },
        }
        for case, values in cases.items():
            with self.subTest(case=case):
                with self.assertRaises(AssertionError):
                    _validated_rebase_rollback_order(
                        before="main-before",
                        after=values["after"],
                        parents=values["parents"],
                        patch_ids=values["patch_ids"],
                        expected_patch_ids=("patch-1", "patch-2", "patch-3"),
                        feature_branch_shas=values["feature_branch_shas"],
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
