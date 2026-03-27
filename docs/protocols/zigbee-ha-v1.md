# Zigbee + Home Assistant Integration - V1 Design Reference

**Product:** nowaControl hydraulic sensor
**Hardware platform:** XIAO MG24, internal 2.4 GHz FPC antenna (optional external U.FL, 6.4 dBi)
**Document status:** Draft - 2026-03-22
**Scope:** V1 ZHA integration. zigbee2mqtt is out of scope for V1 (see Section 9 for known risks).

---

## 1. Device Role (V1)

| Property | Value |
|---|---|
| Zigbee device type | End Device |
| ZHA profile ID | 0x0104 (Home Automation) |
| Logical device | Pressure sensor |
| Endpoint | 1 |
| Device ID | 0x0305 (Pressure Sensor) |
| Manufacturer name | `nowaControl` |
| Model identifier | `hydraulic-sensor-v1` |

**Device ID rationale:** Device ID 0x0305 (Pressure Sensor) is defined in the ZHA Device Specification and maps directly to the Pressure Measurement cluster (0x0403). ZHA and other ZCL-aware coordinators use the Device ID to drive automatic entity discovery. Using 0x0305 avoids the need for a custom ZHA quirk in V1 - the coordinator's cluster inspection path can resolve the pressure entity without manual cluster mapping. Device ID 0x0000 (Generic Sensor) would require coordinator-side custom handling and is explicitly rejected for V1.

The device operates as a sleeping end device only. It does not route traffic and must not be configured as a router.

---

## 2. Cluster and Attribute Behavior

### Server clusters on endpoint 1

| Cluster | Cluster ID | Required attributes |
|---|---|---|
| Basic | 0x0000 | ManufacturerName, ModelIdentifier, PowerSource |
| Identify | 0x0003 | IdentifyTime |
| Power Configuration | 0x0001 | BatteryVoltage, BatteryPercentageRemaining |
| Pressure Measurement | 0x0403 | MeasuredValue, MinMeasuredValue, MaxMeasuredValue |

**Client clusters on endpoint 1:** none in V1.

### Attribute encoding table

| Cluster | Attribute | Attr ID | ZCL type | Encoding / unit | Example |
|---|---|---|---|---|---|
| Basic | ManufacturerName | 0x0004 | CharString | UTF-8 string | `nowaControl` |
| Basic | ModelIdentifier | 0x0005 | CharString | UTF-8 string | `hydraulic-sensor-v1` |
| Basic | PowerSource | 0x0007 | uint8 | 0x03 = battery | `0x03` |
| Identify | IdentifyTime | 0x0000 | uint16 | Seconds, writable | `0x000A` = 10 s |
| Power Configuration | BatteryVoltage | 0x0020 | uint8 | 100 mV per unit | `37` = 3700 mV = 3.7 V |
| Power Configuration | BatteryPercentageRemaining | 0x0021 | uint8 | 0.5% per unit (ZCL spec) | `100` = 50% |
| Pressure Measurement | MeasuredValue | 0x0000 | int16 | 10 Pa per unit | `1000` = 10 000 Pa = 0.1 bar |
| Pressure Measurement | MinMeasuredValue | 0x0001 | int16 | 10 Pa per unit | `0` = 0 Pa |
| Pressure Measurement | MaxMeasuredValue | 0x0002 | int16 | 10 Pa per unit | `25000` = 250 000 Pa = 2.5 bar |
| Pressure Measurement | Tolerance | 0x0003 | uint16 | 10 Pa per unit, optional | omitted in V1 |

**Notes on encoding:**

- `BatteryPercentageRemaining` follows ZCL spec section 3.3.2.2.3: the attribute value equals `percentage * 2`. A fully charged battery (100%) is reported as `200`. A dead battery (0%) is reported as `0`. Home Assistant's ZHA integration handles this conversion automatically.
- `MeasuredValue` unit is defined by ZCL cluster 0x0403 as 10 Pa per unit (i.e., value = pressure_in_Pa / 10). Home Assistant performs the bar conversion at the entity level (see Section 7).
- `ManufacturerName` and `ModelIdentifier` strings are the canonical ZHA quirk matching keys and must not be changed between firmware versions without a migration plan.

---

## 3. Reporting Cadence

### Configured attribute reports (device-initiated)

| Attribute | Cluster | Min interval | Max interval | Reportable change |
|---|---|---|---|---|
| MeasuredValue (pressure) | 0x0403 | 30 s | 300 s | 10 (= 100 Pa) |
| BatteryPercentageRemaining | 0x0001 | 3600 s | 43200 s | 2 (= 1%) |

**Rules:**

