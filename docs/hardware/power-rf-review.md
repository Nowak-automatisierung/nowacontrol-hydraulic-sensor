# nowaControl Hydraulic Sensor — Power & RF Review

**Document status:** Draft — pre-DVT
**Date:** 2026-03-22
**Author:** power-rf-hardware agent
**Source baseline:** repo state at branch `ws/power-rf-hardware`

---

## 1. Assumptions

The following table separates facts derived from repository documents from engineering assumptions that
require measurement or explicit design confirmation before DVT exit.

### Facts confirmed from repository

| Item | Value | Source |
|---|---|---|
| MCU | Seeed XIAO MG24 (EFR32MG24) | `sensor-platform/README.md`, `.claude/agents/firmware-mg24.md` |
| V1 radio protocol | Zigbee (IEEE 802.15.4, 2.4 GHz) for Home Assistant | `sensor-platform/README.md`, `firmware-mg24.md` |
| Battery chemistry | 1S LiPo | `WORKSPACE-FOCUS.md`, `.claude/agents/power-rf-hardware.md` |
| Primary antenna path | Internal 2.4 GHz FPC antenna | `docs/hardware/antenna-baseline.md` |
| Optional antenna path | External 2.4 GHz U.FL omnidirectional, 6.4 dBi | `docs/hardware/antenna-baseline.md` |
| EIRP compliance requirement | CE/RED EIRP budget must be checked at 6.4 dBi before shipping | `docs/hardware/antenna-baseline.md` |
| OTA | OTA-capable firmware architecture intended for V1 | `sensor-platform/README.md` |

### Assumptions — not yet confirmed in repo

| Item | Assumed value | Risk if wrong |
|---|---|---|
| [ASSUMPTION] Battery capacity | 400–600 mAh (typical for compact IoT sensor) | Directly drives battery life estimate |
| [ASSUMPTION] Battery nominal voltage | 3.7 V nominal, 4.2 V full charge, 3.0 V cutoff | Incorrect cutoff → MCU brownout or cell damage |
| [ASSUMPTION] Charger IC | MCP73831 or equivalent linear charger | Wrong charge current → cell degradation or thermal risk |
| [ASSUMPTION] Charge current | 100–200 mA (0.25–0.5 C assumed) | Higher current → thermal stress without cutoff IC |
| [ASSUMPTION] 3.3 V rail supply | LDO (e.g., XC6220 or similar) on XIAO MG24 module | LDO dropout at end-of-battery → premature brownout |
| [ASSUMPTION] Sensor type | Active pressure bridge or I2C/SPI digital pressure sensor | Active bridge → significant sensor excitation current |
| [ASSUMPTION] Sensor supply switching | Sensor rail switched off during sleep | Unswitched sensor → sleep current dominated by sensor quiescent |
| [ASSUMPTION] Enclosure material | Metallic or metal-mounted (hydraulic pipe/manifold) | Metal proximity degrades FPC antenna performance significantly |
| [ASSUMPTION] FPC antenna placement | On XIAO MG24 module, clearance from metal assumed sufficient | Must be verified on final mechanical assembly |
| [ASSUMPTION] EFR32MG24 TX power setting | +10 dBm (default, GSDK configurable) | Higher setting → EIRP may approach or exceed CE/RED limit with 6.4 dBi antenna |
| [ASSUMPTION] Cable loss (U.FL path) | 0.5–1.0 dB (connector + short cable) | Lower actual loss → higher effective EIRP |
| [ASSUMPTION] Sleep wakeup interval | 30–300 s (typical Zigbee end device polling) | Shorter interval → proportional reduction in battery life |

---

## 2. LiPo 1S Power Path Review

### Voltage range

- [CONFIRMED] Battery: 1S LiPo.
- [ASSUMPTION] Nominal: 3.7 V. Full charge: 4.2 V. Cutoff: 3.0 V (protection IC threshold).
- EFR32MG24 VREGVDD minimum: 1.71 V (per EFR32MG24 datasheet). The 3.3 V regulated rail must
  not droop below the MCU's minimum VDD over the full LiPo discharge curve including TX bursts.

