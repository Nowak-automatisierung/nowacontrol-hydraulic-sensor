# OTA Rollback Runbook — nowaControl Hydraulic Sensor

**Version**: V1
**Last updated**: 2026-03-24
**Owner**: Release / On-call Operator
**Related doc**: `docs/release/v1-validation-matrix.md`

---

## 1. Purpose and Scope

This runbook describes how to execute an OTA rollback for the nowaControl hydraulic sensor (Seeed XIAO MG24, EFR32MG24) in a production or field environment.

**Use this runbook when**:
- A newly deployed firmware version is causing device instability, crash loops, sensor misreads, or pairing failures and the decision to roll back has been taken.
- An operator or automated alert triggers the rollback criteria defined in Section 3.
- A staged rollout must be halted and reverted.

**V1 context**:
V1 is the first production release — no prior field versions exist at initial deployment. For V1, "rollback" means pushing the last known-good image that was validated in HIL before a new image was pushed. Once V2 and later firmware versions exist, this runbook applies to any regression of the fleet to a prior verified image.

**This runbook does not cover**:
- Factory re-flashing via JTAG/SWD (hardware recovery — see separate hardware recovery procedure).
- Coordinator firmware rollback.
- Home Assistant ZHA binding reset (unless explicitly noted as a side-effect step).

---

## 2. Rollback Prerequisites

Before initiating rollback, confirm every item below. If any item is not met, rollback via OTA is not possible — escalate to hardware recovery.

| # | Prerequisite | How to verify |
|---|---|---|
| P1 | Rollback image (previous known-good version) is staged in the update-service | Check update-service image registry; confirm version N-1 is present and its hash matches the release manifest |
| P2 | Rollback image is signed with the production signing key | Re-verify signature against `sensor-platform/firmware/signing-public/` public certificate material |
| P3 | Target devices are reachable by the Zigbee coordinator | Check ZHA device list; last-seen timestamp within 2x the configured reporting interval |
| P4 | Device battery level is at or above the minimum OTA threshold | Read battery attribute from ZHA; threshold is defined in `device-cloud/services/update-service/` config — do not push OTA to devices below this level |
| P5 | Coordinator is running and reachable from update-service | Confirm coordinator health in Home Assistant; confirm update-service can route OTA block requests |
| P6 | You have identified the exact set of affected devices | Device IDs / IEEE addresses of devices to roll back are listed before starting |
| P7 | You have read this runbook in full before beginning | Self-check |

---

## 3. Rollback Triggers

The following conditions mandate an immediate rollback decision. The on-call operator makes the final call, but must document the reason.

| Trigger | Threshold | Source |
|---|---|---|
| Device crash rate | >= 0.1 % of fleet per hour, sustained over 15 min | Fleet health dashboard |
| Pairing failure rate | >= 5 % of join attempts fail after new firmware deployed | ZHA event log / dashboard |
| Telemetry loss | >= 5 % of expected reports missing over a 30-min window | Fleet health dashboard |
| Silent wrong sensor value | Any confirmed instance of a sensor reporting a value more than 2x outside calibrated range with no hardware fault | Manual or automated check |
| Operator escalation | Any operator or customer escalation that cannot be resolved within 30 min by configuration change | Escalation channel |
| Staged rollout gate breach | Any health threshold in the validation matrix `docs/release/v1-validation-matrix.md` Section 5 is breached | Deployment monitoring |

If a trigger is met, stop further OTA rollout immediately before executing rollback.

---

## 4. Rollback Procedure

Work through every step in order. Do not skip steps. Record outcomes at each step.

### Step 1 — Declare rollback intent

1. Note the current time (UTC) and the firmware version being rolled back FROM.
2. Note the rollback target version (the version being rolled back TO).
3. Post a rollback-in-progress notice to the team channel / incident tracker.
4. Confirm prerequisite P6: produce the list of affected device IEEE addresses.

### Step 2 — Halt any ongoing OTA rollout

1. In the update-service, suspend or cancel any active OTA campaigns targeting the affected devices.
2. Confirm no new OTA block requests are being served to the affected fleet segment.
3. Wait 60 s and verify in ZHA logs that OTA block traffic has stopped.

### Step 3 — Stage the rollback image

1. Confirm the rollback image version and hash in the update-service image registry (prerequisite P1 and P2 must already be verified).
2. Create a rollback OTA campaign in the update-service targeting only the devices identified in Step 1.
3. Set campaign type to "rollback" (lower version number than current) — confirm the update-service is configured to permit downgrade pushes.

