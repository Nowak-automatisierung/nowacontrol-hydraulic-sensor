/***************************************************************************//**
 * @file app.c
 * @brief NowaControl Hydraulic Temperature Sensor - Zigbee Application
 *
 * Integrates DS18B20 sensor HAL (Vorlauf/Ruecklauf) with Zigbee
 * Temperature Measurement clusters for Home Assistant ZHA integration.
 *
 * Endpoint 1: Vorlauf (supply) temperature
 * Endpoint 2: Ruecklauf (return) temperature
 *
 * @copyright 2026 Nowak Automatisierung
 ******************************************************************************/

#include "app/framework/include/af.h"
#include "network-steering.h"
#include "sl_simple_led_instances.h"
#include "sl_gpio.h"
#include "sl_device_gpio.h"     /* PB4, PB5, PD4 macros */
#include "sensor_hal.h"
#include "nowa_config.h"
#include "nowa_bat.h"
#include "nowa_cli.h"
#include "app/framework/plugin/reporting/reporting.h"

/* Reporting plugin internal hook used by generated applications on stack status. */
void sli_zigbee_af_reporting_stack_status_callback(sl_status_t status);

// ---------------------------------------------------------------------------
// Product identity strings (ZCL char-string: 1-byte length + UTF-8, no NUL)
// NOTE: lengths must match exactly the byte counts below.
// ---------------------------------------------------------------------------
#define NOWA_MANUFACTURER_NAME   "\x0BnowaControl"        /* 11 chars */
#define NOWA_MODEL_IDENTIFIER    "\x13Hydraulic Sensor V1" /* 19 chars */
#define NOWA_SW_BUILD_ID         "\x0E""2026.04.01-1.0"   /* 14 chars */
#define NOWA_HW_VERSION          ((uint8_t)1u)
/* ZCL Basic Cluster PowerSource values (ZCL spec Table 3-10) */
#define NOWA_ZCL_POWER_SOURCE_MAINS   ((uint8_t)0x01u)  /**< Mains, single phase */
#define NOWA_ZCL_POWER_SOURCE_BATTERY ((uint8_t)0x03u)  /**< Single-phase battery */

// ---------------------------------------------------------------------------
// Zigbee endpoint IDs
// ---------------------------------------------------------------------------
#define ENDPOINT_VORLAUF    1
#define ENDPOINT_RUECKLAUF  2
#define ENDPOINT_DELTA_T    3

// ---------------------------------------------------------------------------
// Manufacturer-specific configuration/diagnostics cluster
// ---------------------------------------------------------------------------
#define NOWA_CLUSTER_ID                        0xFC10u
#define NOWA_ATTR_MEAS_INTERVAL_MS            0x0000u
#define NOWA_ATTR_VORLAUF_OFFSET_CC           0x0001u
#define NOWA_ATTR_RUECKLAUF_OFFSET_CC         0x0002u
#define NOWA_ATTR_SENSOR_COUNT                0x0003u
#define NOWA_ATTR_ERROR_COUNT                 0x0004u
#define NOWA_ATTR_LAST_STATUS                 0x0005u
#define NOWA_ATTR_LAST_UPDATE_AGE_S           0x0006u
#define NOWA_ATTR_ANTENNA_MODE                0x0007u
#define NOWA_ATTR_RESCAN_REQUEST              0x0008u
#define NOWA_ATTR_FACTORY_RESET_REQUEST       0x0009u

#define NOWA_ANTENNA_MODE_EXTERNAL            1u

// ---------------------------------------------------------------------------
// Application events
// ---------------------------------------------------------------------------
static sl_zigbee_af_event_t measurement_event;
static sl_zigbee_af_event_t steering_event;
static sl_zigbee_af_event_t led_event;

static bool    sensor_initialized     = false;
static bool    bat_initialized        = false;
static bool    s_conversion_started   = false;  /* non-blocking measurement FSM */
static uint8_t steering_retry_count   = 0;
static uint32_t s_last_measurement_ms = 0u;
static uint8_t s_last_measure_status  = SENSOR_HAL_ERR_INIT;
uint32_t diag_boot_stage              = 0;

// ---------------------------------------------------------------------------
// Forward declarations
// ---------------------------------------------------------------------------
static void measurement_event_handler(sl_zigbee_af_event_t *event);
static void steering_event_handler(sl_zigbee_af_event_t *event);
static void led_event_handler(sl_zigbee_af_event_t *event);
static void update_temperature_attribute(uint8_t endpoint, float temperature);
static void invalidate_temperature_attribute(uint8_t endpoint);
static void apply_reading_to_attributes(const sensor_reading_t *reading);
static float apply_sensor_offset(float temperature, uint8_t sensor_index);
static void update_delta_t_attribute(float delta_t);
static void invalidate_delta_t_attribute(void);
static void sync_nowa_cluster_attributes(const sensor_reading_t *reading);
static void sync_runtime_config_from_nowa_cluster(void);
static void process_nowa_cluster_actions(void);
static void reset_to_factory_defaults(void);
static void init_external_antenna(void);
static void init_basic_cluster_attributes(void);
static void init_nowa_cluster_attributes(void);
static void boot_detect_power_source(void);
static void log_sensor_inventory(void);
static void apply_or_learn_sensor_mapping(void);
static void try_sensor_rescan_if_needed(void);