### Protection IC

- [ASSUMPTION] A discrete LiPo protection IC is present (e.g., DW01A or equivalent) providing:
  - Over-voltage protection (>4.25 V cutoff)
  - Under-voltage protection (<2.75–3.0 V cutoff)
  - Short-circuit / over-current protection
- **Risk:** If protection IC is absent or under-specified, cell damage or fire risk exists. This must be
  confirmed against the BOM and schematic before any charging is performed in the lab.

### Charging circuit

- [ASSUMPTION] Charger IC: MCP73831 or equivalent single-cell linear charger.
- [ASSUMPTION] Charge current: 100–200 mA (resistor-set). No thermal cutoff assumed on PCB; cell
  self-protection assumed.
- **Risk:** Without NTC-based thermal cutoff, charging in a confined metallic enclosure in warm
  environments (hydraulic machinery) can lead to elevated cell temperature. Verify charger IC thermal
  behavior at maximum ambient.
- [ASSUMPTION] Charging via USB-C or JST connector — charge path not yet defined in repo.

### 3.3 V regulation

- [ASSUMPTION] XIAO MG24 module provides onboard 3.3 V LDO regulation from battery input.
- LDO efficiency is low at light load (typical quiescent ~55 µA for XC6220-class LDO), which adds
  directly to sleep current budget.
- LDO dropout: typically 200–300 mV. At 3.0 V battery cutoff → regulated rail may drop to ~2.7–2.8 V,
  which remains above EFR32MG24 minimum, but margin is narrow.
- **Recommendation:** If battery capacity is small, consider a buck-boost or high-efficiency LDO to
  extend usable battery range.

### Decoupling and bulk capacitance

- [ASSUMPTION] XIAO MG24 module includes standard bulk decoupling on VDD per Seeed module design.
- Insufficient bulk capacitance on the 3.3 V rail during Zigbee TX burst (peak ~13–20 mA for
  ~1–2 ms) can cause rail droop exceeding LDO transient response capability.
- **Required measurement:** See Section 7, measurement M1.

---

## 3. Peak Current and Brownout Risks

### EFR32MG24 TX current

- EFR32MG24 at +10 dBm output power (2.4 GHz, Zigbee): approximately 13 mA TX peak current
  (per Silicon Labs EFR32MG24 datasheet, Section 4 electrical characteristics).
- At maximum PA setting (+20 dBm): approximately 35 mA. [ASSUMPTION] This setting is not intended
  for this product given EIRP constraints, but must be explicitly disabled in firmware configuration.
- Duration of TX burst: Zigbee MAC frame transmission, typically 1–5 ms per packet.

### Sensor excitation current

- [ASSUMPTION] Pressure sensor with I2C or SPI digital interface: quiescent ~0.5–2 mA during active
  measurement, ~1 µA during powerdown.
- [ASSUMPTION] If an analog pressure bridge is used: excitation current could be 1–5 mA additional.
  This has a direct impact on measurement duty-cycle design.

### Total peak current estimate

| Source | Estimate | Basis |
|---|---|---|
| EFR32MG24 TX burst | ~13 mA | Datasheet (0 dBm typical); [ASSUMPTION] +10 dBm setting |
| EFR32MG24 core (active) | ~3–5 mA | Datasheet, EM0 active mode |
| Sensor active | ~1–2 mA | [ASSUMPTION] digital pressure sensor |
| LDO quiescent | ~0.1 mA | [ASSUMPTION] XC6220-class |
| **Total peak** | **~17–20 mA** | Concurrent TX + sensor active |

LDO or regulator must be rated for sustained 20 mA with headroom. [ASSUMPTION] XIAO MG24 module
LDO is rated for at least 200 mA — verified against Seeed XIAO MG24 module schematic required.