- The device configures these reporting bindings on startup and after every rejoin before sending the first measurement.
- The coordinator must not rely on poll-based reads for normal pressure monitoring. Poll reads are an acceptable fallback only for battery state (see interoperability note below).
- If the coordinator does not acknowledge the reporting configuration, the device falls back to max-interval periodic pushes (300 s for pressure, 43200 s for battery).
- Reportable change for pressure (10 = 100 Pa) prevents flooding on stable systems. On a rapidly changing hydraulic circuit, reports may arrive as fast as the min interval (30 s).

> **Coordinator-side:** ZHA re-configures attribute reporting on every device rejoin as part of its normal lifecycle. The device must accept new reporting configuration write requests from the coordinator without requiring a factory reset. If ZHA issues a reporting configuration that differs from the device's startup defaults, the device applies the coordinator's configuration.

> **Coordinator-side:** ZHA polls `BatteryPercentageRemaining` (cluster 0x0001, attr 0x0021) every 45 minutes by default as a fallback when no reporting is configured or after coordinator restart. This polling fallback is acceptable for V1 battery state accuracy.

---

## 4. Battery Behavior

**Battery type:** LiPo single cell
**Nominal voltage:** 3.7 V
**Full charge:** 4.2 V
**Cutoff / empty:** 3.0 V

### Voltage encoding

`BatteryVoltage` (attr 0x0020) = floor(mV / 100)

| Real voltage | Attribute value |
|---|---|
| 4.20 V | 42 |
| 3.70 V | 37 |
| 3.30 V | 33 |
| 3.00 V | 30 |

### Percentage encoding

Linear mapping: 3.0 V = 0%, 4.2 V = 100%.

`BatteryPercentageRemaining` attribute value = floor((V - 3.0) / 1.2 * 100) * 2

| Real voltage | Percentage | Attribute value |
|---|---|---|
| 4.20 V | 100% | 200 |
| 3.70 V | 58% | 116 |
| 3.30 V | 25% | 50 |
| 3.00 V | 0% | 0 |

**Low battery threshold:** 15% real percentage (attribute value 30). When the computed percentage drops to or below 15%, the device should report immediately (outside the normal max-interval cadence) rather than waiting for the next scheduled report. Home Assistant will render the battery entity as "low" based on the numeric value; no separate alarm cluster is required in V1.

> **TODO:** Confirm whether ZHA automatically surfaces a "battery low" warning in the HA UI at a configurable threshold, or whether this requires a sensor template / automation in V1. Flag for validation test ZB-V1-10.

### Sleep / wake cycle

The device is a sleeping end device. It wakes on a configurable schedule (default: aligned to the 30 s minimum report interval) or on a pressure threshold event. Between wakes, the radio is off.

**End device poll interval:** 7.5 s (Zigbee specification default for sleeping end devices). The coordinator's MAC layer keepalive and queue behavior is governed by this value.

> **Coordinator-side:** The coordinator (ZHA + CC2652P) must buffer messages for the end device during sleep intervals. If the coordinator's indirect transmission queue is exhausted, messages are dropped. This is a standard Zigbee coordinator behavior and is not a device-side concern, but must be considered when sizing the coordinator's transmit queue for dense deployments.

---

## 5. Pairing Behavior

### Factory reset

- Hold the physical button for more than 5 seconds.
- Device sends a `Leave` request to the current coordinator (if joined), clears all network parameters from NVM, and reboots.
- After reboot, device enters join mode automatically.

### Join mode

- Join method for V1: standard open-network join (coordinator issues `Permit Join` open broadcast).
- The device scans all Zigbee channels and attempts association on the first channel with a joinable PAN.
- Join timeout: 3 minutes from boot. If no coordinator responds within 3 minutes, the device enters deep sleep and retries on next scheduled wake.

> **TODO:** Install code (ZB3 install code commissioning) is not implemented in V1. Mark as future enhancement. Touchlink commissioning is explicitly out of scope for V1 - complexity is not justified by the product use case.

### Post-join sequence

1. Device completes network join and receives network key.
2. Device sends `Device_annce` (ZDP).
3. Device configures attribute reporting (as defined in Section 3).
4. Device sends first pressure and battery measurement within 10 seconds of successful join.
5. Identify cluster is available immediately after join.

### Identify behavior

- On receipt of an `Identify` command with `IdentifyTime > 0`: blink the on-board LED at 1 Hz for `IdentifyTime` seconds.
- On receipt of `IdentifyTime = 0`: stop blinking immediately.
- `IdentifyTime` is writable by the coordinator; default value after join is 0 (not identifying).

---

## 6. Rejoin Behavior

### Rejoin trigger

- Parent link failure (no ACK after retries).
- Power cycle.
- NWK layer `leave` command received.

### Backoff schedule

Exponential backoff starting at 10 seconds, doubling each attempt, capped at 30 minutes.

