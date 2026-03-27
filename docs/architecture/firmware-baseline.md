# Firmware Baseline - nowaControl Hydraulic Sensor

**Platform:** XIAO MG24 (EFR32MG24)
**Status:** Draft - pre-bringup
**Date:** 2026-03-22

---

## 1. Platform Assumptions

| Item | Assumption | Must verify |
|------|-----------|-------------|
| MCU | Silicon Labs EFR32MG24 (XIAO MG24, Seeed Studio) | Confirm exact part (B210F1536IM48 or variant) |
| Flash | 1536 kB | Confirm against actual BOM |
| RAM | 256 kB | - |
| SDK | Silicon Labs GSDK (Gecko SDK), EmberZNet for Zigbee | GSDK version pinned in project |
| Radio | 2.4 GHz IEEE 802.15.4 - Zigbee V1 path | - |
| Antenna | Internal 2.4 GHz FPC (primary); optional U.FL external | See `docs/hardware/antenna-baseline.md` |
| Power | 1S LiPo, no USB power assumed in field | Energy budget to be bench-validated |
| Active clock | HFXO 38.4 MHz | - |
| Sleep clock | LFXO or LFRCO 32.768 kHz | LFXO preferred for accuracy |
| Wi-Fi | **Not present in device firmware** | - |
| Debugger | J-Link via SWD (XIAO debug pads) | - |

---

## 2. Firmware Folder Boundaries

```
sensor-platform/firmware/
├── bootloader/
│   └── mg24-bootloader/        # Gecko Bootloader project (.slcp or Simplicity Studio)
├── devices/
│   └── hydraulic-sensor/
│       ├── src/                # App main, event loop, ZCL cluster handlers
│       ├── config/             # ZCL config, board config, GSDK component selection
│       └── CMakeLists.txt      # or .slcp (Silicon Labs project file)
├── shared/
│   ├── hal/                    # HAL interface headers (sensor.h, adc.h, power.h, bus.h)
│   └── drivers/                # Peripheral drivers implementing the HAL interfaces
└── signing-public/
    └── app-signing.pem         # Public key only - no private keys in repo
```

**Rules:**
- Application code under `devices/` MUST NOT access peripheral registers directly.
- All sensor and bus access goes through `shared/hal/` interface headers.
- Private signing keys are never stored in this repository.

---

## 3. HAL Boundaries for Sensor Access

The HAL layer decouples application and Zigbee logic from hardware peripherals.

```
shared/hal/
├── sensor.h     # sensor_init(), sensor_read() -> typed result struct
├── adc.h        # adc_init(), adc_sample_mv()
├── bus.h        # i2c_init/write/read or spi_init/transfer (depending on sensor BOM)
└── power.h      # power_sleep_em2(), power_sleep_em3(), power_set_wake_source()
```

**Constraints:**
- `sensor_read()` returns a typed struct (pressure_pa, temp_degc, etc.); callers do not interpret raw ADC counts.
- Bus type (I2C, SPI, analog) is encapsulated in `drivers/`; changing the sensor does not change application code.
- Host-side unit tests use mock implementations of `shared/hal/` (no EFR32 silicon required).
- Sensor interface type (I2C, SPI, analog) is **not yet defined** - see Risk R1.

---

## 4. Boot / Flash / Debug Workflow

### Boot sequence

```
Power-on / reset
  └─ Gecko Bootloader
       ├─ Check OTA upgrade slot for pending image
       ├─ Verify image signature (public key in bootloader)
       ├─ CRC / integrity check
       └─ Jump to application
            └─ CMSIS SystemInit
                 └─ GSDK platform init (clocks, watchdog, EMU)
                      └─ HAL init (bus, ADC, power)
                           └─ Zigbee stack init (EmberZNet)
                                └─ Main event loop
```

### Flash workflow

| Stage | Method |
|-------|--------|
| Development | J-Link SWD via `commander flash --device EFR32MG24 --serialno <sn> app.gbl` |
| CI | `commander` CLI in pipeline, device attached via J-Link |
| Production | OTA via Zigbee OTA Upgrade cluster (ZCL 0x0019) or J-Link production fixture |

### Debug