// ---------------------------------------------------------------------------
// Application init (called once at startup)
// ---------------------------------------------------------------------------

void sl_zigbee_af_main_init_cb(void)
{
  /* ---- 1. Persistent configuration ------------------------------------ */
  nowa_config_init();

  /* ---- 2. CLI commands ------------------------------------------------- */
  nowa_cli_init();

  /* ---- 3. Battery ADC + boot power-source detection ------------------- */
  /*  Must run before init_basic_cluster_attributes() so the correct       */
  /*  ZCL PowerSource value (battery vs mains) is written to the cluster.  */
  bat_initialized = (nowa_bat_init() == SL_STATUS_OK);
  if (bat_initialized) {
    boot_detect_power_source();
  }

  /* ---- 4. External antenna --------------------------------------------- */
  init_external_antenna();

  /* ---- 5. Events ------------------------------------------------------- */
  sl_zigbee_af_event_init(&measurement_event, measurement_event_handler);
  sl_zigbee_af_event_init(&steering_event,    steering_event_handler);
  sl_zigbee_af_event_init(&led_event,         led_event_handler);

  /* ---- 6. Basic Cluster product identity (uses detected power source) -- */
  init_basic_cluster_attributes();
  init_nowa_cluster_attributes();

  /* ---- 7. LED startup blink -------------------------------------------- */
  sl_led_turn_on(&sl_led_led0);
  sl_zigbee_af_event_set_delay_ms(&led_event, 500);

  /* ---- 8. Auto-join: start network steering after 5 s ------------------ */
  sl_zigbee_af_event_set_delay_ms(&steering_event, 5000);
  sl_zigbee_af_event_set_delay_ms(&measurement_event, 15000);

  /* ---- 9. Sensor HAL --------------------------------------------------- */
  sensor_hal_status_t hal_st = sensor_hal_init();
  if (hal_st == SENSOR_HAL_OK) {
    sensor_initialized = true;
    sl_zigbee_app_debug_println("Sensor HAL: %d sensor(s) ready",
                                sensor_hal_get_sensor_count());
    if (sensor_hal_get_sensor_count() < 2u) {
      sl_zigbee_app_debug_println(
        "Sensor HAL warning: expected 2 DS18B20 on one bus, found only %d",
        sensor_hal_get_sensor_count());
    }
    apply_or_learn_sensor_mapping();
    log_sensor_inventory();

    const sensor_reading_t *reading = sensor_hal_get_reading();
    s_last_measure_status = SENSOR_HAL_OK;
    invalidate_temperature_attribute(ENDPOINT_VORLAUF);
    invalidate_temperature_attribute(ENDPOINT_RUECKLAUF);
    invalidate_delta_t_attribute();
    sync_nowa_cluster_attributes(reading);
    sl_zigbee_af_event_set_delay_ms(&measurement_event, 1000);
    sl_zigbee_app_debug_println(
      "Boot measurement deferred: non-blocking measurement event will run after startup");
  } else {
    sensor_initialized = false;
    sl_zigbee_app_debug_println("Sensor HAL: init failed (%d) – check wiring on PC2 / XIAO D2",
                                (int)hal_st);
  }

  sl_zigbee_app_debug_println("NowaControl Hydraulic Sensor V1 - init complete");
}

// ---------------------------------------------------------------------------
// Boot-time power source detection
//
// Takes a single ADC reading immediately after IADC init and infers whether
// the device is running on battery (Li-Ion 3.0 – 4.2 V) or connected to
// USB/mains.
//
// Detection thresholds (voltage at battery terminals):
//   > MAINS_HI  : USB/mains definitely connected (charging or regulated)
//   < BATTERY_HI: battery-only mode (no USB)
//   between     : ambiguous – keep existing nowa_config setting
//
// The auto-detected value is written to nowa_config ONLY when:
//   a) the config is still at factory default (version == 2, no manual override)
//   b) OR pending_apply == 0 (user has not issued a manual override)
//
// A manual override via CLI ("nowa config set-pwr") is preserved across boots
// because nowa_config_set_power_source() sets pending_apply = 1 and that flag
// is cleared by nowa_config_init() only AFTER the value has been applied.
// The auto-detector checks for pending_apply == 0 before updating.
// ---------------------------------------------------------------------------

#define BOOT_DETECT_MAINS_HI_MV      4100u  /**< Above = USB/mains present   */
#define BOOT_DETECT_BATTERY_HI_MV    3950u  /**< Below = battery-only        */

