# V1 Validation Matrix - nowaControl Hydraulic Sensor

## 1. Overview

**Purpose**
This document is the authoritative validation matrix for the V1 release of the nowaControl hydraulic sensor. It defines every test area that must be evaluated before production units ship, establishes pass/fail criteria for each tier of validation (lab, HIL, field), and records the current evidence status for each item.

**V1 Scope Statement**
V1 is the first field-ready release. No prior production units are deployed - this is a greenfield rollout. The target integration path is: Seeed XIAO MG24 (EFR32MG24) running Zigbee firmware, joined to Home Assistant via ZHA, with OTA updates delivered through the Gecko Bootloader BGAPI OTA mechanism and managed by the device-cloud update-service.

**Document date**: 2026-03-24
**Release branch**: ws/qa-release
**Document owner**: QA/Release Gatekeeper

---

## 2. Test Areas

Evidence status key:
- `PASS` - evidence collected, criteria met
- `FAIL` - evidence collected, criteria not met
- `IN PROGRESS` - testing underway
- `[EVIDENCE MISSING]` - no test artifact exists yet

| Area | Test ID | Description | Pass Criteria | Evidence Status |
|---|---|---|---|---|
| Boot & init | BT-01 | Cold boot from full battery | Device boots within 5 s, Zigbee stack initialises, no hard fault | [EVIDENCE MISSING] |
| Boot & init | BT-02 | Boot after deep-sleep wake | Wake-up time <= 500 ms, sensor HAL re-initialises correctly | [EVIDENCE MISSING] |
| Boot & init | BT-03 | Boot with low battery (3.0 V LiPo cutoff) | Device either boots or powers off cleanly - no crash loop | [EVIDENCE MISSING] |
| Boot & init | BT-04 | Boot after interrupted OTA (incomplete image) | Gecko Bootloader falls back to primary slot; device boots previous image | [EVIDENCE MISSING] |
| Zigbee pairing (ZHA) | ZB-01 | First-time join to ZHA coordinator | Device pairs within 60 s, ZHA recognises device class and cluster set | [EVIDENCE MISSING] |
| Zigbee pairing (ZHA) | ZB-02 | Re-join after network reset | Device re-joins within 60 s without manual coordinator intervention | [EVIDENCE MISSING] |
| Zigbee pairing (ZHA) | ZB-03 | Pairing rejected device (wrong pan_id) | Device does not join foreign PAN; no crash | [EVIDENCE MISSING] |
| Zigbee pairing (ZHA) | ZB-04 | Coordinator firmware compatibility matrix | Tested against ZHA coordinator firmware versions: TBD | [EVIDENCE MISSING] |
| Zigbee reporting | ZR-01 | Periodic pressure report cadence | Reports arrive at ZHA at configured interval (+/- 10 %); no missed reports over 1 h | [EVIDENCE MISSING] |
| Zigbee reporting | ZR-02 | Change-of-value report trigger | Report fires within one reporting cycle of threshold crossing | [EVIDENCE MISSING] |
| Zigbee reporting | ZR-03 | Report survives brief coordinator outage (< 60 s) | Reports resume automatically after coordinator returns; no data loss beyond outage window | [EVIDENCE MISSING] |
| Zigbee reporting | ZR-04 | Cluster attribute correctness | Pressure, battery voltage, and link-quality attributes match bench reference values within spec tolerance | [EVIDENCE MISSING] |
| OTA update | OT-01 | Nominal OTA - V1 image applied to V1 device | Device downloads, verifies, and applies image; reboots into new firmware; version attribute updated | [EVIDENCE MISSING] |
| OTA update | OT-02 | OTA image signature verification | Corrupt or unsigned image rejected by bootloader; device stays on current version | [EVIDENCE MISSING] |
| OTA update | OT-03 | OTA interrupted mid-transfer (battery pull) | Device recovers to previous good image on next boot | [EVIDENCE MISSING] |
| OTA update | OT-04 | OTA over low-battery condition | Update refused or safely aborted when battery < defined threshold | [EVIDENCE MISSING] |
| OTA update | OT-05 | OTA cluster negotiation with ZHA | OTA cluster handshake completes; image block requests observed on coordinator side | [EVIDENCE MISSING] |
| Battery & power | BP-01 | Battery life estimate under nominal reporting cadence | Measured current profile matches power budget; projected runtime >= V1 target (TBD days) | [EVIDENCE MISSING] |
| Battery & power | BP-02 | Deep-sleep current draw | Sleep current <= design target (TBD uA) measured with PPK2 or equivalent | [EVIDENCE MISSING] |
| Battery & power | BP-03 | Tx burst peak current | Peak Tx current does not exceed LiPo sustained discharge rating | [EVIDENCE MISSING] |
| Battery & power | BP-04 | Low-battery attribute reporting | Device reports low-battery flag to ZHA before cutoff voltage | [EVIDENCE MISSING] |
| Sensor HAL | SH-01 | Pressure reading accuracy | Readings within +/- tolerance against calibrated reference across full operating range | [EVIDENCE MISSING] |
| Sensor HAL | SH-02 | Sensor init after wake | Sensor HAL ready within 50 ms of wake; no stale reads | [EVIDENCE MISSING] |
| Sensor HAL | SH-03 | Out-of-range input handling | Sensor reports error attribute; no crash or silent wrong value | [EVIDENCE MISSING] |
| Sensor HAL | SH-04 | Temperature compensation (if applicable) | Pressure accuracy maintained across operating temperature range | [EVIDENCE MISSING] |
| Rollback | RB-01 | Rollback image push via OTA | Previous signed image applied; device boots previous version; version attribute reflects rollback | [EVIDENCE MISSING] |
| RB-02 | RB-02 | Rollback from crash-looping device | Bootloader detects repeated boot failures and falls back automatically (if watchdog rollback supported) | [EVIDENCE MISSING] |
| RB-03 | RB-03 | Rollback image availability in update-service | Previous release image is staged and accessible in device-cloud update-service before any new image is pushed | [EVIDENCE MISSING] |
| RF / antenna | RF-01 | RSSI floor - internal FPC antenna | Link quality sufficient for operation at target installation distance from coordinator | [EVIDENCE MISSING] |
| RF-02 | RF-02 | RSSI floor - external U.FL 6.4 dBi antenna | Link quality improvement vs. internal antenna documented | [EVIDENCE MISSING] |
| RF-03 | RF-03 | CE/RED conducted emissions pre-scan | Pre-scan results available; no obvious out-of-band emission at 2.4 GHz | [EVIDENCE MISSING] |
| RF-04 | RF-04 | Coexistence - WiFi 2.4 GHz present | Pairing and reporting stable with 802.11n AP active on adjacent channel | [EVIDENCE MISSING] |
| HIL regression | HIL-01 | Full boot-to-report cycle on real MG24 hardware | End-to-end: boot, pair, report, OTA, rollback - all pass on physical device | [EVIDENCE MISSING] |
| HIL regression | HIL-02 | 24 h continuous operation soak | Zero crashes, zero missed reports beyond defined threshold, battery model consistent | [EVIDENCE MISSING] |
| HIL regression | HIL-03 | OTA on real hardware with real coordinator | OTA completes on physical device joined to physical ZHA coordinator | [EVIDENCE MISSING] |
| Field soak | FS-01 | 7-day pilot deployment (internal/lab environment) | Zero unrecoverable failures; operator can explain every anomaly | [EVIDENCE MISSING] |
| Field soak | FS-02 | Staged rollout gate 1 - 10 units | Fleet health dashboard shows >= 95 % devices reporting; zero crash-rate above threshold | [EVIDENCE MISSING] |
| Field soak | FS-03 | Staged rollout gate 2 - 100 units | Same thresholds as FS-02, sustained over 72 h | [EVIDENCE MISSING] |

