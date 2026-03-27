# Compliance Impact Note

**Product:** nowacontrol-hydraulic-sensor
**Platform:** Seeed Studio XIAO MG24 (EFR32MG24 SoC)
**Date:** 2026-03-24
**Branch:** ws/regulatory
**Status:** Pre-certification - no lab submission has been made

---

## 1. Current Assumptions

The table below separates verified facts from engineering assumptions or stated intent.
This distinction is a prerequisite for any pre-lab documentation package.

| Parameter | State | Basis |
|---|---|---|
| SoC | EFR32MG24, Seeed XIAO MG24 module | Known fact |
| Primary protocol (V1) | Zigbee, Home Assistant ZHA | Design intent |
| Roadmap protocols | Matter + Thread, BLE | Design intent - not V1 scope |
| Internal antenna | 2.4 GHz FPC, gain unspecified | Design intent - gain NOT measured |
| External antenna | 2.4 GHz U.FL omnidirectional, 6.4 dBi | Datasheet claim - NOT measured on product |
| RF output power | Not documented | Not measured |
| EIRP budget | Not calculated | Not performed |
| Enclosure | Not defined | Not tested |
| Module-level approval transferability | Not confirmed | Not verified |
| CE / RED formal test plan | Does not exist | None |

**No parameter in the RF path has been independently verified by measurement.**
All figures in use are either datasheet values or design intent.

---

## 2. Compliance-Sensitive Assumptions and Decisions

### 2.1 External Antenna at 6.4 dBi - EIRP Ceiling Risk

**Severity: HIGH - potential hard regulatory stop**

Under the EU Radio Equipment Directive (RED, 2014/53/EU) and harmonised standard ETSI EN 300 328,
the maximum allowed EIRP for 2.4 GHz wideband transmitters (including Zigbee / IEEE 802.15.4) is **+20 dBm**.

The EFR32MG24 supports up to +20 dBm conducted output (datasheet maximum).
At 6.4 dBi antenna gain the system EIRP reaches approximately **+26.4 dBm** - 6 dB above the regulatory ceiling.

This configuration cannot be shipped CE-marked without mitigation. Labelling alone does not resolve it.
Two paths exist:

1. **Firmware power cap:** When the external antenna is fitted, conducted output must not exceed approximately **+13.6 dBm** to keep EIRP <= +20 dBm.
2. **Remove the external antenna option** from all CE-marked product configurations.

Additionally: the 6.4 dBi figure is a datasheet claim. It has not been measured in the actual product context.
Antenna gain varies with ground plane geometry, nearby conductors, and enclosure proximity.
The 6.4 dBi value must not be used as a safe design assumption until verified by measurement.

### 2.2 Internal FPC Antenna - Gain Unknown

The internal FPC antenna has no documented gain. Without a measured gain value:

- The EIRP budget for the internal-antenna configuration cannot be calculated.
- EN 300 328 test setup parameters (antenna substitution method, reference level) cannot be defined.
- Lab submission cannot proceed.

FPC antenna performance is strongly influenced by PCB ground plane size, component placement, and enclosure material.
None of these have been characterised.

### 2.3 RF Output Power Not Documented

The firmware Tx power setting has not been documented or fixed.
Without a locked, documented, and verified conducted output power:

- The EIRP budget cannot be closed.
- The test lab cannot configure a reference scenario.
- A Declaration of Conformity cannot be signed.

This is a prerequisite for every subsequent RF compliance step.

### 2.4 Module-Level Approval - Scope Not Transferable Without Review

The Seeed XIAO MG24 module may carry FCC/IC/CE marks at the module level.
Module-level approval covers the module in isolation on a reference PCB with a specific antenna configuration.

Module-level approval does **not** automatically transfer to this product in any of the following cases:

- The final product uses a different antenna than the one used during module certification.
- The U.FL external antenna connector is used, unless explicitly listed in the module approval.
- The final enclosure changes the RF environment relative to the reference test setup.
- Additional radio modes are enabled that were not active during the original module test (e.g., BLE or Thread on a Zigbee-only certified module).