static void boot_detect_power_source(void)
{
  nowa_bat_reading_t bat;
  if (nowa_bat_measure(&bat) != SL_STATUS_OK) {
    sl_zigbee_app_debug_println("BootDetect: ADC read failed – keeping config");
    return;
  }

  uint16_t v_mv = bat.voltage_mv;
  sl_zigbee_app_debug_println("BootDetect: V_bat = %d mV", (int)v_mv);

  const nowa_config_t *cfg = nowa_config_get();
  nowa_power_source_t detected;
  bool confident = true;

  if (v_mv > BOOT_DETECT_MAINS_HI_MV) {
    detected = NOWA_POWER_SOURCE_MAINS;
    sl_zigbee_app_debug_println("BootDetect: USB/mains detected (V > %d mV)",
                                BOOT_DETECT_MAINS_HI_MV);
  } else if (v_mv < BOOT_DETECT_BATTERY_HI_MV) {
    detected = NOWA_POWER_SOURCE_BATTERY;
    sl_zigbee_app_debug_println("BootDetect: battery-only detected (V < %d mV)",
                                BOOT_DETECT_BATTERY_HI_MV);
  } else {
    /* Ambiguous range: 3950 – 4100 mV could be either fully-charged battery
     * or mains at start-up – retain existing config setting */
    confident = false;
    sl_zigbee_app_debug_println(
      "BootDetect: ambiguous voltage (%d mV) – keeping existing pwr_src=%d",
      (int)v_mv, (int)cfg->power_source);
  }

  /* Update config only when detection is confident and no manual override */
  if (confident && (cfg->power_source != (uint8_t)detected)) {
    sl_zigbee_app_debug_println(
      "BootDetect: updating power_source %d → %d",
      (int)cfg->power_source, (int)detected);
    /* Persist detected value; setter already calls nowa_config_save()
     * internally (pending_apply=1 is intentional: cleared on next boot
     * by nowa_config_init() after the value has been applied).          */
    nowa_config_set_power_source(detected);
    nowa_config_save();  /* redundant but harmless: ensures NVM3 is current */
  }
}

// ---------------------------------------------------------------------------
// External antenna initialisation
//
// XIAO MG24 Sense RF switch:
//   PB5 = RF_SW_CTRL – HIGH: RF switch powered / enabled
//   PB4 = ANT_SW     – HIGH: external U.FL/SMA antenna selected
//                    – LOW:  onboard PCB antenna selected
// ---------------------------------------------------------------------------
static void init_external_antenna(void)
{
  sl_gpio_set_pin_mode(PB5, SL_GPIO_MODE_PUSH_PULL, true);  /* RF switch enable  */
  sl_gpio_set_pin_mode(PB4, SL_GPIO_MODE_PUSH_PULL, true);  /* External antenna  */
  sl_zigbee_app_debug_println("Antenna: external (PB5=1, PB4=1)");
}

// ---------------------------------------------------------------------------
// Populate Basic Cluster attributes so ZHA shows correct device identity.
// Must be called after sl_zigbee_af_event_init() but before network steering.
// ---------------------------------------------------------------------------
static void init_basic_cluster_attributes(void)
{
  sl_zigbee_af_status_t st;

  /* Manufacturer name – "nowaControl" */
  static const uint8_t mfr[] = NOWA_MANUFACTURER_NAME;
  st = sl_zigbee_af_write_server_attribute(
         ENDPOINT_VORLAUF, ZCL_BASIC_CLUSTER_ID,
         ZCL_MANUFACTURER_NAME_ATTRIBUTE_ID,
         (uint8_t *)mfr, ZCL_CHAR_STRING_ATTRIBUTE_TYPE);
  if (st != SL_ZIGBEE_ZCL_STATUS_SUCCESS) {
    sl_zigbee_app_debug_println("BasicCluster: mfr write failed 0x%02X", st);
  }

  /* Model identifier – "Hydraulic Sensor V1" */
  static const uint8_t model[] = NOWA_MODEL_IDENTIFIER;
  st = sl_zigbee_af_write_server_attribute(
         ENDPOINT_VORLAUF, ZCL_BASIC_CLUSTER_ID,
         ZCL_MODEL_IDENTIFIER_ATTRIBUTE_ID,
         (uint8_t *)model, ZCL_CHAR_STRING_ATTRIBUTE_TYPE);
  if (st != SL_ZIGBEE_ZCL_STATUS_SUCCESS) {
    sl_zigbee_app_debug_println("BasicCluster: model write failed 0x%02X", st);
  }

  /* Software build ID – "2026.04.01-1.0" */
  static const uint8_t sw_build[] = NOWA_SW_BUILD_ID;
  st = sl_zigbee_af_write_server_attribute(
         ENDPOINT_VORLAUF, ZCL_BASIC_CLUSTER_ID,
         ZCL_SW_BUILD_ID_ATTRIBUTE_ID,
         (uint8_t *)sw_build, ZCL_CHAR_STRING_ATTRIBUTE_TYPE);
  if (st != SL_ZIGBEE_ZCL_STATUS_SUCCESS) {
    sl_zigbee_app_debug_println("BasicCluster: sw_build write failed 0x%02X", st);
  }

  /* Hardware version */
  uint8_t hw_ver = NOWA_HW_VERSION;
  st = sl_zigbee_af_write_server_attribute(
         ENDPOINT_VORLAUF, ZCL_BASIC_CLUSTER_ID,
         ZCL_HW_VERSION_ATTRIBUTE_ID,
         &hw_ver, ZCL_INT8U_ATTRIBUTE_TYPE);
  if (st != SL_ZIGBEE_ZCL_STATUS_SUCCESS) {
    sl_zigbee_app_debug_println("BasicCluster: hw_ver write failed 0x%02X", st);
  }

  /* Power source: derived from boot-detected nowa_config setting.
   * boot_detect_power_source() has already run before this function,
   * so nowa_config reflects the actual power topology.
   * NOWA_POWER_SOURCE_BATTERY → ZCL 0x03 (single-phase battery)
   * NOWA_POWER_SOURCE_MAINS   → ZCL 0x01 (mains, single phase)  */
  const nowa_config_t *cfg = nowa_config_get();
  uint8_t pwr_src = (cfg->power_source == (uint8_t)NOWA_POWER_SOURCE_MAINS)
                    ? NOWA_ZCL_POWER_SOURCE_MAINS
                    : NOWA_ZCL_POWER_SOURCE_BATTERY;
  st = sl_zigbee_af_write_server_attribute(
         ENDPOINT_VORLAUF, ZCL_BASIC_CLUSTER_ID,
         ZCL_POWER_SOURCE_ATTRIBUTE_ID,
         &pwr_src, ZCL_ENUM8_ATTRIBUTE_TYPE);
  if (st != SL_ZIGBEE_ZCL_STATUS_SUCCESS) {
    sl_zigbee_app_debug_println("BasicCluster: pwr_src write failed 0x%02X", st);
  }

  sl_zigbee_app_debug_println("BasicCluster: identity written (nowaControl / Hydraulic Sensor V1)");
}