**Important**: Zigbee OTA cluster implementations on some coordinators reject lower version numbers by default. Verify the ZHA OTA provider configuration permits downgrade before proceeding.

### Step 4 — Push the rollback image

1. Trigger the rollback campaign from the update-service.
2. Monitor ZHA OTA cluster traffic: you should see `Image Block Request` frames from target devices within 2x the reporting interval (battery devices wake periodically — they do not poll continuously).
3. Do not expect immediate response from deep-sleeping devices. Allow up to 2x the configured wake/report interval for the device to wake and begin the OTA download.

**Expected timeline**: For a battery device on a deep-sleep cycle, allow at minimum 2 full wake cycles before concluding a device has not responded.

### Step 5 — Monitor download and apply

1. Track OTA progress per device in the update-service dashboard or ZHA log.
2. Confirm `Upgrade End Response` is received for each device.
3. After apply, the device will reboot. Expect a brief offline period (< 60 s under normal conditions).
4. Confirm the device re-appears in ZHA with the rollback firmware version in the `sw_build_id` or equivalent version attribute.

### Step 6 — Verify rollback (see Section 5)

Complete all verification criteria before declaring the rollback complete.

### Step 7 — Close the incident

1. Record the following in the incident log:
   - Rollback trigger (which criterion from Section 3 was met)
   - Devices rolled back (count and IEEE address list)
   - Start time and completion time
   - Verification outcome (Section 5)
   - Any devices that could not be rolled back (Section 6)
2. Post rollback-complete notice to team channel.
3. Do not resume forward OTA rollout until the root cause of the original failure is identified and a fix is validated.

---

## 5. Verification Criteria

After rollback, confirm all of the following before closing the incident.

| # | Criterion | How to check |
|---|---|---|
| V1 | Firmware version attribute on device matches rollback target version | Read `sw_build_id` attribute from ZHA device detail |
| V2 | Device is paired and reachable in ZHA | Device shows as online in ZHA device list; last-seen is current |
| V3 | Sensor reporting has resumed | Pressure attribute updates are arriving at the expected cadence in ZHA |
| V4 | No crash loop | Device has not rebooted more than once since rollback; uptime counter is increasing |
| V5 | Battery attribute reporting | Battery level attribute is present and plausible (no sudden drop to 0 %) |
| V6 | Fleet health metrics have returned to baseline | Dashboard crash rate, pairing failure rate, and report loss rate are all below trigger thresholds for at least 15 min |

All 6 criteria must be met. If any criterion fails, proceed to Section 6.

---

## 6. Rollback Failure Handling

### 6.1 Device does not respond to rollback OTA push

**Possible causes**: device is in deep sleep and has not woken; battery is critically low; device has crashed and is not processing ZDO/OTA messages.

**Actions**:
1. Wait for a full 2x wake cycle beyond the configured reporting interval before concluding non-response.
2. Check the battery attribute last reported before the failure. If battery was near or below the OTA threshold at the time of the original update, assume the device may have lost power mid-OTA.
3. If the device is genuinely unreachable after 3 full wake cycles, it is effectively bricked over-the-air. Mark the device as requiring hardware recovery.
4. Document the device IEEE address and failure mode in the incident log.

### 6.2 Device accepts rollback image but remains in crash loop

**Possible causes**: the rollback image itself has a defect; persistent flash state or NVM data is incompatible with the rollback version.

**Actions**:
1. Check whether the crash loop began immediately after rollback or after the first sensor read / ZHA join attempt.
2. If the rollback image is also crashing, do not push additional OTA — escalate to hardware recovery.
3. Do not attempt a forward re-push of the broken new image as a "fix" without explicit engineering sign-off.

### 6.3 Battery died mid-rollback OTA

**Symptoms**: device was downloading the rollback image, battery depleted, device went offline mid-transfer.

**Expected behaviour**: The Gecko Bootloader should not apply a partial image. On next boot (after recharging or battery replacement), the device should boot the last complete and valid image in the primary slot.

**Actions**:
1. Wait for the device to be recharged / battery replaced.
2. After reboot, check the firmware version attribute. If it matches the rollback target: proceed with verification (Section 5). If it matches the broken new version: re-trigger the rollback campaign for this device.
3. If the device does not boot after recharge: escalate to hardware recovery.

### 6.4 Coordinator becomes unreachable during rollback