---

## 3. Lab Validation Criteria

Lab validation covers automated tests executable on developer hardware or CI runners without a full Zigbee coordinator setup.

### 3.1 Automated unit tests

| Criterion | Threshold | Status |
|---|---|---|
| Sensor HAL unit tests pass | 100 % pass, 0 skip | [EVIDENCE MISSING] - `sensor-platform/tests/unit/` is empty |
| Power management unit tests pass | 100 % pass | [EVIDENCE MISSING] |
| OTA image verification logic tests | 100 % pass | [EVIDENCE MISSING] |
| Bootloader slot-selection logic tests | 100 % pass | [EVIDENCE MISSING] |

### 3.2 Integration tests

| Criterion | Threshold | Status |
|---|---|---|
| Sensor HAL + sleep/wake cycle integration | 100 % pass | [EVIDENCE MISSING] - `sensor-platform/tests/integration/` is empty |
| OTA download + verify integration (simulated coordinator) | 100 % pass | [EVIDENCE MISSING] |
| Update-service API contract tests | 100 % pass | [EVIDENCE MISSING] - `device-cloud/services/update-service/` is empty |

### 3.3 Static / build gates

| Criterion | Threshold | Status |
|---|---|---|
| Firmware builds cleanly with zero warnings at -Wall | 0 warnings | [EVIDENCE MISSING] |
| Firmware image size within flash budget | <= defined linker region | [EVIDENCE MISSING] |
| Signing key NOT present in repository | No private key in git history | [EVIDENCE MISSING] |
| OTA image signed with correct V1 signing key | Signature verifies against `firmware/signing-public/` material | [EVIDENCE MISSING] |