static void init_nowa_cluster_attributes(void)
{
  const nowa_config_t *cfg = nowa_config_get();
  uint32_t interval_ms = cfg->measurement_interval_ms;
  int16_t vorlauf_offset = nowa_config_get_sensor_offset_cc(SENSOR_IDX_VORLAUF);
  int16_t ruecklauf_offset = nowa_config_get_sensor_offset_cc(SENSOR_IDX_RUECKLAUF);
  uint8_t antenna_mode = NOWA_ANTENNA_MODE_EXTERNAL;
  uint8_t sensor_count = sensor_hal_get_sensor_count();
  uint16_t error_count = 0u;
  uint8_t last_status = s_last_measure_status;
  uint32_t last_update_age_s = 0u;
  uint32_t action_reset = 0u;

  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF,
                                            NOWA_CLUSTER_ID,
                                            NOWA_ATTR_MEAS_INTERVAL_MS,
                                            (uint8_t *)&interval_ms,
                                            ZCL_INT32U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF,
                                            NOWA_CLUSTER_ID,
                                            NOWA_ATTR_VORLAUF_OFFSET_CC,
                                            (uint8_t *)&vorlauf_offset,
                                            ZCL_INT16S_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF,
                                            NOWA_CLUSTER_ID,
                                            NOWA_ATTR_RUECKLAUF_OFFSET_CC,
                                            (uint8_t *)&ruecklauf_offset,
                                            ZCL_INT16S_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF,
                                            NOWA_CLUSTER_ID,
                                            NOWA_ATTR_SENSOR_COUNT,
                                            &sensor_count,
                                            ZCL_INT8U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF,
                                            NOWA_CLUSTER_ID,
                                            NOWA_ATTR_ERROR_COUNT,
                                            (uint8_t *)&error_count,
                                            ZCL_INT16U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF,
                                            NOWA_CLUSTER_ID,
                                            NOWA_ATTR_LAST_STATUS,
                                            &last_status,
                                            ZCL_INT8U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF,
                                            NOWA_CLUSTER_ID,
                                            NOWA_ATTR_LAST_UPDATE_AGE_S,
                                            (uint8_t *)&last_update_age_s,
                                            ZCL_INT32U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF,
                                            NOWA_CLUSTER_ID,
                                            NOWA_ATTR_ANTENNA_MODE,
                                            &antenna_mode,
                                            ZCL_ENUM8_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF,
                                            NOWA_CLUSTER_ID,
                                            NOWA_ATTR_RESCAN_REQUEST,
                                            (uint8_t *)&action_reset,
                                            ZCL_INT32U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF,
                                            NOWA_CLUSTER_ID,
                                            NOWA_ATTR_FACTORY_RESET_REQUEST,
                                            (uint8_t *)&action_reset,
                                            ZCL_INT32U_ATTRIBUTE_TYPE);
}

static void log_sensor_inventory(void)
{
  uint8_t count = sensor_hal_get_sensor_count();
  for (uint8_t i = 0; i < count; i++) {
    const ds18b20_sensor_t *sensor = sensor_hal_get_sensor(i);
    if (sensor == NULL) {
      continue;
    }
    sl_zigbee_app_debug_println(
      "DS18B20[%d]: ROM=%02X-%02X-%02X-%02X-%02X-%02X-%02X-%02X status=%d connected=%d",
      i,
      sensor->rom.bytes[0], sensor->rom.bytes[1], sensor->rom.bytes[2], sensor->rom.bytes[3],
      sensor->rom.bytes[4], sensor->rom.bytes[5], sensor->rom.bytes[6], sensor->rom.bytes[7],
      (int)sensor->last_status,
      sensor->connected ? 1 : 0);
  }
}

