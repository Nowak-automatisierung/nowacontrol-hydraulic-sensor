# Hydraulic reproducible build contract

Status: Draft, review required. This contract defines evidence required before
any future generator execution or firmware build. It does not authorize those
actions now.

Current enforcement state: `NO GENERATOR RUN`, `NO FIRMWARE BUILD`, no firmware
artifact publication, no release, and no deployment.

## Entry conditions

All entry conditions are mandatory and must be version-controlled before the
first authorized tool invocation:

1. The authoritative SDK version must be selected by an approved owner decision
   and supported by approved primary evidence. The canonical authority contract
   is the `sdk_authority_entry_condition` mapping in
   `hydraulic-firmware-provenance.yaml`. It requires both through an AND
   combination: neither an owner decision alone nor approved primary evidence
   alone is sufficient, and alternative, optional, or disjunctive authority is
   prohibited. Approved primary evidence must be a traceable, approved vendor or
   toolchain source unambiguously tied to the selected SDK version, verifiable
   and version-controlled—not merely a local installation, filename, or derived
   version statement. The following are insufficient: an owner decision alone;
   conflict resolution alone; repository history alone; the legacy generated
   tree alone; Mannheim test evidence alone; live-system state alone; inference;
   or an SDK version number alone. The unresolved `2025.12.1`/`2025.12.2`
   conflict remains open until both requirements are satisfied.
2. SDK content checksums covering every consumed SDK file, package, template,
   schema, and binary—not merely a marketing version string.
3. Exact pins for Simplicity Studio, SLC, ZAP, CMake, compiler, linker,
   binutils, and Ninja, including platform and distribution hashes.
4. A versioned generator command and complete invocation order for project
   import-free SLC and ZAP processing, CMake configuration, compilation, and
   artifact collection. Every input, option, environment variable, and working
   directory rule must be documented repository-relatively.
5. An isolated container or equivalently reproducible build environment with
   immutable base-image digest, no user profile dependency, no ambient SDK, no
   network-fetched unpinned input, and external disposable output directories.

Until these are approved, `AUTHORITATIVE_SDK_VERSION = UNRESOLVED` and both
generator execution and firmware build remain blocked.

## Generation gate

An authorized generation trial must use a clean copy of the approved inputs and
must never overwrite the forensic reference. It must produce:

- a complete generated-tree diff against the locked legacy tree;
- a file-by-file classification of unchanged, textual-only, semantic, removed,
  and added output;
- proof that repository-relative inputs contain no user, workstation, checkout,
  or site dependency;
- a machine-readable record of generator commands, order, versions, exit
  status, environment digest, input hashes, and output hashes;
- explicit review of SDK, HFXO, TX-power, security, endpoint, cluster,
  attribute, identity, and reporting conflicts.

Generated output is evidence until independently reviewed. A successful tool
exit is not product approval.

## Independent build gate

The approved source and generated output must produce two independent clean builds.
They run in separately created environments and may share only the versioned
input set and immutable environment definition. For each build retain:

- SBOM in an approved machine-readable format;
- firmware hash for every binary and packaging layer;
- map file and size report;
- complete build log with tool versions and sanitized repository-relative paths;
- compiler, linker, and post-processing command records;
- generated-tree manifest and input manifest;
- a comparison report explaining every byte difference.

Byte-identical results are preferred. If byte identity is not achieved, the
non-determinism must be isolated and justified before semantic comparison.
Historical byte identity remains not demonstrable without an approved
historical firmware artifact.

## Semantic compatibility gate

`SEMANTIC_COMPATIBILITY = MANDATORY`. The following ZCL invariants require an
approved expected matrix and automated comparison for both clean builds:

- device role, profile, endpoint, device type, server/client cluster list, and
  manufacturer codes;
- all exposed attributes, types, access, defaults, persistence, and reporting;
- ManufacturerName, ModelIdentifier, ZCL SW Build ID, and consumer matching;
- security profile and joining/rejoining behavior;
- HFXO selection, channel mask, TX power, PA configuration, and antenna switch;
- application timing, battery encoding, measurement semantics, and failure
  behavior.

No conflict may be resolved by accepting new generator output implicitly.

## Physical and delivery gates

Artifact comparison is necessary but insufficient. Independent approval needs:

1. HIL evidence on the exact approved chip and physical board configuration.
2. RF evidence for oscillator accuracy, channel behavior, conducted power,
   antenna selection, EIRP budget, and regression limits.
3. A bootloader contract with version, flash layout, slot selection, recovery,
   compatibility, and interrupted-update behavior.
4. A signing contract with key ownership, custody, algorithm, signer audit,
   public-key distribution, verification, revocation, and recovery.
5. An OTA contract with inventory targeting, eligibility, staged rollout,
   integrity, observability, abort conditions, and failure containment.
6. A rollback contract with known-good artifacts, compatibility bounds,
   downgrade policy, recovery channel, and demonstrated device behavior.
7. A Home Assistant contract proving discovery, entities, events, capabilities,
   reporting, reconnect behavior, and compatibility with the versioned Zigbee
   contract.

The installed device population must be established before OTA or rollback can
be planned. Bootloader, signing, OTA, rollback, and Home Assistant contract
evidence must refer to the exact firmware hash under review.

## Governance and platform gates

- `MANNHEIM = TEST_EVIDENCE_ONLY`. Mannheim may identify a portable evidence
  set but must not supply product defaults, identity, paths, or hidden inputs.
- `SENSOR_STANDALONE = REQUIRED`. Sensor build and operation may not depend on
  a consumer platform checkout or service.