- **SWD:** SWDIO + SWDCK on XIAO debug pads (2-wire).
- **UART log:** J-Link CDC VCOM, 115200 8N1 - active only during development builds.
- **RTT:** Preferred for low-power debug (no UART wake penalty in EM2).
- **Energy Profiler:** Simplicity Studio, for sleep current measurement at M3.

---

## 5. Low-Power / Wake-Sleep Model

### Energy modes (EFR32MG24)

| Mode | Core | HF clocks | LF clocks | Typical current | Use |
|------|------|-----------|-----------|----------------|-----|
| EM0 | Active | On | On | ~5 mA | Measurement, TX |
| EM1 | Sleeping | On | On | ~1-2 mA | DMA, IADC running |
| EM2 | Deep sleep | Off | On (LFXO) | ~2-10 uA | Primary idle state |
| EM3 | Stop | Off | Off | ~1 uA | Long intervals only |

**Target:** EM2 between measurement cycles. EM3 only if measurement interval exceeds 60 s and Zigbee poll constraints permit.

### Wake sources

1. **RTCC periodic timer** (primary): configurable interval, default 10 s.
2. **Analog threshold interrupt** (AFE): immediate wake on pressure event exceeding threshold.
3. **Zigbee stack events**: sleepy end-device poll timer, keep-alive.

### Sleepy End Device (SZED) constraints

- Zigbee Sleepy End Device mode requires periodic poll to coordinator.
- Poll interval sets the practical floor for sleep depth and wake frequency.
- Target poll interval: >= 30 s for low-power operation (to be aligned with product latency spec).
- Average current target: **< 50 uA** - unvalidated until M3 bench measurement.

### Cycle model

```
Wake (RTCC or AFE interrupt)
  └─ EM0: sensor read + optional ZCL report
       └─ EM0/EM1: Zigbee TX (if data to send)
            └─ EM2: deep sleep until next wake source
```

---

## 6. OTA Readiness Constraints

### Bootloader configuration

- Gecko Bootloader with **slot-based upgrade** (two application slots: running + candidate).
- Signature verification mandatory on every image load.
- Public key embedded in bootloader image; private key never in this repo.
- On failed verification or CRC mismatch: **revert to running image** (no brick path).
- Watchdog must fire if application does not boot within a timeout after upgrade.

### OTA transport (V1)

- **Zigbee OTA Upgrade cluster** (ZCL 0x0019).
- Image format: `.gbl` (Gecko Bootloader format).
- Image distribution: coordinator-side OTA server (ZHA or Zigbee2MQTT).
- Version monotonic increment enforced by bootloader.

### Flash partition constraint

- Bootloader + 2x application slots must fit in 1536 kB flash.
- EmberZNet Zigbee stack footprint: ~350-450 kB (estimated) - must be measured at M1.
- If footprint exceeds ~600 kB, dual-slot OTA becomes tight. Mitigation: evaluate compressed upgrade or single-slot with recovery.

---

## 7. Protocol Tracks

| Track | Status | Notes |
|-------|--------|-------|
| Zigbee (ZHA) | **V1 shipping path** | Full EmberZNet stack, OTA, ZCL clusters |
| BLE | Future track | Not in V1 firmware; DMP implications not yet evaluated |
| Matter / Thread | Future track | Separate track - see `matter-thread-ble-roadmap` skill |
| Wi-Fi | **Out of scope** | No Wi-Fi stack in device firmware |

**Dynamic Multiprotocol (DMP):** EFR32MG24 supports concurrent Zigbee + BLE via RAIL scheduling. This is **not in V1**. Before any DMP proposal, memory, power budget, timing, and certification cost must be explicitly evaluated (see agent rule 7-8).

---

## 8. First Bring-Up Milestones

### M0 - Hardware alive
- [ ] J-Link connects via SWD, device recognized
- [ ] Flash erase and write succeeds
- [ ] Blink application runs (GPIO LED toggle at 1 Hz)
- [ ] UART/RTT log output received on host

### M1 - Sensor HAL
- [ ] Selected bus (I2C / SPI / ADC) initializes without fault
- [ ] Raw sensor value readable via `sensor_read()`
- [ ] Unit test for HAL mock passes on host (no hardware required)
- [ ] First flash footprint measurement: GSDK + Zigbee stack + sensor driver