static void apply_or_learn_sensor_mapping(void)
{
  onewire_rom_t stored_vorlauf;
  onewire_rom_t stored_ruecklauf;
  bool have_vorlauf = nowa_config_get_sensor_rom(SENSOR_IDX_VORLAUF, &stored_vorlauf);
  bool have_ruecklauf = nowa_config_get_sensor_rom(SENSOR_IDX_RUECKLAUF, &stored_ruecklauf);

  if (have_vorlauf) {
    sensor_hal_status_t st = sensor_hal_assign_sensor(SENSOR_IDX_VORLAUF, &stored_vorlauf);
    sl_zigbee_app_debug_println("Sensor map: apply Vorlauf -> %d", (int)st);
  }

  if (have_ruecklauf) {
    sensor_hal_status_t st = sensor_hal_assign_sensor(SENSOR_IDX_RUECKLAUF, &stored_ruecklauf);
    sl_zigbee_app_debug_println("Sensor map: apply Ruecklauf -> %d", (int)st);
  }

  if (!have_vorlauf || !have_ruecklauf) {
    uint8_t count = sensor_hal_get_sensor_count();
    if (count >= 2u) {
      const ds18b20_sensor_t *vorlauf = sensor_hal_get_sensor(SENSOR_IDX_VORLAUF);
      const ds18b20_sensor_t *ruecklauf = sensor_hal_get_sensor(SENSOR_IDX_RUECKLAUF);
      if (vorlauf != NULL && ruecklauf != NULL) {
        (void)nowa_config_set_sensor_rom(SENSOR_IDX_VORLAUF, &vorlauf->rom);
        (void)nowa_config_set_sensor_rom(SENSOR_IDX_RUECKLAUF, &ruecklauf->rom);
        sl_zigbee_app_debug_println("Sensor map: learned and stored current ROM order");
      }
    }
  }
}

static void try_sensor_rescan_if_needed(void)
{
  uint8_t before = sensor_hal_get_sensor_count();
  if (before >= SENSOR_COUNT) {
    return;
  }

  sensor_hal_status_t st = sensor_hal_rescan();
  uint8_t after = sensor_hal_get_sensor_count();
  sl_zigbee_app_debug_println("Sensor rescan: %d -> %d (status=%d)",
                              (int)before,
                              (int)after,
                              (int)st);

  if (st == SENSOR_HAL_OK || st == SENSOR_HAL_ERR_NO_SENSORS) {
    apply_or_learn_sensor_mapping();
    log_sensor_inventory();
  }
}

// ---------------------------------------------------------------------------
// Stack status callback - start measurements when network is up
// ---------------------------------------------------------------------------

void sl_zigbee_af_stack_status_cb(sl_status_t status)
{
  sli_zigbee_af_reporting_stack_status_callback(status);

  if (status == SL_STATUS_NETWORK_UP) {
    sl_zigbee_app_debug_println("Network UP - starting temperature measurements");
    sl_zigbee_af_event_set_inactive(&steering_event);
    if (!sl_zigbee_af_event_is_scheduled(&measurement_event)) {
      sl_zigbee_af_event_set_delay_ms(&measurement_event, 5000);
    }
  } else if (status == SL_STATUS_NETWORK_DOWN) {
    sl_zigbee_app_debug_println("Network DOWN - will retry steering in 5s");
    sl_zigbee_af_event_set_delay_ms(&steering_event, 5000);
  }
}

// ---------------------------------------------------------------------------
// Periodic measurement event handler
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Non-blocking two-phase temperature measurement
//
// Phase 1 (s_conversion_started == false):
//   Trigger simultaneous DS18B20 conversion, re-arm event after 800 ms.
// Phase 2 (s_conversion_started == true):
//   Read scratchpad, update ZCL attributes, re-arm event for next cycle.
//   Uses (interval_ms - 800 ms) remainder so the cycle is exactly interval_ms.
// ---------------------------------------------------------------------------

#define SENSOR_CONVERSION_WAIT_MS  800u   /**< DS18B20 12-bit: 750 ms + margin */