**Actions**:
1. Do not panic — devices in deep sleep are not mid-transfer and will not brick from coordinator loss.
2. Restore coordinator connectivity first.
3. After coordinator is restored, audit which devices completed rollback (check version attribute) and which did not, then re-trigger the campaign for incomplete devices.

### 6.5 Update-service is unreachable

**Actions**:
1. Do not attempt manual OTA via ZHA without the rollback image hash being independently verified.
2. Restore the update-service; then resume from Step 3.
3. Any OTA campaign that was partially triggered when the service went down must be audited for state consistency before resuming.

---

## 7. Operator Notes

### 7.1 Battery devices do not poll OTA continuously

The XIAO MG24 spends most of its time in deep sleep. The ZHA OTA provider serves images in response to `Image Notify` or `Query Next Image Request` frames, which only occur when the device is awake. Do not expect OTA progress in real time. Use the configured reporting interval as the minimum cadence for progress checks. Typical OTA for a battery sensor may take several hours depending on image size and reporting interval.

### 7.2 ZHA OTA downgrade permissions

ZHA's OTA provider may refuse to serve an image with a lower version number than the device's current version. Before the rollback campaign is created, confirm ZHA OTA provider settings allow downgrade. If downgrade is not permitted in the default configuration, it must be explicitly enabled. Document which ZHA/coordinator version was used and what configuration change was made.

### 7.3 Zigbee binding state after rollback

Rolling back firmware does not reset the Zigbee binding table or NVM network credentials on the device. The device should re-join its existing PAN without re-pairing. If the new (broken) firmware corrupted the NVM network state before rollback, the device may need a manual factory reset and re-pair after rollback. Check ZHA for unexpected "device not found" or "failed to bind" errors.

### 7.4 Multiple devices in the same rollback campaign

Do not roll back the entire fleet simultaneously. Stage the rollback: roll back a subset, verify, then expand. This limits the blast radius if the rollback image itself has an unexpected interaction with field conditions.

### 7.5 Do not mix rollback and forward OTA campaigns simultaneously

Running a rollback campaign and a forward OTA campaign at the same time against overlapping device sets will create version confusion. Ensure all active campaigns are audited and non-overlapping before starting rollback.

### 7.6 Signing key for rollback image

The rollback image must be signed with the same production signing key as the forward image. A rollback image signed with a development or test key will be rejected by the Gecko Bootloader in production. Verify the signature chain before staging.

### 7.7 ZHA coordinator reachability is a hard dependency

OTA delivery is entirely routed through the Zigbee coordinator. If the coordinator (e.g., Sonoff Zigbee 3.0 USB or equivalent) is unavailable, unplugged, or its host (Home Assistant) is down, no OTA frame can be delivered to the device. Confirm coordinator health before and during rollback.

---

## 8. Missing Readiness Items

The following gaps in rollback infrastructure exist as of 2026-03-24. Each is a blocker or risk for executing this runbook in a real incident.

| # | Item | Impact | Marker |
|---|---|---|---|
| 1 | `device-cloud/services/update-service/` has no implementation | Rollback campaign cannot be created or triggered; entire OTA delivery path is absent | [NOT READY] |
| 2 | No rollback image exists — no V1 firmware has been built or signed | Step 2/3 of the procedure cannot be executed | [NOT READY] |
| 3 | OTA battery threshold value is not defined | P4 prerequisite cannot be evaluated; risk of pushing OTA to critically low-battery devices | [NOT READY] |
| 4 | Fleet health dashboard is not confirmed to exist or be operational | Trigger thresholds in Section 3 cannot be monitored; Section 5 verification criteria V6 cannot be checked | [NOT READY] |
| 5 | ZHA OTA downgrade permission configuration not documented | Section 7.2 risk is unmitigated; downgrade may silently fail at coordinator layer | [NOT READY] |
| 6 | Hardware recovery procedure (JTAG/SWD re-flash) is not written | Fallback for Section 6.1 / 6.2 escalation path does not exist | [NOT READY] |
| 7 | `sensor-platform/tests/hil/` is empty — rollback flow has never been exercised on real hardware | Rollback OTA behaviour on physical MG24 is untested; Gecko Bootloader slot-fallback not verified | [NOT READY] |
| 8 | Incident log / tracking channel is not defined | Step 1 and Step 7 of the procedure cannot be completed operationally | [NOT READY] |

This runbook is NOT operationally ready until items 1, 2, 3, and 4 are resolved at minimum. Items 5–8 must be resolved before GA rollout.