### Brownout risk

- EFR32MG24 VREGVDD minimum: 1.71 V (absolute), 1.8 V for normal operation.
- Risk scenario: LiPo near cutoff (3.0–3.1 V) + LDO dropout (250 mV) + rail droop during TX
  burst (100 mV estimated) → regulated rail at ~2.65 V. Margin to brownout reset: ~850 mV.
  This appears safe, but depends on actual LDO dropout and bulk cap quality.
- **Risk:** If a buck regulator is used instead of LDO, startup inrush or short-circuit foldback
  during TX burst could cause a different class of transient. Confirm regulator topology before
  brownout analysis is complete.

---

## 4. Low-Power Implications

### EFR32MG24 sleep modes

Sleep current figures from Silicon Labs EFR32MG24 datasheet (reference values — must be confirmed on
actual hardware at final firmware configuration):

| Mode | Typical current | RAM retention | RTC active |
|---|---|---|---|
| EM0 (active) | ~3–5 mA | Yes | Yes |
| EM1 (sleep) | ~1.5 mA | Yes | Yes |
| EM2 (deep sleep) | ~2 µA | Yes | Yes |
| EM3 (stop) | ~1.5 µA | Yes | Yes |
| EM4 (shutoff) | ~0.3 µA | No | No |

Target sleep mode for this product: **EM2 or EM3** with RTC wakeup for Zigbee end-device polling.
[ASSUMPTION] EM4 is not viable for Zigbee end device operation as it requires full radio re-join on
wakeup (acceptable only for very long sleep intervals with network rejoin).

### Sensor and peripheral leakage during sleep

- [ASSUMPTION] Sensor power rail is not switched off during sleep in current baseline.
  If so, sensor quiescent current (~0.5–2 mA) fully dominates the sleep budget and eliminates any
  battery life advantage from MCU sleep modes.
- **Recommendation:** Implement GPIO-controlled sensor power switch before estimating realistic sleep
  current. Verify with µA bench (Section 7, measurement M2).

### Wakeup interval and duty cycle

- [ASSUMPTION] Zigbee end device poll interval: 30–300 s (coordinator-configurable).
- Battery life estimate (rough order-of-magnitude, [ASSUMPTION] all values):

  | Parameter | Value |
  |---|---|
  | Battery capacity | 500 mAh |
  | Sleep current (EM2 + sensor off) | 5 µA total |
  | Active cycle current | 18 mA average |
  | Active cycle duration | 50 ms per wakeup |
  | Wakeup interval | 60 s |
  | Average current | ~5 µA + (18 mA × 50 ms / 60 s) = ~5 µA + 15 µA = ~20 µA |
  | Estimated battery life | 500 mAh / 0.020 mA = ~25,000 h (~1,040 days) |

  This estimate is optimistic and depends on sensor power switching being implemented and
  Zigbee radio not being in RX polling mode frequently. A more conservative estimate with
  5-second polling intervals and sensor rail always on would reduce battery life to weeks.

- **Watchdog at low voltage:** Verify that the watchdog does not cause repeated resets when battery
  approaches cutoff. EFR32MG24 reset sources must be logged and reported via Zigbee diagnostic
  attribute for field reliability.

---

## 5. FPC vs. U.FL Antenna Baseline

Source: `docs/hardware/antenna-baseline.md` [CONFIRMED].

### FPC antenna (primary path)

- [CONFIRMED] Primary path: internal 2.4 GHz FPC antenna.
- Typical gain: 0 to +2 dBi in free space (unobstructed, antenna oriented optimally).
- [ASSUMPTION] FPC antenna is on the XIAO MG24 module per Seeed module design.
- Sensitivity to placement: FPC antenna gain is significantly affected by:
  - Ground plane proximity (recommended: no ground plane within 3–5 mm of antenna trace)
  - Metal surfaces nearby (enclosure walls, mounting hardware)
  - Antenna orientation relative to coordinator/gateway