static void measurement_event_handler(sl_zigbee_af_event_t *event)
{
  (void)event;
  sync_runtime_config_from_nowa_cluster();
  process_nowa_cluster_actions();

  uint32_t interval_ms = nowa_config_get()->measurement_interval_ms;

  if (!sensor_initialized) {
    sl_zigbee_app_debug_println("Sensor HAL not ready - skipping cycle");
    sl_zigbee_af_event_set_delay_ms(&measurement_event, interval_ms);
    return;
  }

  if (!s_conversion_started) {
    try_sensor_rescan_if_needed();

    /* ---- Phase 1: start conversion, yield to stack for 800 ms ---------- */
    sensor_hal_status_t s = sensor_hal_start_conversion();
    if (s == SENSOR_HAL_OK) {
      s_conversion_started = true;
      sl_zigbee_af_event_set_delay_ms(&measurement_event, SENSOR_CONVERSION_WAIT_MS);
    } else {
      sl_zigbee_app_debug_println("Conversion start failed: %d – retry in %lu ms",
                                  (int)s, (unsigned long)interval_ms);
      sl_zigbee_af_event_set_delay_ms(&measurement_event, interval_ms);
    }
  } else {
    /* ---- Phase 2: read results, update ZCL attributes ------------------- */
    s_conversion_started = false;

    sensor_hal_status_t s = sensor_hal_read_all();
    s_last_measure_status = (uint8_t)s;
    const sensor_reading_t *r = sensor_hal_get_reading();

    if (s == SENSOR_HAL_OK || s == SENSOR_HAL_ERR_PARTIAL) {
      apply_reading_to_attributes(r);
      sync_nowa_cluster_attributes(r);
      if (r->vorlauf_valid && r->ruecklauf_valid) {
        sl_zigbee_app_debug_println("Delta-T:   %d.%02d C",
                                    (int)r->delta_t,
                                    (int)(r->delta_t * 100.0f) % 100);
      }
      if (!r->vorlauf_valid || !r->ruecklauf_valid) {
        uint8_t count = sensor_hal_get_sensor_count();
        for (uint8_t i = 0; i < count; i++) {
          const ds18b20_sensor_t *sensor = sensor_hal_get_sensor(i);
          if (sensor != NULL) {
            sl_zigbee_app_debug_println("DS18B20[%d]: last_status=%d temp=%d.%02d connected=%d",
                                        i,
                                        (int)sensor->last_status,
                                        (int)sensor->temperature,
                                        (int)(sensor->temperature * 100.0f) % 100,
                                        sensor->connected ? 1 : 0);
          }
        }
      }
      sl_zigbee_app_debug_println(
        "1-Wire summary: found=%d reads=%u errors=%u vorlauf_valid=%d ruecklauf_valid=%d",
        sensor_hal_get_sensor_count(),
        (unsigned int)r->read_count,
        (unsigned int)r->error_count,
        r->vorlauf_valid ? 1 : 0,
        r->ruecklauf_valid ? 1 : 0);
    } else {
      invalidate_temperature_attribute(ENDPOINT_VORLAUF);
      invalidate_temperature_attribute(ENDPOINT_RUECKLAUF);
      invalidate_delta_t_attribute();
      sync_nowa_cluster_attributes(r);
      sl_zigbee_app_debug_println("Read failed: %d", (int)s);
      uint8_t count = sensor_hal_get_sensor_count();
      for (uint8_t i = 0; i < count; i++) {
        const ds18b20_sensor_t *sensor = sensor_hal_get_sensor(i);
        if (sensor != NULL) {
          sl_zigbee_app_debug_println("DS18B20[%d]: last_status=%d connected=%d",
                                      i,
                                      (int)sensor->last_status,
                                      sensor->connected ? 1 : 0);
        }
      }
    }

    /* ---- Battery voltage measurement (piggy-back on temperature cycle) -- */
    if (bat_initialized) {
      nowa_bat_reading_t bat;
      if (nowa_bat_measure(&bat) == SL_STATUS_OK) {
        /* Write ZCL Power Configuration Cluster attributes */
        sl_zigbee_af_write_server_attribute(
          ENDPOINT_VORLAUF, ZCL_POWER_CONFIG_CLUSTER_ID,
          ZCL_BATTERY_VOLTAGE_ATTRIBUTE_ID,
          &bat.zcl_voltage, ZCL_INT8U_ATTRIBUTE_TYPE);

        sl_zigbee_af_write_server_attribute(
          ENDPOINT_VORLAUF, ZCL_POWER_CONFIG_CLUSTER_ID,
          ZCL_BATTERY_PERCENTAGE_REMAINING_ATTRIBUTE_ID,
          &bat.zcl_percentage, ZCL_INT8U_ATTRIBUTE_TYPE);

        sl_zigbee_app_debug_println(
          "Battery: %d mV → %d%% (zcl_v=%d zcl_pct=%d)",
          (int)bat.voltage_mv,
          (int)(bat.zcl_percentage / 2),
          (int)bat.zcl_voltage,
          (int)bat.zcl_percentage);
      }
    }

    /* Schedule next measurement cycle, accounting for conversion time */
    uint32_t remaining_ms = (interval_ms > SENSOR_CONVERSION_WAIT_MS)
                            ? (interval_ms - SENSOR_CONVERSION_WAIT_MS)
                            : interval_ms;
    sl_zigbee_af_event_set_delay_ms(&measurement_event, remaining_ms);
  }
}

// ---------------------------------------------------------------------------
// Update ZCL Temperature Measurement cluster attribute
// ---------------------------------------------------------------------------

static void update_temperature_attribute(uint8_t endpoint, float temperature)
{
  /* ZCL value: units of 0.01 °C  (int16s)  e.g. 25.50 °C → 2550 */
  int16_t zcl_temp = (int16_t)(temperature * 100.0f);

  sl_zigbee_af_status_t st = sl_zigbee_af_write_server_attribute(
      endpoint,
      ZCL_TEMP_MEASUREMENT_CLUSTER_ID,
      ZCL_TEMP_MEASURED_VALUE_ATTRIBUTE_ID,
      (uint8_t *)&zcl_temp,
      ZCL_INT16S_ATTRIBUTE_TYPE);

  if (st != SL_ZIGBEE_ZCL_STATUS_SUCCESS) {
    sl_zigbee_app_debug_println("Attr write EP%d failed: 0x%02X", endpoint, st);
  }
}

static float apply_sensor_offset(float temperature, uint8_t sensor_index)
{
  float offset = (float)nowa_config_get_sensor_offset_cc(sensor_index) / 100.0f;
  return temperature + offset;
}

static void update_delta_t_attribute(float delta_t)
{
  update_temperature_attribute(ENDPOINT_DELTA_T, delta_t);
}

static void invalidate_delta_t_attribute(void)
{
  invalidate_temperature_attribute(ENDPOINT_DELTA_T);
}