### 3.4 Lab pass/fail threshold

Lab validation is BLOCKED until all unit and integration test suites exist and pass. A missing test suite is treated as a failing test suite.

---

## 4. HIL Validation Criteria

Hardware-in-the-loop validation requires: one or more physical XIAO MG24 devices, a Zigbee coordinator running ZHA (e.g., Sonoff Zigbee 3.0 USB or equivalent), Home Assistant instance, and lab power supply or instrumented battery.

### 4.1 Required HIL scenarios

| Scenario | Duration | Pass Criteria |
|---|---|---|
| Cold boot to first Zigbee report | Single run | Boot <= 5 s; first report received by ZHA within 2 min |
| Re-pair after factory reset | 3 repetitions | 100 % success rate |
| Continuous reporting soak | 24 h minimum | Report loss rate <= 1 % of expected reports; zero crashes |
| Deep-sleep cycle verification | 1 h, measured | Sleep current within design target; wake-up report cadence maintained |
| OTA nominal flow | Single run | Full image applied and verified on device |
| OTA interrupted mid-transfer | Single run | Device recovers to previous image; no brick |
| OTA rollback push | Single run | Rollback image applied; previous version reported by device |
| Battery depletion end-to-end | Run to cutoff | Device shuts down cleanly; no flash corruption on reboot with fresh battery |

### 4.2 HIL pass threshold

All 8 scenarios must pass. Any scenario that cannot be executed due to missing infrastructure is a blocker. HIL must be completed on at least 3 individual physical units to rule out unit-specific defects.

### 4.3 Current HIL status

[EVIDENCE MISSING] - `sensor-platform/tests/hil/` is empty. No HIL test scripts, fixtures, or results exist.

---

## 5. Field Rollout Criteria

V1 is a greenfield rollout. Staged rollout gates must be passed sequentially.

### 5.1 Rollout stages

| Stage | Unit count | Gate duration | Health threshold | Blocker conditions |
|---|---|---|---|---|
| Internal lab pilot | 1-5 units | 7 days | 100 % reporting; 0 crashes | Any crash, any unrecoverable failure |
| Gate 1 - limited beta | 10 units | 72 h | >= 95 % devices reporting; crash rate < 0.1 % | Crash rate >= 0.1 %; pairing failure rate >= 5 % |
| Gate 2 - expanded beta | 100 units | 72 h | Same thresholds as Gate 1, sustained | Any metric below threshold for > 2 h |
| Gate 3 - general availability | Unlimited | Ongoing | Monitoring dashboards active; rollback image staged | Missing rollback image; monitoring not operational |

### 5.2 Rollout prerequisites

- Update-service is deployed and reachable from coordinator
- Fleet health dashboard is operational and alerting configured
- Rollback image for the previous stable version is staged in update-service
- On-call operator has read `docs/runbooks/ota-rollback.md`
- OTA go/no-go checklist (Section 6) is signed off

---

## 6. OTA Go/No-Go Criteria

Every OTA push - including rollback pushes - must satisfy all items in this checklist before triggering.

### 6.1 Image readiness

| Item | Required state | Verified |
|---|---|---|
| Target image is signed with the V1 production key | Yes | [ ] |
| Signature verified against `firmware/signing-public/` public material | Yes | [ ] |
| Image version number is greater than current fleet version (or is an explicit rollback) | Yes | [ ] |
| Image has passed all lab and HIL validation for its version | Yes | [ ] |
| Rollback image (previous known-good version) is staged in update-service | Yes | [ ] |
| Image binary matches the hash recorded in the release manifest | Yes | [ ] |

### 6.2 Fleet and device state