### U.FL path (optional external antenna)

- [CONFIRMED] Optional path: U.FL connector, external omnidirectional antenna, 6.4 dBi gain.
- U.FL connector insertion loss: [ASSUMPTION] 0.3–0.5 dB.
- Cable loss (if pigtail used): [ASSUMPTION] 0.5–1.0 dB per 30 cm at 2.4 GHz.
- Net antenna gain at radiating element: [ASSUMPTION] 6.4 dBi − 0.5 dB (connector) − 0.5 dB (cable)
  = ~5.4 dBi effective.

### EIRP calculation (U.FL path)

- [ASSUMPTION] EFR32MG24 conducted TX power: +10 dBm (configurable in GSDK).
- EIRP = TX power (dBm) − cable/connector loss (dB) + antenna gain (dBi)
- EIRP = +10 dBm − 1.0 dB + 6.4 dBi = **+15.4 dBm** (27.5 mW)

Regulatory limits:
- EU (CE/RED, 802.15.4 at 2.4 GHz): EIRP limit **+20 dBm** (100 mW)
- US (FCC Part 15.247): EIRP limit **+30 dBm** with point-to-point justification;
  **+20 dBm** for point-to-multipoint / general operation

Margin at assumed +10 dBm TX: **+4.6 dB margin to EU limit**.

**Compliance risk:** This margin is adequate at +10 dBm but is not large. If:
- TX power is set above +10 dBm (e.g., during GSDK auto-power tuning or misconfiguration), or
- Cable loss is lower than assumed (shorter or higher-quality cable), or
- A higher-gain antenna variant is substituted in the field,

the EIRP limit can be exceeded. [CONFIRMED from `docs/hardware/antenna-baseline.md`]:
"the EIRP budget must be checked against CE/RED limits before using this antenna in any shipped
product configuration."

**Required action:** TX power must be firmware-capped at a value that guarantees the EIRP limit
is not exceeded for any antenna configuration in the approved hardware list. This is a
release-gating item.

### Antenna configuration lock

- Antenna type and gain must be fixed and documented in the CE/RED technical file before
  type approval testing.
- If the antenna is field-replaceable or user-selectable, all approved antenna configurations must be
  explicitly listed and their EIRP budgets verified.
- [ASSUMPTION] The product will ship with one fixed antenna configuration per SKU. If both FPC and
  U.FL variants exist as separate SKUs, each requires its own compliance documentation.

---

## 6. Enclosure and Placement Sensitivities

### Hydraulic mounting environment

- [ASSUMPTION] The sensor is mounted on or near metal hydraulic components (pipe, manifold,
  valve block). This is an inference from the product name "hydraulic sensor" — confirmed
  application environment not yet documented in repo.
- Metal proximity is the highest RF risk for FPC antenna performance. Effects include:
  - Antenna resonant frequency shift (detuning)
  - Gain reduction (absorption and reflection)
  - Pattern distortion (non-omnidirectional effective radiation)
  - Increased return loss (antenna mismatch)

### FPC antenna clearance requirements

- [ASSUMPTION] Minimum clearance from metal surfaces for FPC antenna: **>10 mm** on all sides.
  This is a commonly used rule of thumb; actual minimum depends on antenna design and must be
  validated by the antenna vendor or by OTA characterization.
- At 2.4 GHz, λ/4 ≈ 31 mm in free space. Metal objects within λ/4 of the antenna will have
  measurable impact on performance.
- Metallic enclosure walls or mounting plates within 5–10 mm of the FPC antenna are expected to
  cause 3–10 dB gain degradation. [ASSUMPTION — must be measured.]

### U.FL + external antenna in metallic environment

- External antenna on a cable can be routed to a non-metallic window or positioned away from the
  metal enclosure, which is a significant advantage over FPC in this application.