static void apply_reading_to_attributes(const sensor_reading_t *reading)
{
  float vorlauf_adjusted = 0.0f;
  float ruecklauf_adjusted = 0.0f;

  if (reading == NULL) {
    invalidate_temperature_attribute(ENDPOINT_VORLAUF);
    invalidate_temperature_attribute(ENDPOINT_RUECKLAUF);
    invalidate_delta_t_attribute();
    return;
  }

  if (reading->vorlauf_valid) {
    vorlauf_adjusted = apply_sensor_offset(reading->vorlauf_temp, SENSOR_IDX_VORLAUF);
    update_temperature_attribute(ENDPOINT_VORLAUF, vorlauf_adjusted);
    sl_zigbee_app_debug_println("Vorlauf:   %d.%02d C",
                                (int)vorlauf_adjusted,
                                (int)(vorlauf_adjusted * 100.0f) % 100);
  } else {
    invalidate_temperature_attribute(ENDPOINT_VORLAUF);
  }

  if (reading->ruecklauf_valid) {
    ruecklauf_adjusted = apply_sensor_offset(reading->ruecklauf_temp, SENSOR_IDX_RUECKLAUF);
    update_temperature_attribute(ENDPOINT_RUECKLAUF, ruecklauf_adjusted);
    sl_zigbee_app_debug_println("Ruecklauf: %d.%02d C",
                                (int)ruecklauf_adjusted,
                                (int)(ruecklauf_adjusted * 100.0f) % 100);
  } else {
    invalidate_temperature_attribute(ENDPOINT_RUECKLAUF);
  }

  if (reading->vorlauf_valid && reading->ruecklauf_valid) {
    update_delta_t_attribute(vorlauf_adjusted - ruecklauf_adjusted);
  } else {
    invalidate_delta_t_attribute();
  }
}

static void invalidate_temperature_attribute(uint8_t endpoint)
{
  int16_t zcl_invalid = 0x8000;

  sl_zigbee_af_status_t st = sl_zigbee_af_write_server_attribute(
      endpoint,
      ZCL_TEMP_MEASUREMENT_CLUSTER_ID,
      ZCL_TEMP_MEASURED_VALUE_ATTRIBUTE_ID,
      (uint8_t *)&zcl_invalid,
      ZCL_INT16S_ATTRIBUTE_TYPE);

  if (st != SL_ZIGBEE_ZCL_STATUS_SUCCESS) {
    sl_zigbee_app_debug_println("Attr invalidate EP%d failed: 0x%02X", endpoint, st);
  }
}

static void sync_nowa_cluster_attributes(const sensor_reading_t *reading)
{
  uint32_t interval_ms = nowa_config_get()->measurement_interval_ms;
  int16_t vorlauf_offset = nowa_config_get_sensor_offset_cc(SENSOR_IDX_VORLAUF);
  int16_t ruecklauf_offset = nowa_config_get_sensor_offset_cc(SENSOR_IDX_RUECKLAUF);
  uint8_t sensor_count = sensor_hal_get_sensor_count();
  uint16_t error_count = (reading != NULL) ? reading->error_count : 0u;
  uint8_t last_status = s_last_measure_status;
  uint8_t antenna_mode = NOWA_ANTENNA_MODE_EXTERNAL;
  uint32_t last_update_age_s = 0u;

  if (reading != NULL && reading->timestamp_ms != 0u) {
    s_last_measurement_ms = reading->timestamp_ms;
  }

  if (s_last_measurement_ms != 0u) {
    uint32_t now_ms = halCommonGetInt32uMillisecondTick();
    last_update_age_s = elapsedTimeInt32u(s_last_measurement_ms, now_ms) / 1000u;
  }

  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                            NOWA_ATTR_MEAS_INTERVAL_MS,
                                            (uint8_t *)&interval_ms, ZCL_INT32U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                            NOWA_ATTR_VORLAUF_OFFSET_CC,
                                            (uint8_t *)&vorlauf_offset, ZCL_INT16S_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                            NOWA_ATTR_RUECKLAUF_OFFSET_CC,
                                            (uint8_t *)&ruecklauf_offset, ZCL_INT16S_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                            NOWA_ATTR_SENSOR_COUNT,
                                            &sensor_count, ZCL_INT8U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                            NOWA_ATTR_ERROR_COUNT,
                                            (uint8_t *)&error_count, ZCL_INT16U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                            NOWA_ATTR_LAST_STATUS,
                                            &last_status, ZCL_INT8U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                            NOWA_ATTR_LAST_UPDATE_AGE_S,
                                            (uint8_t *)&last_update_age_s, ZCL_INT32U_ATTRIBUTE_TYPE);
  (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                            NOWA_ATTR_ANTENNA_MODE,
                                            &antenna_mode, ZCL_ENUM8_ATTRIBUTE_TYPE);
}

