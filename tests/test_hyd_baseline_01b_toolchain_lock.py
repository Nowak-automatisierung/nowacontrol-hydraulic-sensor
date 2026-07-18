"""Static governance guards for HYD-BASELINE-01B-TOOLCHAIN-LOCK."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_ROOT = REPOSITORY_ROOT / "docs/governance"
PROVENANCE_MANIFEST = GOVERNANCE_ROOT / "hydraulic-firmware-provenance.yaml"
INVARIANTS_DOCUMENT = GOVERNANCE_ROOT / "hydraulic-firmware-invariants.md"
BUILD_CONTRACT = GOVERNANCE_ROOT / "hydraulic-reproducible-build-contract.md"
WORKFLOW = REPOSITORY_ROOT / ".github/workflows/validate-homeassistant.yml"
BASELINE_COMMIT = "9a3e88454fb95ce600e2fbb1049718e137e6b35b"
RE_AUDIT_START_HEAD = "31bd6b1190fe5e7a14d687cf8a94ed6cc4922c18"

SDK_AUTHORITY_CONTRACT = {
    "approved_owner_decision": "REQUIRED",
    "approved_primary_evidence": "REQUIRED",
    "combination": "AND",
    "owner_decision_alone": "INSUFFICIENT",
    "primary_evidence_alone": "INSUFFICIENT",
    "alternative_authority": "PROHIBITED",
    "optional_authority": "PROHIBITED",
    "disjunctive_authority": "PROHIBITED",
    "authoritative_sdk_version": "UNRESOLVED",
}

SDK_AUTHORITY_STRUCTURE_FINGERPRINTS = {
    "build contract": frozenset(
        {
            "0eb6dfc15bd5b91dab00bf3b134e5a3fdb26a431616e127f44759f51ad4ad0f6",
            "4017655132d13504b6b24f1f65f5823c1843af38374aaf73acf2eca8f665bd4d",
            "707f5606ddd8add3b6f7fc6b575389dbb6f471d19cbe692a6e23e3a3d780b13c",
            "8285fd22543bab44ce2110109be9ee27ccf27f2743af98a755e43454eaa94a66",
        }
    ),
    "firmware invariants": frozenset(
        {
            "28d5096ca78e1d46576e175c197ed121beffcd9a8763696f0a4c7d2025163caa",
            "da42bded43a331ef4917ab2a777871db0916f545a1f058cdaa3f1f720e1b4ecb",
        }
    ),
}

SDK_AUTHORITY_POLICY_FINGERPRINTS = frozenset(
    {
        "0f03765cf34207b144cbc6a0e9888357d1a29e6f0e8c7f389e209249e34a4ceb",
        "65a2e61d4bed33ce0eee0a24faad6494f9c1686a870e721ff80149c43eea476f",
        "83ebd461fa3d0575e6c37ae79b68850549361f1b956da326de185b64c0c94bfa",
        "b827b6fb3e01313401e8abe938435e1e979d02e19bfa372f7a8b7b3e19d04e60",
        "c01554e8d3ba4b31a0f6387a468af285ddc2c00d224c2b70eb492fa236efe91e",
        "eb815ca1f6fe50e6b7363d13cbcef4636187a24c49eab084655d47a16d37bd58",
    }
)

RUBY_YAML_LOADER = r"""
input = STDIN.read
stream = Psych.parse_stream(input)
raise "exactly one YAML document required" unless stream.children.length == 1
document = stream.children.first
root = document.root
raise "top-level YAML value must be a mapping" unless root.is_a?(Psych::Nodes::Mapping)

validate = nil
validate = lambda do |node|
  case node
  when Psych::Nodes::Mapping
    keys = {}
    node.children.each_slice(2) do |key, value|
      raise "non-scalar YAML mapping key" unless key.is_a?(Psych::Nodes::Scalar)
      unless key.tag.nil? || key.tag == "tag:yaml.org,2002:str"
        raise "non-string YAML mapping key"
      end
      signature = key.value
      raise "duplicate YAML key: #{key.value}" if keys.key?(signature)
      keys[signature] = true
      validate.call(value)
    end
  when Psych::Nodes::Sequence, Psych::Nodes::Document, Psych::Nodes::Stream
    node.children.each { |child| validate.call(child) }
  when Psych::Nodes::Alias
    raise "YAML aliases are prohibited"
  end
end

validate.call(stream)
sdk_authority_keys = root.children.each_slice(2).count do |key, _value|
  key.value == "sdk_authority_entry_condition"
end
unless sdk_authority_keys == 1
  raise "sdk_authority_entry_condition must occur exactly once at top level"
end

value = YAML.safe_load(
  input,
  permitted_classes: [],
  permitted_symbols: [],
  aliases: false
)
raise "top-level YAML value must be a mapping" unless value.is_a?(Hash)

validate_loaded = nil
validate_loaded = lambda do |loaded|
  case loaded
  when Hash
    loaded.each do |key, child|
      raise "non-string YAML mapping key" unless key.is_a?(String)
      validate_loaded.call(child)
    end
  when Array
    loaded.each { |child| validate_loaded.call(child) }
  end