- Cable routing must not run along or parallel to metallic surfaces for extended lengths (>λ/4)
  without shielded coax.
- [ASSUMPTION] Antenna mounting point on enclosure (e.g., bulkhead SMA) not yet designed.

### Recommended placement validation

1. Measure RSSI in free air (FPC antenna, no enclosure) as baseline.
2. Measure RSSI with sensor installed in final mechanical assembly on representative mounting surface.
3. Compare results — target: less than 10 dB degradation (see measurement M6 in Section 7).
4. If degradation exceeds 10 dB with FPC antenna, evaluate external antenna option.
5. Document final mechanical assembly as the tested configuration in the compliance technical file.

---

## 7. Required Bench Measurements

The following measurements must be completed on final or near-final hardware before DVT exit.
Results must be recorded in the test evidence file associated with this review.

| ID | Measurement | Purpose | Method | Pass criteria |
|---|---|---|---|---|
| M1 | VDD rail droop during Zigbee TX burst | Brownout risk assessment | Oscilloscope on 3.3 V rail, trigger on RF TX enable GPIO or RAIL TX event; 10 µs/div | < 100 mV droop from nominal; no brownout reset observed |
| M2 | Sleep current (MCU in EM2/EM3, sensor off) | Battery life baseline | µA bench (e.g., PPK2 or Otii Arc) with no charger connected, sensor GPIO held low | < 5 µA total (MCU + LDO quiescent + any peripheral leakage) |
| M3 | Sleep current (MCU in EM2/EM3, sensor rail on) | Sensor leakage quantification | Same as M2 but sensor powered | Record actual value; compare to M2 |
| M4 | Charge current profile | LiPo charger safety verification | Current probe (milliamp range) during charge from empty to full | Charge current within ±10% of charger IC resistor-set value; taper to <10 mA at 4.2 V |
| M5 | Battery voltage at undervoltage cutoff | MCU behavior at end of battery | Discharge cell with controlled load to protection IC cutoff; observe MCU behavior | Clean Zigbee leave or reset; no infinite reset loop; no hang state |
| M6 | RSSI at 1 m, free air, FPC antenna | Antenna baseline performance | Zigbee coordinator or sniffer RSSI measurement, device at 1 m LOS | > −60 dBm (indicative; actual target depends on link margin spec) |
| M7 | RSSI in final mechanical assembly on metal mounting surface | Enclosure and mounting detuning | Same setup as M6, device installed as shipped | < 10 dB degradation vs. M6 (i.e., > −70 dBm) [ASSUMPTION — threshold requires product link budget] |
| M8 | Conducted TX power at U.FL port (if U.FL SKU) | EIRP calculation input | Spectrum analyzer or calibrated reference antenna; measure output at U.FL with matched load | Within ±2 dB of firmware PA setting; confirm matches EIRP budget assumption |
| M9 | LDO output voltage at battery cutoff | Regulator dropout margin | Measure 3.3 V rail simultaneously with battery voltage during M5 discharge test | 3.3 V rail > 2.0 V when battery protection trips; no premature MCU reset before protection trip |

---

## 8. RF and Compliance-Sensitive Risks

### Risk register

| Risk ID | Description | Severity | Likelihood | Required action |
|---|---|---|---|---|
| RF-01 | EIRP limit exceeded with 6.4 dBi external antenna if TX power not capped | Critical | Possible | Firmware cap on PA output; document in technical file; measure M8 |
| RF-02 | FPC antenna gain degradation in metallic mounting environment | High | Likely | Measure M7; evaluate external antenna option if degradation > 10 dB |
| RF-03 | Antenna type or gain changed in field (user substitution) | High | Possible | Declare antenna non-removable, or document all approved configurations |
| HW-01 | LiPo protection IC absent or under-specified | Critical | Unknown | Confirm BOM and schematic; lab charge test before any bench charging |
| HW-02 | Charger IC without thermal cutoff in warm industrial environment | High | Possible | Verify charger IC thermal spec vs. worst-case enclosure temperature |
| HW-03 | Sensor rail not switched off during sleep | High | Likely (not yet implemented) | Implement GPIO power switch; verify with M2/M3 |
| HW-04 | Brownout reset at low battery during TX burst | Medium | Possible | Measure M1 and M9; verify with M5 |
| HW-05 | Watchdog reset loop at end of battery | Medium | Possible | Define reset cause logging; test M5 to EOL voltage |

