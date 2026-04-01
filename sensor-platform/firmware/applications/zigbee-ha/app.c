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

// ---------------------------------------------------------------------------
// Product identity strings (ZCL char-string: 1-byte length + UTF-8, no NUL)
// NOTE: lengths must match exactly the byte counts below.
// ---------------------------------------------------------------------------
#define NOWA_MANUFACTURER_NAME   "\x0BnowaControl"        /* 11 chars */
#define NOWA_MODEL_IDENTIFIER    "\x13Hydraulic Sensor V1" /* 19 chars */
#define NOWA_SW_BUILD_ID         "\x0E""2026.04.01-1.0"   /* 14 chars */
#define NOWA_HW_VERSION          ((uint8_t)1u)
/* ZCL power source 0x03 = single battery; already the generated default */
#define NOWA_POWER_SOURCE_ZCL    ((uint8_t)0x03u)

// ---------------------------------------------------------------------------
// Zigbee endpoint IDs
// ---------------------------------------------------------------------------
#define ENDPOINT_VORLAUF    1
#define ENDPOINT_RUECKLAUF  2

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

// ---------------------------------------------------------------------------
// Forward declarations
// ---------------------------------------------------------------------------
static void measurement_event_handler(sl_zigbee_af_event_t *event);
static void steering_event_handler(sl_zigbee_af_event_t *event);
static void led_event_handler(sl_zigbee_af_event_t *event);
static void update_temperature_attribute(uint8_t endpoint, float temperature);
static void init_external_antenna(void);
static void init_basic_cluster_attributes(void);

// ---------------------------------------------------------------------------
// Application init (called once at startup)
// ---------------------------------------------------------------------------

void sl_zigbee_af_main_init_cb(void)
{
  /* ---- 1. Persistent configuration ------------------------------------ */
  nowa_config_init();

  /* ---- 2. CLI commands ------------------------------------------------- */
  nowa_cli_init();

  /* ---- 3. External antenna --------------------------------------------- */
  init_external_antenna();

  /* ---- 4. Events ------------------------------------------------------- */
  sl_zigbee_af_event_init(&measurement_event, measurement_event_handler);
  sl_zigbee_af_event_init(&steering_event,    steering_event_handler);
  sl_zigbee_af_event_init(&led_event,         led_event_handler);

  /* ---- 5. Basic Cluster product identity -------------------------------- */
  init_basic_cluster_attributes();

  /* ---- 6. LED startup blink -------------------------------------------- */
  sl_led_turn_on(&sl_led_led0);
  sl_zigbee_af_event_set_delay_ms(&led_event, 500);

  /* ---- 7. Auto-join: start network steering after 5 s ------------------ */
  sl_zigbee_af_event_set_delay_ms(&steering_event, 5000);

  /* ---- 8. Battery ADC -------------------------------------------------- */
  bat_initialized = (nowa_bat_init() == SL_STATUS_OK);

  /* ---- 9. Sensor HAL --------------------------------------------------- */
  sensor_hal_status_t hal_st = sensor_hal_init();
  if (hal_st == SENSOR_HAL_OK) {
    sensor_initialized = true;
    sl_zigbee_app_debug_println("Sensor HAL: %d sensor(s) ready",
                                sensor_hal_get_sensor_count());
  } else {
    sensor_initialized = false;
    sl_zigbee_app_debug_println("Sensor HAL: init failed (%d) – check wiring on PB1",
                                (int)hal_st);
  }

  sl_zigbee_app_debug_println("NowaControl Hydraulic Sensor V1 - init complete");
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

  /* Power source: 0x03 = single-phase battery */
  uint8_t pwr_src = NOWA_POWER_SOURCE_ZCL;
  st = sl_zigbee_af_write_server_attribute(
         ENDPOINT_VORLAUF, ZCL_BASIC_CLUSTER_ID,
         ZCL_POWER_SOURCE_ATTRIBUTE_ID,
         &pwr_src, ZCL_ENUM8_ATTRIBUTE_TYPE);
  if (st != SL_ZIGBEE_ZCL_STATUS_SUCCESS) {
    sl_zigbee_app_debug_println("BasicCluster: pwr_src write failed 0x%02X", st);
  }

  sl_zigbee_app_debug_println("BasicCluster: identity written (nowaControl / Hydraulic Sensor V1)");
}

// ---------------------------------------------------------------------------
// Stack status callback - start measurements when network is up
// ---------------------------------------------------------------------------

void sl_zigbee_af_stack_status_cb(sl_status_t status)
{
  if (status == SL_STATUS_NETWORK_UP) {
    sl_zigbee_app_debug_println("Network UP - starting temperature measurements");
    sl_zigbee_af_event_set_inactive(&steering_event);
    sl_zigbee_af_event_set_delay_ms(&measurement_event, 5000);
  } else if (status == SL_STATUS_NETWORK_DOWN) {
    sl_zigbee_app_debug_println("Network DOWN - will retry steering in 5s");
    sl_zigbee_af_event_set_inactive(&measurement_event);
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
  uint32_t interval_ms = nowa_config_get()->measurement_interval_ms;

  if (!sensor_initialized) {
    sl_zigbee_app_debug_println("Sensor HAL not ready - skipping cycle");
    sl_zigbee_af_event_set_delay_ms(&measurement_event, interval_ms);
    return;
  }

  if (!s_conversion_started) {
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
    const sensor_reading_t *r = sensor_hal_get_reading();

    if (s == SENSOR_HAL_OK || s == SENSOR_HAL_ERR_PARTIAL) {
      if (r->vorlauf_valid) {
        update_temperature_attribute(ENDPOINT_VORLAUF, r->vorlauf_temp);
        sl_zigbee_app_debug_println("Vorlauf:   %d.%02d C",
                                    (int)r->vorlauf_temp,
                                    (int)(r->vorlauf_temp * 100.0f) % 100);
      }
      if (r->ruecklauf_valid) {
        update_temperature_attribute(ENDPOINT_RUECKLAUF, r->ruecklauf_temp);
        sl_zigbee_app_debug_println("Ruecklauf: %d.%02d C",
                                    (int)r->ruecklauf_temp,
                                    (int)(r->ruecklauf_temp * 100.0f) % 100);
      }
      if (r->vorlauf_valid && r->ruecklauf_valid) {
        sl_zigbee_app_debug_println("Delta-T:   %d.%02d C",
                                    (int)r->delta_t,
                                    (int)(r->delta_t * 100.0f) % 100);
      }
    } else {
      sl_zigbee_app_debug_println("Read failed: %d", (int)s);
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