| Item | Required state | Verified |
|---|---|---|
| Target devices are reachable by coordinator (last-seen within 2x reporting interval) | Yes | [ ] |
| Device battery level reported >= minimum OTA threshold (TBD %, recommend >= 50 %) | Yes | [ ] |
| No active crash-loop event on target devices | Yes | [ ] |
| Coordinator firmware is compatible with OTA cluster used in target image | Yes | [ ] |

### 6.3 Infrastructure state

| Item | Required state | Verified |
|---|---|---|
| Update-service is running and reachable | Yes | [ ] |
| Fleet health dashboard is active and showing baseline | Yes | [ ] |
| Operator monitoring for the rollout window is confirmed | Yes | [ ] |
| Rollback runbook (`docs/runbooks/ota-rollback.md`) has been reviewed by the executing operator | Yes | [ ] |
| Maintenance window is defined and communicated (if applicable) | Yes | [ ] |

### 6.4 OTA go/no-go decision

If any item above is unchecked: **NO-GO**. Do not proceed.

If all items are checked: the release lead countersigns and the push may be triggered.

---

## 7. Missing Evidence

The following items have no test artifacts, no test results, and no implementation to validate against. Each is a blocker for its respective validation tier.

| # | Item | Tier blocked | Marker |
|---|---|---|---|
| 1 | `sensor-platform/tests/unit/` - no unit tests exist | Lab | [EVIDENCE MISSING] |
| 2 | `sensor-platform/tests/integration/` - no integration tests exist | Lab | [EVIDENCE MISSING] |
| 3 | `sensor-platform/tests/hil/` - no HIL test scripts, fixtures, or results | HIL | [EVIDENCE MISSING] |
| 4 | `sensor-platform/tests/e2e/` - no end-to-end tests exist | HIL/Field | [EVIDENCE MISSING] |
| 5 | `sensor-platform/firmware/devices/` - firmware source is absent; no build artifact to validate | All tiers | [EVIDENCE MISSING] |
| 6 | `sensor-platform/firmware/bootloader/` - bootloader configuration absent; slot-fallback behaviour unverifiable | All tiers | [EVIDENCE MISSING] |
| 7 | `device-cloud/services/update-service/` - update-service implementation absent; OTA delivery pipeline untestable | Lab / Field | [EVIDENCE MISSING] |
| 8 | No OTA image has been built or signed; signing key workflow unverified | OTA go/no-go | [EVIDENCE MISSING] |
| 9 | No power measurements (sleep current, Tx peak, runtime estimate) | Lab / HIL | [EVIDENCE MISSING] |
| 10 | No RF pre-scan or antenna characterisation data | Lab / HIL | [EVIDENCE MISSING] |
| 11 | No coordinator compatibility matrix defined or tested | HIL | [EVIDENCE MISSING] |
| 12 | Fleet health dashboard: not confirmed to exist or be operational | Field | [EVIDENCE MISSING] |
| 13 | Battery OTA threshold value not defined | OTA go/no-go | [EVIDENCE MISSING] |
| 14 | V1 battery runtime target not defined | Lab / HIL | [EVIDENCE MISSING] |
| 15 | CE/RED pre-compliance testing not initiated | Field (regulatory gate) | [EVIDENCE MISSING] |

---

## 8. Release Recommendation

**Recommendation: BLOCK**

**Reason**

V1 cannot be released in its current state. All validation tiers - lab, HIL, and field - are blocked by the same root cause: the firmware, test suites, and update-service are not yet implemented. There are no artifacts to validate.

Specifically:
- All 15 missing-evidence items in Section 7 are open.
- No unit, integration, HIL, or e2e tests exist in any form.
- No firmware build exists to sign, flash, or characterise.
- The update-service (the OTA delivery path) has no implementation.
- OTA go/no-go prerequisites in Section 6 cannot be verified.

**Path to STAGE (partial gate)**

The recommendation may be upgraded to STAGE when:
1. Firmware builds successfully and passes static gates (BT, SH, BP build-time checks).
2. Unit and integration test suites are populated and pass at 100 %.
3. At least one signed OTA image exists and the signing key workflow is verified.
4. The update-service has a deployable build.

**Path to APPROVE (full gate)**

The recommendation may be upgraded to APPROVE when:
1. All items in Sections 3, 4, and 5 pass.
2. All 15 missing-evidence items are resolved.
3. OTA go/no-go checklist in Section 6 is fully signed off.
4. CE/RED pre-compliance is cleared or a regulatory plan is accepted.