### Compliance framework

- **CE/RED (Radio Equipment Directive 2014/53/EU):** Applies for EU market. Covers radio, EMC,
  and electrical safety.
- **FCC Part 15.247:** Applies if product is sold in the US market. [ASSUMPTION — US market scope
  not confirmed in repo.]
- Both frameworks require a fixed, documented antenna configuration. Field-replaceable antennas
  require all approved configurations to be tested or bounded by conducted power limits.
- If XIAO MG24 module has existing FCC/CE module approval, verify that the host product integration
  (enclosure, antenna, power supply) does not void the modular approval. [ASSUMPTION — module
  certification status not confirmed in repo.]
- Conducted vs. radiated testing: confirm with test house which test method is applicable for
  this product category before scheduling type approval.

---

## 9. Release Impact

The following items are release-gating requirements. None may be marked done by inference — each
requires physical evidence or a documented engineering decision with named owner.

- [ ] **Antenna configuration locked:** Antenna type, gain, and placement must be fixed per SKU
      before compliance testing is scheduled. Document in `docs/hardware/antenna-baseline.md`
      and CE/RED technical file.
- [ ] **EIRP budget sheet created:** A signed-off EIRP calculation sheet per antenna configuration
      must exist in `docs/hardware/` or `docs/compliance/` before type approval submission.
- [ ] **PA output cap implemented in firmware:** Firmware must enforce a maximum TX power that
      keeps EIRP below applicable limits for all approved antenna configurations. This must be
      a release-gating firmware change.
- [ ] **Bench measurements M1–M9 completed and results filed:** All measurements in Section 7 must
      have recorded pass/fail results in the HIL test evidence file
      (`sensor-platform/tests/hil/`).
- [ ] **LiPo protection IC confirmed:** BOM and schematic reviewed; charger IC spec confirmed
      against cell datasheet; no bench charging before this is verified.
- [ ] **Sensor rail power switching implemented and verified:** Sleep current measured (M2/M3)
      with sensor rail switching in firmware; result meets < 5 µA target or target is revised
      with documented rationale.
- [ ] **Battery life estimate updated with measured values:** Replace all [ASSUMPTION] values in
      Section 4 with measured sleep current, measured active current, confirmed capacity, and
      confirmed wakeup interval before any public battery life claim is made.
- [ ] **Reset cause logging implemented:** Watchdog, brownout, and LiPo cutoff behavior
      documented and observable via Zigbee diagnostic attribute or debug interface.
- [ ] **Any TX power setting change treated as release-gating:** Changes to GSDK PA configuration,
      TX power level, or antenna matching network are compliance-sensitive and must re-trigger
      EIRP review.

---

## References

| Document | Location | Status |
|---|---|---|
| Antenna baseline | `docs/hardware/antenna-baseline.md` | Exists — referenced in this review |
| Repo map | `docs/architecture/repo-map.md` | Exists |
| Hardware electronics | `sensor-platform/hardware/electronics/` | Directory exists, no files yet |
| HIL test plan | `sensor-platform/tests/hil/` | Directory exists, no files yet |
| EFR32MG24 datasheet | Silicon Labs — not in repo | Required for final electrical verification |
| XIAO MG24 module schematic | Seeed Studio — not in repo | Required for LDO/charger IC confirmation |
| LiPo cell datasheet | Not in repo | Required before any charging |
| CE/RED technical file | Not started | Required before type approval |
