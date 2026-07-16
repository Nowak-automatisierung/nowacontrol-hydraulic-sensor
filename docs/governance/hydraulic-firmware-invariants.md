# Hydraulic firmware product invariants

Status: Draft, review required. Baseline: `main` at
`9a3e88454fb95ce600e2fbb1049718e137e6b35b`.

This document records the product contract that can be supported from the
repository without changing firmware, generated files, runtime configuration,
RF behavior, or deployment state. It is normative for future work only after
owner review. The three locked provenance files remain byte-identical to the
baseline and the legacy generated tree remains evidence, not an automatically
authoritative future product definition.

## Status vocabulary

| Status | Meaning |
|---|---|
| `VERIFIED` | Directly observed in the baseline repository and reproducible by a read-only check. It does not by itself grant product authority. |
| `REQUIRED` | Binding owner decision or release condition. Future work must preserve or satisfy it. |
| `UNKNOWN` | Evidence is absent or conflicting. It must not be represented as `VERIFIED`. |
| `PROPOSED` | Candidate future decision with no current authority. It must not change generation, firmware, or release state. |

## Binding owner decisions

- `AUTHORITATIVE_SDK_VERSION = UNRESOLVED` (`REQUIRED`). The authoritative SDK
  version must be selected by an approved owner decision and supported by
  approved primary evidence; both conditions are jointly required. An owner
  decision alone, conflict resolution alone, repository history alone, the
  legacy generated tree alone, Mannheim test evidence alone, live-system state
  alone, inference, or an SDK version number alone are insufficient. Approved
  primary evidence must be a traceable, approved vendor or toolchain source
  unambiguously tied to the selected SDK version, verifiable and
  version-controlled; a local installation, filename, or derived version
  statement is insufficient. Neither `2025.12.1` nor `2025.12.2` is selected by
  this baseline.
- `LEGACY_GENERATED_TREE = FORENSIC_REFERENCE` (`REQUIRED`). Historical
  generator outputs remain unchanged and are not automatically the future
  product contract.
- `SEMANTIC_COMPATIBILITY = MANDATORY` (`REQUIRED`). Byte identity is desirable,
  but historical firmware artifacts are absent, so it is not currently a
  demonstrable release criterion.
- `CURRENT_SECURITY_BEHAVIOR = PRESERVE` (`REQUIRED`). This PR makes no
  Zigbee-security change.
- `ZIGBEE_3_MIGRATION = SEPARATE_CHANGE` (`REQUIRED`). Any migration needs its
  own reviewed contract, tests, risk assessment, and PR.
- `MANNHEIM = TEST_EVIDENCE_ONLY` (`REQUIRED`). Mannheim may label test evidence
  only; it cannot define identity, defaults, paths, or product logic.
- `INSTALLED_DEVICE_POPULATION = UNKNOWN` (`UNKNOWN`). Firmware deployment,
  OTA, and rollback remain blocked.
- `FIRMWARE_BUILD = BLOCKED` and `RELEASE = BLOCKED` (`REQUIRED`) until the
  reproducibility and product gates are satisfied.

## Hardware, clock, antenna, and RF invariants

| Subject | Status | Baseline evidence and invariant |
|---|---|---|
| Chip target | `VERIFIED` | Project descriptors name `EFR32MG24B220F1536IM48`. Future regeneration must use the approved exact part after toolchain authorization. |
| Physical board | `VERIFIED` / `UNKNOWN` | Repository documentation and source comments name `XIAO MG24`; the exact electrical board configuration, oscillator fit, antenna population, and production assembly remain `UNKNOWN`. The board name alone does not settle those facts. |
| HFXO | `VERIFIED` conflict | Architecture documentation states `38.4 MHz`; the preserved oscillator configuration states `39 MHz`. Neither value is selected here. A board-primary source, SDK compatibility evidence, clean builds, and RF evidence are required before resolution. |
| Antenna switch | `VERIFIED` observation | Application source drives `PB5` high as RF-switch enable and `PB4` high for the external antenna. This describes preserved source behavior only; hardware polarity and production antenna selection remain unverified. No RF or antenna change is authorized. |
| TX power | `VERIFIED` conflict | PA configuration contains `+10 dBm`; network steering contains `+3 dBm`. A 20 dBm mapping table is a capability reference, not proof of operational output. Conducted power, final cap, EIRP, and authoritative runtime value remain `UNKNOWN`; Issue #9 remains the separate decision path. |
| Channel mask | `VERIFIED` observation | Network steering contains `0x07FFF800` (Zigbee channels 11 through 26). It remains preserved evidence, not a newly approved deployment default. |

## Zigbee product-contract conflicts

The following conflicts are release blockers. No value in this section may be
chosen merely because it appears newer, generated, or easier to build.