| Attempt | Delay before attempt |
|---|---|
| 1 | 10 s |
| 2 | 20 s |
| 3 | 40 s |
| 4 | 80 s |
| 5 | 160 s |
| 6+ | 1800 s (30 min cap) |

The device does not implement complex parent selection logic in V1. It attempts to rejoin via the previous parent and falls back to a full rejoin scan if the previous parent is unavailable.

### Post-rejoin sequence

1. Device re-configures attribute reporting (identical to post-join sequence).
2. Device sends any pending measurements that were buffered during the outage (buffer size: TBD, minimum 1 measurement).
3. Normal reporting cadence resumes.

> **Coordinator-side:** ZHA may issue a `leave_and_rejoin` command (e.g., after coordinator restart or ZHA reconfiguration). The device must handle this command gracefully: execute the leave, then immediately re-enter join mode without requiring a manual factory reset.

> **Coordinator-side:** ZHA re-issues reporting configuration writes after device rejoin. The device must accept these without error even if the configuration matches the current state.

> **Coordinator-side:** Network key (NWK key) rotation is a Trust Center function managed by ZHA. The device must process TC key update frames and re-key without dropping off the network. This is standard Zigbee 3.0 behavior. No custom device-side implementation is required beyond using a compliant Zigbee stack (e.g., GSDK / EmberZNet on MG24).

---

## 7. Expected Home Assistant Entities

### Auto-generated entities (no quirk required)

| Entity | Domain | Attribute source | Cluster | Unit | HA conversion | Auto or quirk |
|---|---|---|---|---|---|---|
| Hydraulic Pressure | `sensor` | MeasuredValue (0x0000) | 0x0403 | bar | value / 1000 (10 Pa units -> bar) | Auto (Device ID 0x0305) |
| Battery | `sensor` | BatteryPercentageRemaining (0x0021) | 0x0001 | % | value / 2 | Auto (ZHA battery template) |
| Battery Voltage | `sensor` | BatteryVoltage (0x0020) | 0x0001 | V | value / 10 | Auto (ZHA, may not render by default) |
| Identify | `button` | Identify cluster (0x0003) | 0x0003 | - | sends IdentifyTime=10 | Auto (ZHA generates for all Identify servers) |

**Design goal: no ZHA quirk required for V1.**

### Conditions that would force a quirk

The following conditions would require a custom `zhaquirks` entry. They are design anti-patterns for V1 and must be avoided:

- Using Device ID 0x0000 (Generic) instead of 0x0305 - ZHA cannot auto-map the pressure cluster without a quirk.
- Reporting pressure on a non-standard cluster or attribute ID.
- Using a non-standard unit encoding that ZHA does not recognize.
- Manufacturer/model strings that differ from `nowaControl` / `hydraulic-sensor-v1` - ZHA quirk matching is exact-string on these two fields.
- Any attribute that requires endpoint remapping or cluster override.

> **TODO:** Validate ZHA's automatic unit conversion for cluster 0x0403. ZHA translates the ZCL-spec unit (10 Pa) to bar in the entity. This translation is present in HA 2023.x but the exact release must be confirmed (see Section 8).

---

## 8. Interoperability Notes for ZHA

### ZHA quirk matching

ZHA matches device quirks by the tuple `(ManufacturerName, ModelIdentifier)`. The canonical values for this device are:

- `ManufacturerName`: `nowaControl`
- `ModelIdentifier`: `hydraulic-sensor-v1`

These strings must be treated as a stable interface. A firmware update that changes either string will break any deployed quirk or any user automation that references the device by model.

### ZHA version / Home Assistant release dependency

- Pressure Measurement cluster (0x0403) is natively supported in ZHA as of Home Assistant 2023.2. HA versions below 2023.2 may not render the pressure entity automatically even with Device ID 0x0305.

> **TODO:** Verify the exact HA release where ZHA began auto-mapping cluster 0x0403 to a `sensor` entity with bar units. The 2023.2 reference is based on ZHA changelog review but is not lab-validated. Flag as open until confirmed with a real coordinator.

### Reference coordinator hardware (V1)

**Sonoff Zigbee 3.0 USB Dongle Plus (CC2652P)** with Z-Stack coordinator firmware.

All pairing and reporting validation tests in Section 10 are to be executed on this hardware. Behavior on other coordinator hardware (ConBee II, SkyConnect, etc.) is unvalidated for V1.

> **Risk:** The CC2652P coordinator has a known indirect transmission queue limit. In deployments with many sleeping end devices, buffer overflow may cause missed reports. This is not a V1 concern (single-device validation), but must be documented before any multi-node rollout.

### Sleeping end device behavior in ZHA

- ZHA handles sleeping end devices via the coordinator's MAC indirect queue.
- If the device misses a poll cycle, ZHA may mark the device as unavailable after a configurable timeout (default: 2 hours in ZHA for battery-powered devices).
- The 7.5 s poll interval (see Section 4) governs how frequently the device checks for queued commands from the coordinator.