Under RED there is no modular approval concept equivalent to FCC's modular grant.
RED requires the **final product** to be assessed as a complete system.
A separate technical file and Declaration of Conformity must be prepared for this product.

The current status "not confirmed as transferable" is the correct conservative position and must not be relaxed without explicit legal review of Seeed's approval documentation against this product's actual configuration.

### 2.5 Protocol Scope - Certification-Sensitive Decision

Each radio protocol has a distinct regulatory identity under RED:

| Protocol | Standard | Notes |
|---|---|---|
| Zigbee (IEEE 802.15.4) | ETSI EN 300 328 | V1 scope |
| BLE | ETSI EN 300 328 | Different duty cycle and modulation - separate test run required |
| Thread (IEEE 802.15.4) | ETSI EN 300 328 | Similar test family as Zigbee but RF config must match |
| Matter | Application layer over Thread | CSA certification is a separate, additional process |

**Critical decision not yet made:**
If V1 is certified for Zigbee only, and a subsequent OTA update activates BLE or Matter/Thread,
RED Article 10 re-assessment may be triggered. OTA-enabled protocol additions are a known re-assessment trigger.

Options:
1. Test all planned radio modes now (higher upfront cost, avoids mandatory re-test later).
2. Test Zigbee only and define a documented re-assessment trigger for future protocol activation.

This decision must be captured in an ADR before V1 is submitted for testing.

### 2.6 Enclosure - Undefined and Untested

The enclosure is not defined. Direct compliance consequences:

- Metallic or partially metallic enclosures detune FPC antennas and alter the radiation pattern.
- Enclosure sealing compounds (potting, silicone fills) used in hydraulic sensor applications change the dielectric environment around the antenna.
- The enclosure is part of the EUT (Equipment Under Test) as defined in EN 300 328 and EN 55032 test procedures.
  The lab cannot perform a final test without the production-representative enclosure.

Any enclosure decision made after RF testing begins must be treated as a change that may invalidate existing measurements.

### 2.7 Battery Voltage Variation - RF Impact

The 1S LiPo battery affects compliance testing in two ways:

1. **Conducted output power vs. battery state:** At end-of-life voltage the RF PA supply drops, reducing conducted output. EIRP must be confirmed across the full battery discharge curve to ensure it remains within spec at all battery states.
2. **Transport / UN 38.3:** If the product ships with the battery installed, UN 38.3 transport testing applies (not radio compliance, but a release gate).

---

## 3. Required Measurements and Lab Checks

Listed in dependency order.

### Step 1 - Lock firmware RF configuration (bench, no lab)

Document and version-control the Tx power setting for each radio mode.
Confirm against EFR32MG24 PA calibration tables.
**This single action unblocks all downstream RF compliance work.**

### Step 2 - Conducted output power measurement (bench: spectrum analyser / power meter)

Measure actual conducted output at the U.FL connector and PCB antenna feed for:
- Zigbee (channels 11-26; note channel 26 is restricted in some regions)
- BLE (if planned for any production firmware, even if not V1)
- Thread (if planned)

Measure at full, nominal, and minimum battery voltage.

### Step 3 - Internal FPC antenna gain measurement (anechoic chamber)

Measure total radiated power (TRP) and peak gain of the internal FPC antenna in the production-representative PCB configuration:
- Without enclosure first
- Then with each planned enclosure variant

FPC antenna performance cannot be approximated from datasheet values given its PCB-dependency.

### Step 4 - External U.FL antenna gain measurement (anechoic chamber)

Measure TRP and peak gain of the external omnidirectional antenna as connected to this product, including cable and connector losses.
The 6.4 dBi datasheet value is not acceptable as a design input until confirmed in context.

### Step 5 - EIRP budget calculation and verification

Calculate EIRP for each antenna path and each radio mode using measured conducted power and measured antenna gain.
Confirm all configurations are at or below +20 dBm (EN 300 328 limit for 2.4 GHz).
If any configuration exceeds the limit, implement firmware power capping and repeat measurement.