| Surface | `VERIFIED` observations | Required disposition |
|---|---|---|
| Device role | Current project metadata selects a router. The V1 design reference specifies a sleeping end device. | Resolve through a separate product decision and HIL/power validation. |
| Endpoint conflict | The preserved ZAP and generated tree expose endpoints 1, 2, and 3 with HA profile `0x0104` and device ID `0x0302`. The V1 design reference specifies endpoint 1 only and device ID `0x0305`. | Treat both as evidence; approve one semantic contract before generation. |
| Cluster conflict | The preserved tree uses Temperature Measurement `0x0402` on three endpoints plus manufacturer cluster `0xFC10` on endpoint 1. The V1 design reference specifies Pressure Measurement `0x0403`, no manufacturer cluster contract, and no client clusters. | `SEMANTIC_COMPATIBILITY = MANDATORY`; compare firmware, ZHA discovery, and consumer contracts. |
| Attribute conflict | The ZAP source omits Basic application/hardware version and Power Configuration battery values that appear in the legacy generated table and are written by application source. | Do not regenerate until the approved attribute matrix and defaults are explicit. |
| Model identifier | Preserved application/ZAP/quirk evidence uses `Hydraulic Sensor V1`; the V1 design reference uses `hydraulic-sensor-v1`. | Matching identity is release-sensitive and remains unresolved. |
| Reporting conflict | ZAP reportable metadata uses broad `1..65534` intervals; the legacy generated table uses battery `30/300` and temperature `10/60`; the V1 design reference uses pressure `30/300` and battery `3600/43200`. Reportable-change values also differ. | Approve exact per-endpoint, per-attribute reporting values and verify rejoin behavior in HIL. |
| ZCL SW Build ID | Application source and preserved ZAP state `2026.04.01-1.0`. | `VERIFIED` as repository text only. Mapping to any deployed or historical binary is `UNKNOWN`. |

## Security invariant

The current project descriptor requests Zigbee 3.0 security while the preserved
generated device configuration selects Home Automation security for the primary
network. That is a `VERIFIED` semantic conflict. The current generated behavior
must be preserved for this baseline: `CURRENT_SECURITY_BEHAVIOR = PRESERVE`.
Changing it is a migration, not regeneration cleanup:
`ZIGBEE_3_MIGRATION = SEPARATE_CHANGE`.

No key migration, joining-policy change, security-profile change, commissioning
action, flash, or live network test is authorized by this document.

## Bootloader, signing, OTA, and field state

| Surface | Status | Contract |
|---|---|---|
| Bootloader | `UNKNOWN` | An application bootloader interface/component is referenced, but no approved bootloader artifact, slot layout, fallback proof, or HIL evidence is established. Issue #3 remains open. |
| Signing | `UNKNOWN` | No approved signing-key workflow, signer identity, signed firmware, or verification evidence is established. Issue #8 remains open. |
| OTA | `UNKNOWN` / blocked | Documentation and workflow scaffolding do not prove a deployable OTA path. Device inventory, bootloader, signing, rollback, and HIL gates are open; Issue #7 remains open. |
| Rollback | `UNKNOWN` / blocked | No deployed population, known-good artifact set, compatibility matrix, or demonstrated fallback exists. |
| Existing devices | `INSTALLED_DEVICE_POPULATION = UNKNOWN` | No assumption of zero, one, or many devices is permitted. No deployment plan may proceed from repository text alone. |

## Platform and site boundaries

- `MANNHEIM = TEST_EVIDENCE_ONLY`. Mannheim evidence must be portable, redacted,
  and incapable of becoming a default, identity component, checkout dependency,
  or release selector.
- `SENSOR_STANDALONE = REQUIRED`. The sensor must perform its product function
  without any consumer repository being present.
- `SMARTHOME = OPTIONAL_CONSUMER`. nowaControl-SmartHome may consume only a
  documented, versioned interface.
- `MFH = OPTIONAL_CONSUMER`. nowaControl-MFH may consume only a documented,
  versioned interface.
- `NO_DIRECT_REPOSITORY_COUPLING = REQUIRED`. There may be no source import,
  checkout-relative path, submodule, generated include, or build dependency on
  either consumer.
- Communication is limited to documented Zigbee, entity, event, capability, or
  API contracts.
- Firmware, Home Assistant integration, and platform governance have separate
  release gates. Evidence from one does not approve another.
- `NO_LIVE_SYSTEM_SOURCE_OF_TRUTH = REQUIRED`. A live coordinator, Home
  Assistant instance, building, or checkout cannot be the only authoritative
  record of product behavior.

## Change and release rule

Any proposed resolution must first change the machine-readable provenance
record, define the intended invariant, add failing tests, and pass the separate
generator/build/HIL/RF/security/delivery gates. `PROPOSED` values remain inert
until explicitly approved. Unknown values may never be silently promoted to
`VERIFIED`.