### Polling fallback

- ZHA polls `BatteryPercentageRemaining` every 45 minutes as a fallback even when reporting is configured. This is acceptable for V1.
- ZHA does not poll `MeasuredValue` by default for cluster 0x0403 when reporting is configured. If reporting fails silently, the pressure entity will become stale. The max-interval fallback (300 s) on the device side mitigates this.

---

## 9. Risks for zigbee2mqtt Compatibility

zigbee2mqtt is not in scope for V1. The following risks are documented for future reference only.

> **Risk:** z2m uses an `exposes` / converter model rather than ZHA's cluster-inspection model. The Pressure Measurement cluster (0x0403) may not have a built-in converter in z2m for Device ID 0x0305. A custom `fromZigbee` converter would be required.

> **Risk:** z2m device registry matching is by `(manufacturer, model)` tuple. If no matching entry exists in the z2m device database, the device will appear as unsupported. A custom device definition file must be provided separately.

> **Risk:** `BatteryPercentageRemaining` ZCL encoding (value = percentage * 2) is handled automatically in ZHA but requires explicit handling in a z2m converter. An incorrect converter would report double the actual percentage.

> **Risk:** z2m does not use ZHA quirks. Any z2m support requires a separate, independent converter implementation. The ZHA-first design does not provide any reusable component for z2m.

**Overall z2m risk level: medium.** z2m users cannot use this device out-of-the-box in V1. This is a known and accepted limitation. A z2m converter is a post-V1 deliverable.

---

## 10. Required Validation Tests

All tests listed below must be executed on the V1 reference coordinator (Sonoff Zigbee 3.0 USB Dongle Plus, CC2652P) with Home Assistant running ZHA.

| Test ID | Test name | Method | Pass criteria |
|---|---|---|---|
| ZB-V1-01 | Pairing with ZHA | Manual, USB dongle, HA UI | Device appears in ZHA device list; all 4 server clusters (0x0000, 0x0001, 0x0003, 0x0403) visible in cluster inspection |
| ZB-V1-02 | Pressure entity created | Manual, HA entity registry | `sensor.hydraulic_pressure` (or equivalent) appears in HA with unit `bar` and non-null state within 10 s of pairing |
| ZB-V1-03 | Pressure value accuracy | Manual + calibrated reference pressure source | Reported value is within +/-0.5% of full scale compared to reference; value matches expected ZCL encoding (Pa/10 -> bar) |
| ZB-V1-04 | Reporting cadence | Automated capture via Wireshark/PCAP on CC2652P sniffer port | Pressure reports arrive at min 30 s to max 300 s intervals; no report missed for > 330 s under stable conditions |
| ZB-V1-05 | Battery reporting | Manual + controlled LiPo discharge | `BatteryPercentageRemaining` decrements in expected steps; HA battery entity shows correct percentage (attribute value / 2) |
| ZB-V1-06 | Rejoin after power loss | Manual - cut device power, restore | Device rejoins network within 2 minutes; `sensor.hydraulic_pressure` and battery entities recover to `available` state |
| ZB-V1-07 | Reporting re-configured after rejoin | Automated - monitor ZCL traffic post-rejoin | Attribute reporting configuration is re-established and first pressure report arrives within 30 s of rejoin completion |
| ZB-V1-08 | Factory reset | Manual - hold button > 5 s | Device sends ZDP Leave, disappears from ZHA; re-pairs cleanly as a new device on next join attempt |
| ZB-V1-09 | Network key rotation | ZHA coordinator action (TC key update via HA UI or ZHA service call) | Device receives new NWK key and remains reachable; pressure reports continue uninterrupted after key update |
| ZB-V1-10 | Low battery alert | Manual + controlled LiPo discharge to <=15% | HA battery entity shows value <= 15%; HA UI indicates low battery state; immediate report triggered below threshold |

> **TODO:** Tests ZB-V1-04 and ZB-V1-07 require a Zigbee packet capture setup (second CC2652P in sniffer mode or equivalent). Confirm lab availability before scheduling integration validation.

> **TODO:** Test ZB-V1-09 requires identifying the correct ZHA service call or coordinator firmware action to trigger a TC key update. Document the exact procedure in the test runbook before execution.

---

## Appendix: Cluster and Endpoint Summary

```
Endpoint 1
  Profile:       0x0104 (Home Automation)
  Device ID:     0x0305 (Pressure Sensor)
  Device version: 0x01

  Server clusters (device implements):
    0x0000  Basic
    0x0001  Power Configuration
    0x0003  Identify
    0x0403  Pressure Measurement

  Client clusters (device uses):
    (none)
```

---

*This document is a living design reference. Open items marked `TODO` must be resolved before V1 production release.*