### Step 6 - Enclosure-integrated RF performance

Repeat TRP and EIRP measurements with the production-representative enclosure installed.
Enclosure-induced variation greater than ~1 dB requires EIRP budget recalculation.

### Step 7 - Radiated emissions pre-scan (before formal lab submission)

Perform a radiated emissions pre-scan (EN 55032 / CISPR 32) to identify unexpected harmonics or spurious emissions from the power supply, SoC, or sensor circuitry before committing to a formal test slot.

### Step 8 - Conducted and ESD immunity (installation environment dependent)

Depending on the intended installation environment (hydraulic control cabinet, industrial mounting),
the following may apply:
- IEC 61000-4-2 (ESD)
- IEC 61000-4-4 (EFT)

Determine applicable test levels based on sensor interface wiring length and type.

---

## 4. Documentation Gaps

The following items must exist before a technical file can be assembled for a RED Declaration of Conformity.

| Gap | Required Document |
|---|---|
| RF Tx power not specified | Firmware RF configuration document: protocol, channel, power level, PA setting (versioned) |
| EIRP budget not performed | EIRP budget calculation sheet - both antenna paths, all radio modes |
| FPC antenna gain unknown | Antenna characterisation test report - internal path, final PCB, with and without enclosure |
| External antenna gain unverified | Antenna characterisation test report - external path, 6.4 dBi claim verified or corrected |
| Enclosure not defined | Enclosure material spec and mechanical drawing referencing antenna keep-out zones |
| Module approval scope not assessed | Legal/technical review of Seeed XIAO MG24 RED declaration confirming what it covers for this product |
| No CE / RED test plan | Formal test plan referencing: EN 300 328, EN 55032, EN 62368-1, RED Article 3 |
| Protocol scope not locked | Product-level declaration of which radio modes are active in V1 and which are locked out |
| BLE / Matter / Thread re-assessment path undefined | ADR covering whether future protocol activation triggers RED re-assessment |
| No Declaration of Conformity template | DoC template with correct directive references and signatory |

---

## 5. Recommendation

The product is not currently in a state where a lab submission can be scheduled or a timeline estimated.

### Immediate - close before any lab time is booked

1. **Lock firmware Tx power configuration for Zigbee.** Store as a versioned parameter.
   This unblocks the EIRP budget calculation and all downstream decisions.

2. **Make an explicit product decision on the external antenna option.**
   The 6.4 dBi U.FL antenna, if sold or shipped as any configuration option,
   must appear in the RED technical file as a declared configuration.
   If the EIRP budget shows a violation, implement a firmware power ceiling or withdraw the option.

3. **Commission a legal review of the Seeed XIAO MG24 RED declaration.**
   Confirm whether module-level marks transfer to this product in its actual configuration.

4. **Open an ADR on protocol scope:**
   Zigbee-only V1 with a defined re-assessment trigger vs. multi-mode V1 tested across all active radio paths.
   This is an architectural decision with direct cost and schedule consequences for certification.

### Before enclosure is finalised

5. Complete conducted output power measurement (Step 2) to establish the baseline RF configuration.

6. Ensure the enclosure mechanical design includes a defined antenna keep-out zone for the internal FPC path.
   Changes to the keep-out zone after RF testing restart the antenna characterisation work.

### Before lab submission

7. Complete Steps 3-8 from the measurements section in order.

8. Assemble the technical file: RF configuration document, EIRP budget calculation, antenna test reports, enclosure drawing, applicable standards list, and DoC.

---

## Related paths

| Path | Purpose |
|---|---|
| `docs/hardware/antenna-baseline.md` | Source antenna assumptions (internal + external path) |
| `docs/adr/` | Protocol scope ADR and antenna option decision ADR (to be created) |
| `docs/architecture/` | RF path architecture description |
| `docs/release/` | Per-release certification scope tracking |
| `sensor-platform/hardware/` | Locked firmware RF configuration parameters |
| `sensor-platform/ota/` | OTA policy and RED re-assessment trigger documentation |
