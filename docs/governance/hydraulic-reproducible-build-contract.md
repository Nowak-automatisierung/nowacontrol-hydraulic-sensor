# Hydraulic reproducible build contract

Status: Draft, review required. This contract defines evidence required before
any future generator execution or firmware build. It does not authorize those
actions now.

Current enforcement state: `NO GENERATOR RUN`, `NO FIRMWARE BUILD`, no firmware
artifact publication, no release, and no deployment.

## Entry conditions

All entry conditions are mandatory and must be version-controlled before the
first authorized tool invocation:

1. One authoritative SDK version selected by owner decision. The unresolved
   `2025.12.1`/`2025.12.2` conflict must be closed without inference.
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

Rejecting this documentation requires only reverting its documentation/test
commit. It has no firmware, generator, device, RF, Home Assistant runtime, or
deployment rollback action because none is authorized or performed here.