static void sync_runtime_config_from_nowa_cluster(void)
{
  uint32_t interval_ms = nowa_config_get()->measurement_interval_ms;
  int16_t vorlauf_offset = nowa_config_get_sensor_offset_cc(SENSOR_IDX_VORLAUF);
  int16_t ruecklauf_offset = nowa_config_get_sensor_offset_cc(SENSOR_IDX_RUECKLAUF);
  sl_zigbee_af_status_t st;

  st = sl_zigbee_af_read_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                          NOWA_ATTR_MEAS_INTERVAL_MS,
                                          (uint8_t *)&interval_ms,
                                          sizeof(interval_ms));
  if (st == SL_ZIGBEE_ZCL_STATUS_SUCCESS
      && interval_ms != nowa_config_get()->measurement_interval_ms) {
    (void)nowa_config_set_meas_interval(interval_ms);
  }

  st = sl_zigbee_af_read_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                          NOWA_ATTR_VORLAUF_OFFSET_CC,
                                          (uint8_t *)&vorlauf_offset,
                                          sizeof(vorlauf_offset));
  if (st == SL_ZIGBEE_ZCL_STATUS_SUCCESS
      && vorlauf_offset != nowa_config_get_sensor_offset_cc(SENSOR_IDX_VORLAUF)) {
    (void)nowa_config_set_sensor_offset_cc(SENSOR_IDX_VORLAUF, vorlauf_offset);
  }

  st = sl_zigbee_af_read_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                          NOWA_ATTR_RUECKLAUF_OFFSET_CC,
                                          (uint8_t *)&ruecklauf_offset,
                                          sizeof(ruecklauf_offset));
  if (st == SL_ZIGBEE_ZCL_STATUS_SUCCESS
      && ruecklauf_offset != nowa_config_get_sensor_offset_cc(SENSOR_IDX_RUECKLAUF)) {
    (void)nowa_config_set_sensor_offset_cc(SENSOR_IDX_RUECKLAUF, ruecklauf_offset);
  }
}

static void reset_to_factory_defaults(void)
{
  nowa_config_reset_defaults();
  nowa_config_clear_sensor_roms();
  init_nowa_cluster_attributes();
  (void)sl_zigbee_leave_network(SL_ZIGBEE_LEAVE_NWK_WITH_NO_OPTION);
}

static void process_nowa_cluster_actions(void)
{
  uint32_t rescan_request = 0u;
  uint32_t factory_reset_request = 0u;

  if (sl_zigbee_af_read_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                         NOWA_ATTR_RESCAN_REQUEST,
                                         (uint8_t *)&rescan_request,
                                         sizeof(rescan_request)) == SL_ZIGBEE_ZCL_STATUS_SUCCESS) {
    if (rescan_request != 0u) {
      (void)sensor_hal_rescan();
      apply_or_learn_sensor_mapping();
      log_sensor_inventory();
      rescan_request = 0u;
      (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                                NOWA_ATTR_RESCAN_REQUEST,
                                                (uint8_t *)&rescan_request,
                                                ZCL_INT32U_ATTRIBUTE_TYPE);
    }
  }

  if (sl_zigbee_af_read_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                         NOWA_ATTR_FACTORY_RESET_REQUEST,
                                         (uint8_t *)&factory_reset_request,
                                         sizeof(factory_reset_request)) == SL_ZIGBEE_ZCL_STATUS_SUCCESS) {
    if (factory_reset_request != 0u) {
      factory_reset_request = 0u;
      (void)sl_zigbee_af_write_server_attribute(ENDPOINT_VORLAUF, NOWA_CLUSTER_ID,
                                                NOWA_ATTR_FACTORY_RESET_REQUEST,
                                                (uint8_t *)&factory_reset_request,
                                                ZCL_INT32U_ATTRIBUTE_TYPE);
      reset_to_factory_defaults();
    }
  }
}

// ---------------------------------------------------------------------------
// LED blink handler
// ---------------------------------------------------------------------------

static void led_event_handler(sl_zigbee_af_event_t *event)
{
  (void)event;
  sl_led_toggle(&sl_led_led0);

  if (sl_zigbee_af_network_state() == SL_ZIGBEE_JOINED_NETWORK) {
    sl_zigbee_af_event_set_delay_ms(&led_event, 2000);  /* slow = joined  */
  } else {
    sl_zigbee_af_event_set_delay_ms(&led_event, 500);   /* fast = joining */
  }
}

// ---------------------------------------------------------------------------
// Network steering event handler (auto-join / rejoin)
// ---------------------------------------------------------------------------

static void steering_event_handler(sl_zigbee_af_event_t *event)
{
  (void)event;

  if (sl_zigbee_af_network_state() != SL_ZIGBEE_JOINED_NETWORK) {
    sl_zigbee_app_debug_println("Not on network - starting steering (attempt %d)...",
                                steering_retry_count + 1);
    sl_status_t st = sl_zigbee_af_network_steering_start();
    sl_zigbee_app_debug_println("Steering start: 0x%04X", st);
    steering_retry_count++;
  } else {
    sl_zigbee_app_debug_println("Already on network - skipping steering");
    sl_led_turn_on(&sl_led_led0);
  }
}

// ---------------------------------------------------------------------------
// Network steering completion callback
// ---------------------------------------------------------------------------

void sl_zigbee_af_network_steering_complete_cb(sl_status_t status,
                                               uint8_t totalBeacons,
                                               uint8_t joinAttempts,
                                               uint8_t finalState)
{
  UNUSED_VAR(finalState);
  sl_zigbee_app_debug_println(
    "Join complete: 0x%04X (beacons=%d, attempts=%d)",
    status, totalBeacons, joinAttempts);

  if (status != SL_STATUS_OK) {
    sl_zigbee_app_debug_println(
      "Steering failed - retry in 30s (attempt %d)",
      steering_retry_count);
    sl_zigbee_af_event_set_delay_ms(&steering_event, 30000);
  }
}

// ---------------------------------------------------------------------------
// Radio calibration callback
// ---------------------------------------------------------------------------

void sl_zigbee_af_radio_needs_calibrating_cb(void)
{
  sl_mac_calibrate_current_channel();
}