end
validate_loaded.call(value)
STDOUT.write(JSON.generate(value))
"""

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


def _strip_non_visible_markdown(
    markdown: str, *, strip_inline_code: bool = False
) -> str:
    """Remove Markdown code and closed comments; reject unclosed constructs."""

    visible: list[str] = []
    in_comment = False
    fence: tuple[str, int] | None = None
    list_content_indent: int | None = None

    def indentation_width(text: str) -> int:
        width = 0
        for character in text:
            if character == " ":
                width += 1
            elif character == "\t":
                width += 4 - (width % 4)
            else:
                break
        return width

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
            list_item = re.match(
                r"^(?: {0,3})(?:\d+[.)]|[-+*])[ \t]+", visible_body
            )
            if list_item:
                list_content_indent = indentation_width(list_item.group(0))
            elif visible_body.strip():
                indentation = indentation_width(visible_body)
                code_indent = (
                    list_content_indent + 4
                    if list_content_indent is not None
                    else 4
                )
                if indentation >= code_indent:
                    visible.append(line_ending)
                    continue
                if (
                    list_content_indent is not None
                    and indentation < list_content_indent
                ):
                    list_content_indent = None
                    if indentation >= 4:
                        visible.append(line_ending)
                        continue
            visible.append(visible_body + line_ending)
    if fence is not None:
        raise AssertionError("unclosed Markdown fence")
    if in_comment:
        raise AssertionError("unclosed HTML comment")

    without_fences_or_comments = "".join(visible)
    if not strip_inline_code:
        return without_fences_or_comments
    without_inline_code: list[str] = []
    cursor = 0
    inline_opener = re.compile(r"`+")
    while cursor < len(without_fences_or_comments):
        opener = inline_opener.search(without_fences_or_comments, cursor)
        if opener is None:
            without_inline_code.append(without_fences_or_comments[cursor:])
            break
        marker = opener.group(0)
        closer_pattern = re.compile(
            rf"(?<!`){re.escape(marker)}(?!`)"
        )
        closer = closer_pattern.search(without_fences_or_comments, opener.end())
        if closer is None:
            without_inline_code.append(without_fences_or_comments[cursor:])
            break
        without_inline_code.append(without_fences_or_comments[cursor:opener.start()])
        hidden = without_fences_or_comments[opener.start():closer.end()]
        without_inline_code.append(
            "".join(character if character in "\r\n" else " " for character in hidden)
        )
        cursor = closer.end()
    return "".join(without_inline_code)


def _visible_markdown_headings(visible: str) -> list[tuple[int, int, int, str]]:
    """Parse visible ATX and Setext headings with their document spans."""

    headings: list[tuple[int, int, int, str]] = []
    previous: tuple[int, str] | None = None
    offset = 0
    for raw_line in visible.splitlines(keepends=True):
        body = raw_line.rstrip("\r\n")
        atx = re.fullmatch(r" {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t]*", body)
        if atx:
            title = re.sub(r"[ \t]+#+[ \t]*$", "", atx.group(2) or "").strip()
            headings.append((offset, offset + len(raw_line), len(atx.group(1)), title))
            previous = None
        else:
            setext = re.fullmatch(r" {0,3}(=+|-+)[ \t]*", body)
            if setext and previous is not None:
                start, title = previous
                headings.append(
                    (
                        start,
                        offset + len(raw_line),
                        1 if body.lstrip()[0] == "=" else 2,
                        title.strip(),
                    )
                )
                previous = None
            elif (
                body.strip()
                and not body.startswith(("    ", "\t"))
                and not re.match(r" {0,3}(?:\d+[.)]|[-+*])[ \t]+", body)
            ):
                previous = (offset, body)
            else:
                previous = None
        offset += len(raw_line)
    return headings


def _markdown_section_bounds(
    markdown: str,
    title: str,
    level: int,
    *,
    direct_only: bool,
    already_visible: bool = False,
) -> tuple[str, int, int]:
    """Return visible Markdown and the structurally selected section bounds."""

    visible = markdown if already_visible else _strip_non_visible_markdown(markdown)
    headings = _visible_markdown_headings(visible)
    matches = [
        (index, heading)
        for index, heading in enumerate(headings)
        if heading[2] == level and heading[3].casefold() == title.casefold()
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one section: {title}")

    index, heading = matches[0]
    end = len(visible)
    for following in headings[index + 1 :]:
        if direct_only or following[2] <= level:
            end = following[0]
            break
    return visible, heading[1], end


def _normative_markdown_section(markdown: str, title: str) -> str:
    """Return direct content of exactly one level-two normative section."""

    visible, start, end = _markdown_section_bounds(
        markdown, title, 2, direct_only=True
    )
    return visible[start:end].strip()


def _markdown_section_at_level(markdown: str, title: str, level: int) -> str:
    """Return one heading section, including its nested subsections."""

    visible, start, end = _markdown_section_bounds(
        markdown, title, level, direct_only=False
    )
    return visible[start:end].strip()


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


def _git_commit_parents(
    base: str, chronological: tuple[str, ...]
) -> dict[str, tuple[str, ...]]:
    """Return the observed parent tuple for every commit in one candidate span."""

    if not chronological:
        raise AssertionError("missing pre-merge commit span")
    parents: dict[str, tuple[str, ...]] = {}
    for commit in chronological:
        record = subprocess.check_output(
            ["git", "rev-list", "--parents", "-n", "1", commit],
            cwd=REPOSITORY_ROOT,
            text=True,
        ).split()
        if not record or record[0] != commit:
            raise AssertionError("ambiguous pre-merge commit record")
        parents[commit] = tuple(record[1:])
    if base not in parents[chronological[0]]:
        raise AssertionError("pre-merge span does not start at BASE_SHA")
    return parents


def _validated_pre_merge_revert_order(
    *,
    base: str,
    head: str,
    parents: dict[str, tuple[str, ...]],
    candidate_order: tuple[str, ...],
) -> tuple[str, ...]:
    """Validate one complete linear BASE..HEAD span and its exact reverse order."""

    expected_order: list[str] = []
    seen: set[str] = set()
    current = head
    while current != base:
        if current in seen or current not in parents:
            raise AssertionError("missing, foreign, or ambiguous pre-merge commit")
        seen.add(current)
        commit_parents = parents[current]
        if len(commit_parents) != 1:
            raise AssertionError("non-linear pre-merge history")
        expected_order.append(current)
        current = commit_parents[0]
    if not expected_order or tuple(expected_order) != candidate_order:
        raise AssertionError("pre-merge revert order is incomplete or not exact reverse")
    return tuple(expected_order)


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
    test_case: unittest.TestCase,
    section: str,
    *,
    document: str,
) -> str:
    required_authorities = tuple(
        key.replace("_", " ")
        for key, value in SDK_AUTHORITY_CONTRACT.items()
        if value == "REQUIRED"
    )
    test_case.assertEqual(
        required_authorities,
        ("approved owner decision", "approved primary evidence"),
        f"{document}: canonical authority contract changed",
    )
    test_case.assertEqual(SDK_AUTHORITY_CONTRACT["combination"], "AND")
    for prohibited_field in (
        "alternative_authority",
        "optional_authority",
        "disjunctive_authority",
    ):
        test_case.assertEqual(SDK_AUTHORITY_CONTRACT[prohibited_field], "PROHIBITED")

    items = _ordered_list_items(section)
    candidate_indexes = [
        index
        for index, item in enumerate(items)
        if "authoritative sdk version" in item.casefold()
    ]
    test_case.assertEqual(
        len(candidate_indexes),
        1,
        f"{document}: exactly one SDK authority condition required",
    )
    policy_index = candidate_indexes[0]
    policy = re.sub(r"\s+", " ", items[policy_index]).strip().casefold()
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
            for requirement in ("authoritative sdk version", *required_authorities)
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
    for sentence in policy_sentences:
        sdk_authority_statement = "sdk" in sentence and re.search(
            r"(?:select\w*|authorit\w*|proceed)", sentence
        )
        weakened_authority = (
            "owner decision" in sentence or "primary evidence" in sentence
        ) and re.search(r"\b(?:optional|alternative|either|one of)\b", sentence)
        safe_denial = re.search(
            r"\b(?:insufficient|prohibited|unresolved|blocked|cannot|must not|not allowed)\b",
            sentence,
        )
        evidence_definition = all(
            requirement in sentence
            for requirement in (
                "traceable, approved vendor or toolchain source",
                "selected sdk version",
                "verifiable and version-controlled",
            )
        )
        allowed_projection = (
            sentence in combined_conditions
            or "sdk_authority_entry_condition" in sentence
            or evidence_definition
            or safe_denial
        )
        test_case.assertFalse(
            (sdk_authority_statement or weakened_authority) and not allowed_projection,
            f"{document}: authority statement contradicts canonical AND contract",
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
    policy_fingerprint = hashlib.sha256(
        _normalized_markdown_statement(policy).encode("utf-8")
    ).hexdigest()
    test_case.assertIn(
        policy_fingerprint,
        SDK_AUTHORITY_POLICY_FINGERPRINTS,
        f"{document}: complete SDK authority policy structure is not approved",
    )
    return policy


def _normalized_markdown_statement(text: str) -> str:
    """Normalize visible prose without assuming any SDK version syntax."""

    return (
        re.sub(r"\s+", " ", text)
        .strip(" |\t\r\n")
        .casefold()
        .replace("_", " ")
        .replace("–", "-")
        .replace("—", "-")
    )


def _normative_markdown_statements(
    visible: str,
) -> list[tuple[str, str, str]]:
    """Return heading context, full block, and each visible normative statement."""

    statements: list[tuple[str, str, str]] = []
    heading_stack: list[tuple[int, str]] = []

    def add_block(context: str, block: str) -> None:
        normalized_block = re.sub(r"\s+", " ", block).strip()
        if not normalized_block:
            return
        clauses = re.split(r"(?<=[.!?])(?:\s+|$)|\s*;\s*", normalized_block)
        for clause in clauses:
            if clause.strip():
                statements.append((context, normalized_block, clause.strip()))

    def add_content(context: str, content: str) -> None:
        block_lines: list[str] = []

        def flush() -> None:
            if block_lines:
                add_block(context, " ".join(block_lines))
                block_lines.clear()

        for raw_line in content.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                flush()
                continue
            if stripped.startswith("|") and stripped.endswith("|"):
                flush()
                cells = [cell.strip() for cell in stripped.strip("|").split("|")]
                if cells and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
                    continue
                add_block(context, " | ".join(cells))
                continue
            list_item = re.match(
                r"^ {0,3}(?:\d+[.)]|[-+*])[ \t]+(.*)$", raw_line
            )
            if list_item:
                flush()
                block_lines.append(list_item.group(1).strip())
                continue
            block_lines.append(stripped)
        flush()

    headings = _visible_markdown_headings(visible)
    cursor = 0
    for start, end, level, title in headings:
        context = " > ".join(item[1] for item in heading_stack)
        add_content(context, visible[cursor:start])
        add_block(context, title)
        heading_stack = [item for item in heading_stack if item[0] < level]
        heading_stack.append((level, title))
        cursor = end
    context = " > ".join(item[1] for item in heading_stack)
    add_content(context, visible[cursor:])
    return statements


def _assert_no_additional_sdk_authority(
    test_case: unittest.TestCase,
    visible_document: str,
    *,
    allowed_policy: str,
    document: str,
) -> None:
    """Match the complete visible normative structure against an approved lock."""

    fingerprint = _sdk_authority_structure_fingerprint(
        visible_document,
        allowed_policy=allowed_policy,
    )
    test_case.assertIn(
        fingerprint,
        SDK_AUTHORITY_STRUCTURE_FINGERPRINTS[document],
        f"{document}: visible normative structure changed outside the canonical "
        "SDK authority policy",
    )


def _sdk_authority_structure_fingerprint(
    visible_document: str,
    *,
    allowed_policy: str,
) -> str:
    """Hash every visible normative record except the validated policy block."""

    normalized_policy = _normalized_markdown_statement(allowed_policy)
    records: list[str] = []
    for context, block, statement in _normative_markdown_statements(
        visible_document
    ):
        normalized_block = _normalized_markdown_statement(block)
        if normalized_block == normalized_policy:
            continue
        records.append(
            "\x1f".join(
                (
                    _normalized_markdown_statement(context),
                    normalized_block,
                    _normalized_markdown_statement(statement),
                )
            )
        )
    projection = "\n".join(records).encode("utf-8")
    return hashlib.sha256(projection).hexdigest()


def _assert_build_contract_sdk_entry(
    test_case: unittest.TestCase, markdown: str
) -> None:
    visible = _strip_non_visible_markdown(markdown)
    visible, start, end = _markdown_section_bounds(
        visible,
        "Entry conditions",
        2,
        direct_only=True,
        already_visible=True,
    )
    entry_conditions = visible[start:end].strip("\r\n")
    policy = _assert_sdk_authority_policy(
        test_case,
        entry_conditions,
        document="build contract Entry conditions",
    )
    _assert_no_additional_sdk_authority(
        test_case,
        visible,
        allowed_policy=policy,
        document="build contract",
    )


def _assert_firmware_invariants_sdk_entry(
    test_case: unittest.TestCase, markdown: str
) -> None:
    visible = _strip_non_visible_markdown(markdown)
    visible, start, end = _markdown_section_bounds(
        visible,
        "Binding owner decisions",
        2,
        direct_only=True,
        already_visible=True,
    )
    binding_decisions = visible[start:end].strip("\r\n")
    policy = _assert_sdk_authority_policy(
        test_case,
        binding_decisions,
        document="firmware invariants Binding owner decisions",
    )
    _assert_no_additional_sdk_authority(
        test_case,
        visible,
        allowed_policy=policy,
        document="firmware invariants",
    )


def _yaml_document(text: str) -> dict[str, object]:
    """Fully parse one YAML mapping and reject duplicate mapping keys."""

    result = subprocess.run(
        ["ruby", "-ryaml", "-rjson", "-e", RUBY_YAML_LOADER],
        input=text,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip().splitlines()
        raise AssertionError(detail[0] if detail else "invalid YAML document")
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError("YAML parser returned invalid JSON") from error
    if not isinstance(parsed, dict):
        raise AssertionError("top-level YAML value must be a mapping")
    return parsed


def _yaml_mapping(text: str, key: str) -> dict[str, str]:
    value = _yaml_document(text).get(key)
    if not isinstance(value, dict):
        raise AssertionError(f"missing YAML mapping: {key}")
    if not all(
        isinstance(item_key, str) and isinstance(item, str)
        for item_key, item in value.items()
    ):
        raise AssertionError(f"YAML mapping must contain string scalars: {key}")
    return value


def _yaml_list_item(text: str, item_id: str) -> dict[str, str]:
    values = _yaml_document(text).get("required_follow_up_gates")
    if not isinstance(values, list):
        raise AssertionError("missing YAML list: required_follow_up_gates")
    matches = [
        item
        for item in values
        if isinstance(item, dict) and item.get("id") == item_id
    ]
    if len(matches) != 1:
        raise AssertionError(f"missing YAML list item: {item_id}")
    item = matches[0]
    if not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in item.items()
    ):
        raise AssertionError(f"YAML list item must contain string scalars: {item_id}")
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
        unknown_statuses = re.findall(r"(?m)^\s+status:\s*UNKNOWN\s*$", unknown_block)
        self.assertGreaterEqual(len(unknown_items), 6)
        self.assertEqual(len(unknown_items), len(unknown_statuses))
        self.assertNotRegex(unknown_block, r"(?i)status:\s*verified")

    def test_invariants_preserve_behavior_and_expose_conflicts(self) -> None:
        invariants = _read(INVARIANTS_DOCUMENT)
        for status in (
            "VERIFIED",
            "INFERRED",
            "REQUIRED",
            "UNKNOWN",
            "PROPOSED",
            "VERIFIED_CONFLICT",
        ):
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

    def test_sdk_entry_condition_guard_rejects_structural_authority_bypasses(
        self,
    ) -> None:
        valid_body = VALID_SDK_ENTRY.removeprefix("## Entry conditions\n")
        indented_code = "".join(
            f"    {line}" if line.strip() else line
            for line in valid_body.splitlines(keepends=True)
        )
        invalid_mutations = {
            "indented_markdown_code_block": (
                "# Contract\n\n## Entry conditions\n\n" + indented_code
            ),
            "html_comment_only": (
                "# Contract\n\n<!--\n"
                + VALID_SDK_ENTRY
                + "-->\n\n## Entry conditions\n\n1. SDK selection remains unresolved.\n"
            ),
            "appendix_authority": VALID_SDK_ENTRY
            + "\n## Appendix\n\nVersion 2025.12.1 is authoritative.\n",
            "later_contradictory_section": VALID_SDK_ENTRY
            + "\n## Later rule\n\nRepository history authorizes selection.\n",
            "setext_appendix_authority": VALID_SDK_ENTRY
            + "\nAppendix\n--------\n\nThe legacy tree authorizes selection.\n",
            "additional_owner_only_list": VALID_SDK_ENTRY
            + "\n2. The owner may select the version.\n",
            "additional_optional_authority_list": VALID_SDK_ENTRY
            + "\n2. Authority evidence is optional.\n",
            "additional_version_only_list": VALID_SDK_ENTRY
            + "\n2. Version 2025.12.1 is authoritative.\n",
            "additional_history_list": VALID_SDK_ENTRY
            + "\n2. Repository history authorizes selection.\n",
            "additional_legacy_tree_list": VALID_SDK_ENTRY
            + "\n2. The legacy tree authorizes selection.\n",
            "additional_live_system_list": VALID_SDK_ENTRY
            + "\n2. The live system authorizes selection.\n",
            "additional_mannheim_list": VALID_SDK_ENTRY
            + "\n2. Mannheim authorizes selection.\n",
            "additional_local_installation_list": VALID_SDK_ENTRY
            + "\n2. A local installation authorizes selection.\n",
        }
        for mutation, document in invalid_mutations.items():
            with self.subTest(mutation=mutation):
                with self.assertRaises(AssertionError):
                    _assert_build_contract_sdk_entry(self, document)

    def test_sdk_entry_condition_guard_rejects_hidden_policy_and_basis_records(
        self,
    ) -> None:
        valid_body = VALID_SDK_ENTRY.removeprefix("## Entry conditions\n")
        nested_indented_code = "".join(
            f"       {line}" if line.strip() else line
            for line in valid_body.splitlines(keepends=True)
        )
        invalid_mutations = {
            "nested_indented_markdown_code": (
                "# Contract\n\n## Entry conditions\n\n1. Placeholder policy.\n"
                + nested_indented_code
            ),
            "additional_owner_only_record": VALID_SDK_ENTRY
            + "\n2. Owner decision: APPROVED.\n",
            "additional_version_only_record": VALID_SDK_ENTRY
            + "\n2. SDK version: 2025.12.1.\n",
            "additional_history_record": VALID_SDK_ENTRY
            + "\n2. Repository history: 2025.12.1.\n",
            "additional_legacy_tree_record": VALID_SDK_ENTRY
            + "\n2. Legacy tree: 2025.12.1.\n",
            "additional_live_system_record": VALID_SDK_ENTRY
            + "\n2. Live-system state: 2025.12.1.\n",
            "additional_mannheim_record": VALID_SDK_ENTRY
            + "\n2. Mannheim: 2025.12.1.\n",
            "additional_local_installation_record": VALID_SDK_ENTRY
            + "\n2. Local installation: 2025.12.1.\n",
        }
        for mutation, document in invalid_mutations.items():
            with self.subTest(mutation=mutation):
                with self.assertRaises(AssertionError):
                    _assert_build_contract_sdk_entry(self, document)

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
        _assert_firmware_invariants_sdk_entry(self, invariants)
        _assert_sdk_authority_policy(
            self, invariant_policy, document="firmware invariants"
        )
        self.assertEqual(
            _yaml_mapping(manifest, "sdk_authority_entry_condition"),
            SDK_AUTHORITY_CONTRACT,
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
            "BASE_SHA",
            "HEAD_SHA",
            "complete linear commit span",
            "fdd493f0f9e049ad4411b90fcd11e625756e1400",
            "001aad1d38ad2f39f00253a2a9a36208bf3f96e7",
            "reverse chronological order",
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

    def test_workflow_validates_and_reports_the_exact_event_head(self) -> None:
        workflow = _read(WORKFLOW)
        expected_sha_expression = "${{ github.event.pull_request.head.sha || github.sha }}"
        checkout_match = re.search(
            r"(?ms)^      - name: Checkout\n(?P<body>.*?)(?=^      - name:|\Z)",
            workflow,
        )
        self.assertIsNotNone(checkout_match)
        if checkout_match is None:
            return
        checkout = checkout_match["body"]
        self.assertIn("uses: actions/checkout@v4", checkout)
        self.assertIn(f"ref: {expected_sha_expression}", checkout)
        self.assertIn("fetch-depth: 0", checkout)

        verification_match = re.search(
            r"(?ms)^      - name: Verify exact checkout SHA\n"
            r"(?P<body>.*?)(?=^      - name:|\Z)",
            workflow,
        )
        self.assertIsNotNone(verification_match)
        if verification_match is None:
            return
        verification = verification_match["body"]
        for required_text in (
            f"EXPECTED_SHA: {expected_sha_expression}",
            'ACTUAL_SHA="$(git rev-parse HEAD)"',
            "expected_checkout_sha=%s",
            "actual_checkout_sha=%s",
            'test -n "$EXPECTED_SHA"',
            'test "$ACTUAL_SHA" = "$EXPECTED_SHA"',
        ):
            self.assertIn(required_text, verification)

    def test_sdk_authority_guard_rejects_final_reaudit_bypasses(self) -> None:
        invalid_mutations = {
            "owner_decision_alone_may_proceed": VALID_SDK_ENTRY
            + "\n2. SDK selection may proceed with an approved owner decision alone.\n",
            "primary_evidence_alone_may_proceed": VALID_SDK_ENTRY
            + "\n2. SDK selection may proceed with approved primary evidence alone.\n",
            "only_one_approval_needed": VALID_SDK_ENTRY
            + "\n2. Only one of the two approvals is needed for SDK selection.\n",
            "appendix_exception": VALID_SDK_ENTRY
            + "\n## Appendix\n\nSDK selection may proceed without approved primary evidence.\n",
            "later_exception": VALID_SDK_ENTRY
            + "\n## Exceptions\n\nRepository history may authorize SDK selection.\n",
            "contradictory_second_list": VALID_SDK_ENTRY
            + "\n2. A recorded SDK version is sufficient authority for selection.\n",
            "visible_table_exception": VALID_SDK_ENTRY
            + "\n| SDK selection basis | Authority |\n"
            + "|---|---|\n| Generated tree | sufficient |\n",
            "alternative_authority": VALID_SDK_ENTRY
            + "\n2. Mannheim test evidence is an alternative authority for SDK selection.\n",
            "explicit_or": VALID_SDK_ENTRY
            + "\n2. SDK selection requires approved owner decision OR approved primary evidence.\n",
            "optional_primary_evidence": VALID_SDK_ENTRY
            + "\n2. Approved primary evidence is optional for SDK selection.\n",
            "optional_owner_approval": VALID_SDK_ENTRY
            + "\n2. Approved owner approval is optional for SDK selection.\n",
            "generated_tree_authority": VALID_SDK_ENTRY
            + "\n2. The generated tree authorizes SDK selection.\n",
            "mannheim_authority": VALID_SDK_ENTRY
            + "\n2. Mannheim test evidence authorizes SDK selection.\n",
            "live_system_authority": VALID_SDK_ENTRY
            + "\n2. Live-system state authorizes SDK selection.\n",
            "recorded_version_authority": VALID_SDK_ENTRY
            + "\n2. A recorded SDK version authorizes SDK selection.\n",
            "duplicate_entry_conditions": VALID_SDK_ENTRY
            + "\n## Entry conditions\n\n1. SDK selection remains unresolved.\n",
            "missing_entry_conditions": "# Contract\n\nSDK selection remains unresolved.\n",
            "same_item_owner_decision_alone": VALID_SDK_ENTRY.rstrip()
            + " SDK selection may proceed with an approved owner decision alone.\n",
            "same_item_primary_evidence_alone": VALID_SDK_ENTRY.rstrip()
            + " SDK selection may proceed with approved primary evidence alone.\n",
            "same_item_only_one_approval": VALID_SDK_ENTRY.rstrip()
            + " Only one of the two approvals is needed for SDK selection.\n",
            "unclosed_comment": VALID_SDK_ENTRY + "\n<!-- unclosed comment\n",
        }
        for mutation, document in invalid_mutations.items():
            with self.subTest(mutation=mutation):
                with self.assertRaises(AssertionError):
                    _assert_build_contract_sdk_entry(self, document)

    def test_sdk_authority_guard_rejects_confirmed_approval_record_bypasses(
        self,
    ) -> None:
        invalid_mutations = {
            "owner_decision_approved": "Owner decision: APPROVED.",
            "appendix_owner_approved": "Appendix: Owner: APPROVED.",
            "primary_evidence_omitted": (
                "Approved primary evidence may be omitted."
            ),
            "history_accepted": "History: ACCEPTED.",
            "legacy_tree_approved": "Legacy tree: APPROVED.",
            "mannheim_approved": "Mannheim: APPROVED.",
            "local_installation_approved": "Local installation: APPROVED.",
            "owner_signoff_governs": (
                "Owner sign-off alone governs SDK choice."
            ),
            "bare_version_number": "42",
        }
        for mutation, bypass in invalid_mutations.items():
            with self.subTest(mutation=mutation):
                with self.assertRaises(AssertionError):
                    _assert_build_contract_sdk_entry(
                        self, VALID_SDK_ENTRY + "\n" + bypass + "\n"
                    )

    def test_sdk_authority_guard_rejects_normative_mutation_matrix_in_both_docs(
        self,
    ) -> None:
        def assert_invariants(markdown: str) -> None:
            _assert_firmware_invariants_sdk_entry(self, markdown)

        mutations = {
            "synonym_and_mixed_case": "OWNER CONSENT: aCcEpTeD.",
            "unknown_authority_status": "Owner endorsement: BLESSED.",
            "unordered_list": "- Repository record: APPROVED.",
            "visible_table": (
                "| SDK basis | Status |\n|---|---|\n| Vendor filename | APPROVED |"
            ),
            "prose": "The installed toolchain suffices to choose the SDK.",
            "authority_heading": "## SDK authority: history accepted",
            "nested_subsection": (
                "### SDK selection exception\n\nLegacy output is valid authority."
            ),
            "appendix": "## Appendix\n\nOwner consent can replace source proof.",
            "arbitrary_version_format": (
                "Toolchain release phoenix-rc7 is APPROVED for SDK selection."
            ),
            "pure_version_number": "## SDK authority\n\n42: APPROVED.",
            "explicit_or": (
                "SDK selection requires owner consent OR source evidence."
            ),
            "either_or": (
                "Either owner sign-off or provenance may govern SDK choice."
            ),
            "one_of": "One of the two approvals is sufficient for SDK choice.",
            "optional": "Source proof is optional for SDK selection.",
            "may": "Repository history may govern SDK choice.",
            "can": "The legacy output can establish the selected SDK.",
            "alone": "Owner consent alone controls toolchain selection.",
            "sufficient": "Mannheim test results are sufficient evidence.",
            "without": "SDK selection can proceed without owner consent.",
            "omitted": "Vendor source proof may be omitted.",
            "positive_masked_by_denial": (
                "Owner decision: APPROVED, while history is insufficient."
            ),
        }
        base_documents = {
            "build_contract": (
                VALID_SDK_ENTRY,
                lambda markdown: _assert_build_contract_sdk_entry(self, markdown),
            ),
            "firmware_invariants": (_read(INVARIANTS_DOCUMENT), assert_invariants),
        }
        for document_name, (base, validator) in base_documents.items():
            for mutation, bypass in mutations.items():
                placements = {
                    "before": bypass + "\n\n" + base,
                    "after": base + "\n" + bypass + "\n",
                }
                for placement, document in placements.items():
                    with self.subTest(
                        document=document_name,
                        mutation=mutation,
                        placement=placement,
                    ):
                        with self.assertRaises(AssertionError):
                            validator(document)

    def test_sdk_authority_guard_rejects_synonymous_policy_block_contradictions(
        self,
    ) -> None:
        build_base = _read(BUILD_CONTRACT)
        invariants_base = _read(INVARIANTS_DOCUMENT)
        maintainer_override = (
            "A maintainer sign-off alone suffices to choose the SDK."
        )

        policy_block_contradictions = {
            "maintainer_signoff_alone": maintainer_override,
            "reviewer_approval_sufficient": (
                "Reviewer approval is sufficient for SDK selection."
            ),
            "primary_evidence_omitted": (
                "Primary evidence may be omitted after owner approval."
            ),
            "either_owner_or_evidence": (
                "Either owner approval or primary evidence is sufficient."
            ),
            "one_of_authorities": (
                "One of the following authorities may approve the SDK."
            ),
            "synonymous_owner_approval_selection": (
                "A custodian endorsement by itself warrants adopting the "
                "toolchain release."
            ),
            "synonymous_evidence_sufficient_selection": (
                "Source attestation on its own licenses the toolchain choice."
            ),
            "single_alternative_authority": (
                "One qualifying record is adequate to nominate the release."
            ),
            "owner_without_evidence": (
                "Custodian consent unaccompanied by provenance permits choosing "
                "the toolchain."
            ),
            "repository_history_alone": (
                "The commit ledger by itself licenses toolchain adoption."
            ),
            "legacy_tree_alone": (
                "Legacy generated output independently settles the toolchain "
                "choice."
            ),
            "mannheim_evidence_alone": (
                "Mannheim validation alone warrants the toolchain choice."
            ),
            "live_system_alone": (
                "Running-system state solely determines the toolchain release."
            ),
            "local_installation_alone": (
                "The locally installed package independently establishes the "
                "toolchain release."
            ),
            "filename_alone": (
                "The archive name definitively establishes the toolchain release."
            ),
            "arbitrary_version_format": (
                "Toolchain release phoenix-rc7 is hereby ratified."
            ),
            "pure_version_statement": "42 is the ratified toolchain release.",
        }

        def build_inside_policy(contradiction: str) -> str:
            anchor = "\n2. SDK content checksums"
            return build_base.replace(
                anchor,
                "\n   " + contradiction + anchor,
                1,
            )

        def invariants_inside_policy(contradiction: str) -> str:
            anchor = "\n- `LEGACY_GENERATED_TREE = FORENSIC_REFERENCE`"
            return invariants_base.replace(
                anchor,
                "\n  " + contradiction + anchor,
                1,
            )

        visible_surfaces = {
            "before_policy_block": maintainer_override + "\n\n{base}",
            "after_policy_block": "{base}\n" + maintainer_override + "\n",
            "appendix": (
                "{base}\n## Appendix\n\n" + maintainer_override + "\n"
            ),
            "heading": "{base}\n## " + maintainer_override + "\n",
            "list": "{base}\n- " + maintainer_override + "\n",
            "table": (
                "{base}\n| SDK authority | Rule |\n"
                "|---|---|\n| Maintainer sign-off | sufficient |\n"
            ),
            "record": (
                "{base}\nSDK authority override: " + maintainer_override + "\n"
            ),
            "arbitrary_version": (
                "{base}\nToolchain release comet-2026q3 is approved by reviewer "
                "sign-off alone.\n"
            ),
            "pure_version": "{base}\nApproved SDK: 42\n",
            "inline_code": (
                "{base}\nA `maintainer sign-off alone` suffices to choose the SDK.\n"
            ),
        }

        documents = {
            "build_contract": (
                build_base,
                build_inside_policy,
                lambda markdown: _assert_build_contract_sdk_entry(self, markdown),
            ),
            "firmware_invariants": (
                invariants_base,
                invariants_inside_policy,
                lambda markdown: _assert_firmware_invariants_sdk_entry(
                    self, markdown
                ),
            ),
        }
        for document_name, (base, inside_policy, validator) in documents.items():
            for mutation_name, contradiction in policy_block_contradictions.items():
                with self.subTest(
                    document=document_name,
                    surface="canonical_policy_block",
                    mutation=mutation_name,
                ):
                    with self.assertRaises(AssertionError):
                        validator(inside_policy(contradiction))
            for surface, template in visible_surfaces.items():
                with self.subTest(document=document_name, surface=surface):
                    with self.assertRaises(AssertionError):
                        validator(template.format(base=base))

    def test_sdk_authority_guard_accepts_hidden_and_historical_non_authority(
        self,
    ) -> None:
        bypass = "Owner sign-off alone governs SDK choice."
        historical = (
            "## Historical note\n\n"
            "SDK phoenix-rc7 appeared in an old record. This is descriptive "
            "only and must not authorize or select an SDK.\n"
        )
        additions = (
            "```markdown\n" + bypass + "\n```\n",
            "<!-- " + bypass + " -->\n",
            historical,
        )
        validators = (
            (
                VALID_SDK_ENTRY,
                lambda markdown: _assert_build_contract_sdk_entry(self, markdown),
            ),
            (
                _read(INVARIANTS_DOCUMENT),
                lambda markdown: _assert_firmware_invariants_sdk_entry(
                    self, markdown
                ),
            ),
        )
        for base, validator in validators:
            for addition in additions:
                validator(base + "\n" + addition)

    def test_unclosed_markdown_fences_fail_closed_in_both_governance_documents(
        self,
    ) -> None:
        normative_override = (
            "## SDK authority exception\n\n"
            "Owner decision alone authorizes SDK selection.\n"
        )
        inline_and_table_override = (
            "`Owner decision alone authorizes SDK selection.`\n\n"
            "| SDK authority | Status |\n"
            "|---|---|\n"
            "| Owner decision alone | APPROVED |\n"
        )
        unclosed_fences = {
            "three_backticks_with_language": (
                "```markdown\n" + normative_override
            ),
            "three_backticks_without_language": (
                "```\n" + normative_override
            ),
            "four_backticks_empty_at_eof": "````\n",
            "five_indented_backticks": (
                "   `````markdown\n" + normative_override
            ),
            "four_backticks_with_inline_code_and_table": (
                "````markdown\n" + inline_and_table_override
            ),
            "backticks_with_html_comment": (
                "```markdown\n<!--\n" + normative_override
            ),
            "backticks_not_closed_by_tildes": (
                "```markdown\n" + normative_override + "~~~\n"
            ),
            "four_backticks_not_closed_by_three": (
                "````markdown\n" + normative_override + "```\n"
            ),
            "three_tildes_with_language": (
                "~~~markdown\n" + normative_override
            ),
            "three_tildes_without_language": (
                "~~~\n" + normative_override
            ),
            "four_tildes_empty_at_eof": "~~~~\n",
            "five_indented_tildes": (
                "   ~~~~~markdown\n" + normative_override
            ),
            "four_tildes_with_inline_code_and_table": (
                "~~~~markdown\n" + inline_and_table_override
            ),
            "tildes_with_html_comment": (
                "~~~markdown\n<!--\n" + normative_override
            ),
            "tildes_not_closed_by_backticks": (
                "~~~markdown\n" + normative_override + "```\n"
            ),
            "four_tildes_not_closed_by_three": (
                "~~~~markdown\n" + normative_override + "~~~\n"
            ),
        }
        documents = {
            "build_contract": (
                _read(BUILD_CONTRACT),
                "## Entry conditions",
                lambda markdown: _assert_build_contract_sdk_entry(self, markdown),
            ),
            "firmware_invariants": (
                _read(INVARIANTS_DOCUMENT),
                "## Binding owner decisions",
                lambda markdown: _assert_firmware_invariants_sdk_entry(
                    self, markdown
                ),
            ),
        }

        for document_name, (base, canonical_heading, validator) in documents.items():
            for fence_name, fence in unclosed_fences.items():
                document = base.rstrip("\n") + "\n\n" + fence
                with self.subTest(
                    document=document_name,
                    fence=fence_name,
                    placement="after",
                ):
                    with self.assertRaisesRegex(
                        AssertionError, "unclosed Markdown fence"
                    ):
                        validator(document)

            for marker_name, marker in (
                ("backticks", "```markdown"),
                ("tildes", "~~~markdown"),
            ):
                fence = marker + "\n" + normative_override
                placements = {
                    "before": base.replace(
                        canonical_heading,
                        fence + "\n" + canonical_heading,
                        1,
                    ),
                    "inside": base.replace(
                        canonical_heading,
                        canonical_heading + "\n\n" + fence,
                        1,
                    ),
                    "after": base.rstrip("\n") + "\n\n" + fence,
                }
                for placement, document in placements.items():
                    with self.subTest(
                        document=document_name,
                        fence=marker_name,
                        placement=placement,
                    ):
                        with self.assertRaisesRegex(
                            AssertionError, "unclosed Markdown fence"
                        ):
                            validator(document)

    def test_markdown_fence_controls_preserve_existing_visibility_rules(
        self,
    ) -> None:
        hidden_override = "Owner decision alone authorizes SDK selection.\n"
        closed_fences = {
            "closed_three_backticks": (
                "```markdown\n" + hidden_override + "```\n"
            ),
            "closed_three_tildes": (
                "~~~markdown\n" + hidden_override + "~~~\n"
            ),
            "backticks_ignore_tilde_closer": (
                "```markdown\n" + hidden_override + "~~~\n```\n"
            ),
            "tildes_ignore_backtick_closer": (
                "~~~markdown\n" + hidden_override + "```\n~~~\n"
            ),
            "three_backticks_close_with_four": (
                "```markdown\n" + hidden_override + "````\n"
            ),
            "four_backticks_close_with_five": (
                "````markdown\n" + hidden_override + "`````\n"
            ),
            "three_tildes_close_with_four": (
                "~~~markdown\n" + hidden_override + "~~~~\n"
            ),
            "four_tildes_close_with_five": (
                "~~~~markdown\n" + hidden_override + "~~~~~\n"
            ),
        }
        validators = {
            "build_contract": (
                _read(BUILD_CONTRACT),
                lambda markdown: _assert_build_contract_sdk_entry(self, markdown),
            ),
            "firmware_invariants": (
                _read(INVARIANTS_DOCUMENT),
                lambda markdown: _assert_firmware_invariants_sdk_entry(
                    self, markdown
                ),
            ),
        }
        for document_name, (base, validator) in validators.items():
            for fence_name, fence in closed_fences.items():
                with self.subTest(document=document_name, fence=fence_name):
                    validator(base.rstrip("\n") + "\n\n" + fence)

        prose_with_fence_characters = (
            "Normal prose containing ``` backticks does not open a fence.\n",
            "Normal prose containing ~~~~ tildes does not open a fence.\n",
        )
        for prose in prose_with_fence_characters:
            with self.subTest(prose=prose):
                self.assertEqual(_strip_non_visible_markdown(prose), prose)

    def test_sdk_authority_guard_rejects_all_visible_normative_surfaces_in_both_docs(
        self,
    ) -> None:
        build_base = _read(BUILD_CONTRACT)
        invariants_base = _read(INVARIANTS_DOCUMENT)
        mutations = {
            "visible_inline_code": (
                "`SDK selection may proceed with an approved owner decision alone.`"
            ),
            "heading": "### Approved SDK: phoenix-rc7",
            "subheading": (
                "#### Toolchain selection\n\nUse SDK phoenix-rc7."
            ),
            "unordered_list": "- SDK: phoenix-rc7",
            "ordered_list": "2. Adopt SDK phoenix-rc7.",
            "table": (
                "| SDK | Status |\n|---|---|\n| phoenix-rc7 | APPROVED |"
            ),
            "prose": "Use SDK phoenix-rc7.",
            "sdk_record": "SDK: phoenix-rc7",
            "toolchain_record": "Toolchain: phoenix-rc7",
            "plain_version_record": "Version: 2025.12.1.",
            "version_status_record": "2025.12.1: APPROVED.",
            "pure_version_value": "2025.12.1",
            "sdk_name": "Gecko SDK phoenix-rc7 is official.",
            "unknown_positive_verb": "Adopt SDK phoenix-rc7.",
            "unknown_positive_adjective": "SDK phoenix-rc7 is official.",
            "unknown_positive_modality": "The SDK shall be phoenix-rc7.",
            "chosen_sdk": "The chosen SDK is phoenix-rc7.",
            "owner_only": "Owner decision alone authorizes SDK selection.",
            "evidence_only": "Primary evidence alone authorizes SDK selection.",
            "owner_optional": "Owner approval is optional for SDK selection.",
            "evidence_optional": "Source proof is optional for SDK selection.",
            "either_or": (
                "Either owner sign-off or source proof may govern SDK selection."
            ),
            "explicit_or": "Owner approval OR source proof selects the SDK.",
            "one_of": "One of owner approval and source proof selects the SDK.",
            "history": "Repository history: APPROVED.",
            "legacy_tree": "Legacy Generated Tree: APPROVED.",
            "mannheim": "Mannheim: APPROVED.",
            "live_system": "Live-System: APPROVED.",
            "local_installation": "Local installation: APPROVED.",
            "filename": "Filename: gecko-sdk.zip.",
            "derived_version": "Derived version: 2025.12.1.",
            "dispensable_evidence": "Source proof is dispensable.",
        }

        def build_placements(mutation: str) -> dict[str, str]:
            return {
                "before": build_base.replace(
                    "## Entry conditions",
                    mutation + "\n\n## Entry conditions",
                    1,
                ),
                "inside": build_base.replace(
                    "\n## Generation gate",
                    "\n" + mutation + "\n\n## Generation gate",
                    1,
                ),
                "after": build_base + "\n" + mutation + "\n",
            }

        def invariants_placements(mutation: str) -> dict[str, str]:
            return {
                "before": invariants_base.replace(
                    "## Binding owner decisions",
                    mutation + "\n\n## Binding owner decisions",
                    1,
                ),
                "inside": invariants_base.replace(
                    "\n## Hardware, clock, antenna, and RF invariants",
                    "\n" + mutation
                    + "\n\n## Hardware, clock, antenna, and RF invariants",
                    1,
                ),
                "after": invariants_base + "\n" + mutation + "\n",
            }

        documents = {
            "build_contract": (
                build_placements,
                lambda markdown: _assert_build_contract_sdk_entry(self, markdown),
            ),
            "firmware_invariants": (
                invariants_placements,
                lambda markdown: _assert_firmware_invariants_sdk_entry(
                    self, markdown
                ),
            ),
        }
        for mutation_name, mutation in mutations.items():
            for document_name, (placements, validator) in documents.items():
                for placement, document in placements(mutation).items():
                    with self.subTest(
                        mutation=mutation_name,
                        document=document_name,
                        placement=placement,
                    ):
                        with self.assertRaises(AssertionError):
                            validator(document)

    def test_sdk_authority_guard_rejects_visible_inline_code(self) -> None:
        inline_override = (
            "`SDK selection may proceed with an approved owner decision alone.`"
        )
        build_contract = VALID_SDK_ENTRY + "\n" + inline_override + "\n"
        invariants = _read(INVARIANTS_DOCUMENT) + "\n" + inline_override + "\n"
        with self.assertRaises(AssertionError):
            _assert_build_contract_sdk_entry(self, build_contract)
        with self.assertRaises(AssertionError):
            _assert_firmware_invariants_sdk_entry(self, invariants)

    def test_sdk_authority_contract_is_canonical_and_machine_readable(self) -> None:
        self.assertEqual(
            _yaml_mapping(_read(PROVENANCE_MANIFEST), "sdk_authority_entry_condition"),
            SDK_AUTHORITY_CONTRACT,
        )
        for document in (BUILD_CONTRACT, INVARIANTS_DOCUMENT):
            self.assertIn("sdk_authority_entry_condition", _read(document))

    def test_yaml_guard_rejects_duplicate_keys_and_incomplete_parses(self) -> None:
        manifest = _read(PROVENANCE_MANIFEST)
        owner_entry = "  approved_owner_decision: REQUIRED\n"
        self.assertIn(owner_entry, manifest)
        invalid_manifests = {
            "duplicate_sdk_authority_top_level": manifest
            + "\nsdk_authority_entry_condition: {}\n",
            "duplicate_tagged_sdk_authority_top_level": manifest
            + "\n!!str sdk_authority_entry_condition: {}\n",
            "duplicate_other_top_level": "schema_version: duplicate\n" + manifest,
            "duplicate_nested_authority_key": manifest.replace(
                owner_entry, owner_entry + owner_entry, 1
            ),
            "malformed_trailing_yaml": manifest + "\ninvalid: [\n",
            "multiple_yaml_documents": manifest + "\n---\nschema_version: 2.0.0\n",
        }
        for mutation, document in invalid_manifests.items():
            with self.subTest(mutation=mutation):
                with self.assertRaises(AssertionError):
                    _yaml_mapping(document, "sdk_authority_entry_condition")

    def test_yaml_guard_rejects_semantic_top_level_duplicates_and_missing_sdk_key(
        self,
    ) -> None:
        manifest = _read(PROVENANCE_MANIFEST)
        renamed_sdk_key = manifest.replace(
            "sdk_authority_entry_condition:\n",
            "renamed_sdk_authority_entry_condition:\n",
            1,
        )
        invalid_manifests = {
            "binary_tag_duplicate_sdk_authority": manifest
            + "\n!!binary "
            + "c2RrX2F1dGhvcml0eV9lbnRyeV9jb25kaXRpb24=: {}\n",
            "integer_semantic_duplicate": manifest + "\n1: first\n01: second\n",
            "boolean_semantic_duplicate": manifest
            + "\ntrue: first\nTRUE: second\n",
            "missing_sdk_authority_top_level": renamed_sdk_key,
        }
        for mutation, document in invalid_manifests.items():
            with self.subTest(mutation=mutation):
                with self.assertRaises(AssertionError):
                    _yaml_document(document)

    def test_pre_merge_rollback_contract_derives_complete_current_span(self) -> None:
        contract = _read(BUILD_CONTRACT)
        before_merge = _markdown_section_at_level(contract, "Before merge", 3)
        normalized = re.sub(r"\s+", " ", before_merge)
        for required_text in (
            "BASE_SHA",
            "HEAD_SHA",
            "BASE_SHA..HEAD_SHA",
            "complete linear commit span",
            "reverse chronological order",
            "exact base tree",
            "foreign",
            "missing",
            "non-linear",
            "ambiguous",
            "fail closed",
        ):
            with self.subTest(required_text=required_text):
                self.assertIn(required_text.casefold(), normalized.casefold())

        chronological = tuple(
            subprocess.check_output(
                ["git", "rev-list", "--reverse", f"{BASELINE_COMMIT}..HEAD"],
                cwd=REPOSITORY_ROOT,
                text=True,
            ).splitlines()
        )
        self.assertGreater(len(chronological), 1)
        self.assertEqual(chronological[-1], subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True
        ).strip())
        self.assertEqual(
            _validated_pre_merge_revert_order(
                base=BASELINE_COMMIT,
                head=chronological[-1],
                parents=_git_commit_parents(BASELINE_COMMIT, chronological),
                candidate_order=tuple(reversed(chronological)),
            ),
            tuple(reversed(chronological)),
        )

    def test_pre_merge_rollback_order_mutations_fail_closed(self) -> None:
        chronological = ("commit-1", "commit-2", "commit-3")
        parents = {
            "commit-1": ("base",),
            "commit-2": ("commit-1",),
            "commit-3": ("commit-2",),
        }
        valid_order = tuple(reversed(chronological))
        self.assertEqual(
            _validated_pre_merge_revert_order(
                base="base",
                head="commit-3",
                parents=parents,
                candidate_order=valid_order,
            ),
            valid_order,
        )
        invalid_cases = {
            "wrong_order": (parents, ("commit-1", "commit-2", "commit-3")),
            "shortened_first": (parents, ("commit-3", "commit-2")),
            "shortened_last": (parents, ("commit-2", "commit-1")),
            "foreign_commit": (parents, ("commit-3", "foreign", "commit-1")),
            "non_linear": (
                {**parents, "commit-2": ("commit-1", "side")},
                valid_order,
            ),
            "ambiguous_cycle": (
                {**parents, "commit-1": ("commit-3",)},
                valid_order,
            ),
        }
        for case, (case_parents, candidate_order) in invalid_cases.items():
            with self.subTest(case=case):
                with self.assertRaises(AssertionError):
                    _validated_pre_merge_revert_order(
                        base="base",
                        head="commit-3",
                        parents=case_parents,
                        candidate_order=candidate_order,
                    )

    def test_external_pre_merge_revert_restores_exact_base_tree(self) -> None:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True
        ).strip()
        commits = subprocess.check_output(
            ["git", "rev-list", f"{BASELINE_COMMIT}..{head}"],
            cwd=REPOSITORY_ROOT,
            text=True,
        ).splitlines()
        self.assertGreater(len(commits), 1)
        with tempfile.TemporaryDirectory(prefix="hyd-rollback-") as temporary:
            clone = Path(temporary) / "repository"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--no-local",
                    "--no-hardlinks",
                    str(REPOSITORY_ROOT),
                    str(clone),
                ],
                check=True,
            )
            subprocess.run(["git", "checkout", "--quiet", head], cwd=clone, check=True)
            for commit in commits:
                subprocess.run(
                    ["git", "revert", "--no-commit", commit], cwd=clone, check=True
                )
            restored_tree = subprocess.check_output(
                ["git", "write-tree"], cwd=clone, text=True
            ).strip()
            base_tree = subprocess.check_output(
                ["git", "rev-parse", f"{BASELINE_COMMIT}^{{tree}}"],
                cwd=clone,
                text=True,
            ).strip()
            self.assertEqual(restored_tree, base_tree)

    def test_short_rollback_leaves_workflow_diff_and_base_tree_mismatch(self) -> None:
        historical_head = "834e84f3781c3ecec2b29373951bf0973078b4b8"
        commits = subprocess.check_output(
            ["git", "rev-list", f"{BASELINE_COMMIT}..{historical_head}"],
            cwd=REPOSITORY_ROOT,
            text=True,
        ).splitlines()
        self.assertEqual(len(commits), 5)
        with tempfile.TemporaryDirectory(prefix="hyd-short-rollback-") as temporary:
            clone = Path(temporary) / "repository"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--no-local",
                    "--no-hardlinks",
                    str(REPOSITORY_ROOT),
                    str(clone),
                ],
                check=True,
            )
            subprocess.run(
                ["git", "checkout", "--quiet", historical_head], cwd=clone, check=True
            )
            for commit in commits[1:]:
                subprocess.run(
                    ["git", "revert", "--no-commit", commit], cwd=clone, check=True
                )
            remaining = subprocess.check_output(
                ["git", "diff", "--cached", "--name-only", BASELINE_COMMIT],
                cwd=clone,
                text=True,
            ).splitlines()
            self.assertIn(".github/workflows/validate-homeassistant.yml", remaining)
            self.assertNotEqual(
                subprocess.check_output(["git", "write-tree"], cwd=clone, text=True).strip(),
                subprocess.check_output(
                    ["git", "rev-parse", f"{BASELINE_COMMIT}^{{tree}}"],
                    cwd=clone,
                    text=True,
                ).strip(),
            )

    def test_documented_base_tree_is_reproducible(self) -> None:
        base_tree = subprocess.check_output(
            ["git", "rev-parse", f"{BASELINE_COMMIT}^{{tree}}"],
            cwd=REPOSITORY_ROOT,
            text=True,
        ).strip()
        self.assertEqual(base_tree, "45867099131ea8a0a1f2bb99449eec26469c7460")
        self.assertIn(base_tree, _read(BUILD_CONTRACT))

    def test_status_vocabulary_is_identical_and_canonical(self) -> None:
        expected = {
            "VERIFIED",
            "INFERRED",
            "UNKNOWN",
            "PROPOSED",
            "REQUIRED",
            "VERIFIED_CONFLICT",
        }
        manifest = _read(PROVENANCE_MANIFEST)
        invariants = _read(INVARIANTS_DOCUMENT)
        yaml_vocabulary_match = re.search(
            r"(?m)^status_vocabulary:[ \t]*\n"
            r"(?P<body>(?:^[ \t]+-[ \t]+[A-Z_]+[ \t]*\n?)+)",
            manifest,
        )
        self.assertIsNotNone(yaml_vocabulary_match)
        if yaml_vocabulary_match is None:
            return
        yaml_vocabulary = set(
            re.findall(
                r"(?m)^[ \t]+-[ \t]+([A-Z_]+)[ \t]*$",
                yaml_vocabulary_match["body"],
            )
        )
        markdown_vocabulary = set(
            re.findall(
                r"(?m)^\| `([A-Z_]+)` \|",
                _markdown_section_at_level(invariants, "Status vocabulary", 2),
            )
        )
        self.assertEqual(yaml_vocabulary, expected)
        self.assertEqual(markdown_vocabulary, expected)

        used_yaml_statuses = re.findall(
            r"(?m)^[ \t]+status:[ \t]*(\S+)[ \t]*$", manifest
        )
        self.assertTrue(used_yaml_statuses)
        self.assertTrue(set(used_yaml_statuses) <= expected)
        self.assertFalse(
            any(status != status.upper() for status in used_yaml_statuses),
            "YAML status values must use the canonical uppercase spelling",
        )
        self.assertNotRegex(
            invariants,
            r"(?i)`VERIFIED`\s+conflict|`VERIFIED conflict`",
        )

    def test_status_vocabulary_preserves_authority_semantics(self) -> None:
        vocabulary = _markdown_section_at_level(
            _read(INVARIANTS_DOCUMENT), "Status vocabulary", 2
        )
        normalized = re.sub(r"\s+", " ", vocabulary).casefold()
        requirements = {
            "VERIFIED": "reproducible primary or technical evidence",
            "INFERRED": "must not establish toolchain, sdk, product, build, or release authority",
            "UNKNOWN": "must not authorize",
            "PROPOSED": "must not authorize",
            "REQUIRED": "does not mean that the requirement is satisfied",
            "VERIFIED_CONFLICT": "must not be treated as verified or as an authoritative selection",
        }
        for status, meaning in requirements.items():
            with self.subTest(status=status):
                self.assertIn(f"`{status}`".casefold(), normalized)
                self.assertIn(meaning, normalized)


if __name__ == "__main__":
    unittest.main()