- `SMARTHOME = OPTIONAL_CONSUMER`. nowaControl-SmartHome consumes only a
  documented, versioned contract.
- `MFH = OPTIONAL_CONSUMER`. nowaControl-MFH consumes only a documented,
  versioned contract.
- `NO_DIRECT_REPOSITORY_COUPLING = REQUIRED`. No direct source, build, checkout,
  submodule, or generated-file dependency is allowed.
- Permitted integration surfaces are documented Zigbee, entity, event,
  capability, and API contracts.
- Firmware, Home Assistant integration, and platform governance require
  separate approvals and evidence packages.
- `NO_LIVE_SYSTEM_SOURCE_OF_TRUTH = REQUIRED`. Live behavior can supply test
  evidence but cannot replace version-controlled contracts and artifacts.

## Release record and approval

Before a release candidate can be proposed, its review record must bind all
evidence to the baseline commit, source tree, generated-tree hash, environment
digest, SBOM, firmware hash, map file, build log, HIL/RF results, bootloader,
signing, OTA, rollback, and consumer-contract results. Repository transfer and
stable release remain separate blocked decisions until that record passes an
independent review.

## Documentation rollback

### Before merge

Rollback of this unmerged PR means closing or reverting the entire PR. A fixed
list in this document is never the current normative revert list. Immediately
before merge, record `BASE_SHA` as the exact PR base SHA and `HEAD_SHA` as the
exact reviewed PR head SHA, then confirm that neither ref changed while the
procedure was prepared.

Derive the complete linear commit span from `BASE_SHA..HEAD_SHA`. Verify with
`git merge-base --is-ancestor "$BASE_SHA" "$HEAD_SHA"`, obtain the chronological
span with `git rev-list --reverse "$BASE_SHA..$HEAD_SHA"`, and inspect every
record from `git rev-list --parents "$BASE_SHA..$HEAD_SHA"`. The first commit
must have exactly `BASE_SHA` as its single parent; every following commit must
have exactly the preceding span commit as its single parent; the final commit
must equal `HEAD_SHA`. The observed count must equal
`git rev-list --count "$BASE_SHA..$HEAD_SHA"`.

Derive the revert list from the same validated span and revert every commit in
exact reverse chronological order, starting with `HEAD_SHA` and ending with the
first commit after `BASE_SHA`. The reverse list must have the same count and be
the exact reverse of the chronological list. Stop and fail closed before any
revert if there is a foreign, additional, missing, non-linear, repeated, or
ambiguous commit or parent relationship.

Run the complete sequence in an external clean copy with
`git revert --no-commit` and compare `git write-tree` with
`git rev-parse "$BASE_SHA^{tree}"`. Success requires the exact base tree; no
residual file diff is permitted. For the current baseline base SHA
`9a3e88454fb95ce600e2fbb1049718e137e6b35b`, that reproducible base tree is
`45867099131ea8a0a1f2bb99449eec26469c7460`.

The following is a historical five-commit snapshot for the head reviewed before
this repair; it is not a claim about the current or future complete span:

1. `834e84f3781c3ecec2b29373951bf0973078b4b8`.
2. `3d5fb727c282943d496a5b7bcbf62f69b5e27168`.
3. `31bd6b1190fe5e7a14d687cf8a94ed6cc4922c18`.
4. `fdd493f0f9e049ad4411b90fcd11e625756e1400`.
5. `001aad1d38ad2f39f00253a2a9a36208bf3f96e7`.

### After merge

The post-merge procedure depends on the GitHub merge method actually used. It
must use observed commits on `main`; it must not guess a future commit or reuse
old feature-branch SHAs as post-merge rollback targets. Capture the required
SHAs at merge time: record `MAIN_BEFORE` as the exact `main` SHA immediately
before starting any merge. Validate the history before reverting anything, and
fail closed on any mismatch.

#### Squash merge

After GitHub completes the merge, capture the actual new squash commit on
`main`, observed after the merge, as `SQUASH_MAIN_SHA`. Verify that it is the
single new commit for this PR and that its parent is the `main` SHA observed
immediately before the merge. Revert exactly that observed commit with
`git revert "$SQUASH_MAIN_SHA"`.

#### Merge commit

After GitHub completes the merge, capture the actual merge commit on `main` as
`MERGE_MAIN_SHA`. Verify that it has exactly two parents, that its first parent
equals "$MAIN_BEFORE", and that its second-parent history is the reviewed PR
head. Parent 1 is the `main` history, so the documented mainline parent 1
semantics require `git revert -m 1 "$MERGE_MAIN_SHA"`.

#### Rebase merge

Capture "$MAIN_BEFORE" immediately before the merge and "$MAIN_AFTER"
immediately after the merge. Before merging, also record the reviewed feature
commit count, order, and stable `git patch-id --stable` identities; these
identities validate content but are never rollback SHAs.

Verify ancestry with `git merge-base --is-ancestor "$MAIN_BEFORE"
"$MAIN_AFTER"`. Determine the chronological candidate span only with
`git rev-list --reverse --first-parent "$MAIN_BEFORE..$MAIN_AFTER"`. The span
must contain only single-parent commits and must reproduce the reviewed feature
patch-id sequence with the same count and order. Stop fail closed if the span
contains an unexpected or foreign commit, any merge or other non-linear
history, a repeated patch identity, or any other ambiguous mapping.

The verified span contains the commits actually created on `main` by the rebase
merge. Revert those observed commits in reverse chronological order, one
`git revert` at a time. Never output or use old feature-branch SHAs as the
post-merge rebase rollback targets.

This documentation has no firmware, generator, device, RF, Home Assistant
runtime, or deployment rollback action because none is authorized or performed
here.