### M2 - Zigbee join
- [ ] EmberZNet stack initializes
- [ ] Device joins test Zigbee network (coordinator: ZHA or Zigbee2MQTT)
- [ ] Basic ZCL attribute (e.g., pressure reading) reported to coordinator
- [ ] Device visible in Home Assistant ZHA device list

### M3 - Sleep/wake cycle
- [ ] EM2 reached after idle (confirmed via Energy Profiler)
- [ ] RTCC wake fires at configured interval
- [ ] Measure -> report -> sleep cycle executes deterministically
- [ ] Average sleep current measured (target: < 50 uA)

### M4 - OTA readiness
- [ ] Gecko Bootloader flashed and functional (blinks after bootloader jump)
- [ ] Signed `.gbl` image built via CI pipeline
- [ ] OTA upgrade applied over Zigbee on bench
- [ ] Revert path tested: corrupted image -> device stays on running image
- [ ] Watchdog reboot on upgrade hang confirmed

---

## 9. Open Technical Risks and Unknowns

| ID | Risk | Impact | Action |
|----|------|--------|--------|
| R1 | **Sensor interface type undefined** - I2C, SPI, or analog unknown | HAL depth, ADC path, pin assignment | Define sensor BOM before HAL implementation |
| R2 | **Flash partition sizing unvalidated** - dual-slot OTA may be tight in 1536 kB | OTA capability in V1 | Build minimal Zigbee app, measure flash footprint at M1 |
| R3 | **SZED poll latency not specified** - acceptable delay for hydraulic monitoring undefined | Sleep depth vs. responsiveness | Define max measurement-to-report latency in product spec |
| R4 | **Energy budget not bench-validated** | Battery life estimate unreliable | Bench measurement at M3 milestone |
| R5 | **DMP not evaluated** | If BLE added later, memory/power/cert cost unknown | Defer to future track; do not assume DMP in V1 |
| R6 | **XIAO MG24 GPIO pin conflicts** - sensor + debug + radio pin mapping not verified | Board respins | Review EFR32MG24 datasheet and XIAO schematic before hardware layout |
| R7 | **Signing key infrastructure undefined** | Production OTA not possible without key management process | Define key storage and signing workflow before production build |
| R8 | **GSDK version and toolchain not pinned** | Reproducible builds not guaranteed | Pin GSDK version and arm-none-eabi-gcc version in toolchain file |

---

## 10. Minimal Repo Structure Additions (V1)

Files and folders to create beyond current scaffolding:

```
sensor-platform/firmware/
├── bootloader/
│   └── mg24-bootloader/           # Gecko Bootloader .slcp project
├── devices/
│   └── hydraulic-sensor/
│       ├── src/
│       │   ├── main.c
│       │   ├── app.c / app.h       # Event loop, ZCL handlers
│       │   └── sensor-task.c/h     # Measurement task
│       ├── config/
│       │   ├── zcl-config.zap      # ZCL cluster configuration
│       │   └── board-config.h      # Pin assignments, board ID
│       └── hydraulic-sensor.slcp  # GSDK project file
├── shared/
│   ├── hal/
│   │   ├── sensor.h
│   │   ├── adc.h
│   │   ├── bus.h
│   │   └── power.h
│   └── drivers/
│       └── (sensor driver when BOM defined)
└── signing-public/
    └── app-signing.pem

sensor-platform/tests/
├── unit/
│   ├── hal-mock/                  # Host-side HAL mock implementations
│   └── sensor-logic/             # Unit tests for measurement logic
└── hil/
    └── mg24-bringup/             # J-Link + UART bringup scripts, energy profiler automation

docs/
├── architecture/
│   └── firmware-baseline.md      # This document
└── protocols/
    └── zigbee-v1.md              # Zigbee cluster model, ZHA integration spec (to be created)
```

---

## References

- `docs/hardware/antenna-baseline.md` - antenna selection and compliance constraints
- `docs/architecture/repo-map.md` - monorepo structure overview
- `.claude/agents/firmware-mg24.md` - firmware agent scope and rules
- `.claude/skills/zigbee-ha-v1/` - Zigbee V1 skill (cluster model, ZHA integration)
- `.claude/skills/matter-thread-ble-roadmap/` - future protocol tracks
