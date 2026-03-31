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
#include "sensor_hal.h"

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/** Measurement interval in milliseconds (default: 60 seconds) */
#define MEASUREMENT_INTERVAL_MS  60000

/** Zigbee endpoint IDs */
#define ENDPOINT_VORLAUF    1
#define ENDPOINT_RUECKLAUF  2

// ---------------------------------------------------------------------------
// Event for periodic measurement
// ---------------------------------------------------------------------------

static sl_zigbee_af_event_t measurement_event;
static bool sensor_initialized = false;

// ---------------------------------------------------------------------------
// Forward declarations
// ---------------------------------------------------------------------------

static void measurement_event_handler(sl_zigbee_af_event_t *event);
static void update_temperature_attribute(uint8_t endpoint, float temperature);

// ---------------------------------------------------------------------------
// Application init (called once at startup)
// ---------------------------------------------------------------------------

void sl_zigbee_af_main_init_cb(void)
{
  sl_zigbee_af_event_init(&measurement_event, measurement_event_handler);

  /* Initialize sensor HAL */
  sensor_hal_status_t status = sensor_hal_init();
  if (status == SENSOR_HAL_OK) {
    sensor_initialized = true;
    sl_zigbee_app_debug_println("Sensor HAL initialized: %d sensors found",
                                sensor_hal_get_sensor_count());
  } else {
    sl_zigbee_app_debug_println("Sensor HAL init failed: %d", status);
  }
}

// ---------------------------------------------------------------------------
// Stack status callback - start measurements when network is up
// ---------------------------------------------------------------------------

void sl_zigbee_af_stack_status_cb(sl_status_t status)
{
  if (status == SL_STATUS_NETWORK_UP) {
    sl_zigbee_app_debug_println("Network UP - starting temperature measurements");

    /* Start periodic measurement */
    sl_zigbee_af_event_set_delay_ms(&measurement_event, 5000); /* First read after 5s */
  } else if (status == SL_STATUS_NETWORK_DOWN) {
    sl_zigbee_app_debug_println("Network DOWN");
    sl_zigbee_af_event_set_inactive(&measurement_event);
  }
}

// ---------------------------------------------------------------------------
// Periodic measurement event handler
// ---------------------------------------------------------------------------

static void measurement_event_handler(sl_zigbee_af_event_t *event)
{
  (void)event;

  if (!sensor_initialized) {
    /* Try to reinitialize sensors */
    sensor_hal_status_t init_status = sensor_hal_init();
    if (init_status == SENSOR_HAL_OK) {
      sensor_initialized = true;
      sl_zigbee_app_debug_println("Sensor HAL re-initialized OK");
    } else {
      sl_zigbee_app_debug_println("Sensor init retry failed");
      sl_zigbee_af_event_set_delay_ms(&measurement_event, MEASUREMENT_INTERVAL_MS);
      return;
    }
  }

  /* Perform blocking measurement (~750ms) */
  sensor_hal_status_t status = sensor_hal_measure();
  const sensor_reading_t *reading = sensor_hal_get_reading();

  if (status == SENSOR_HAL_OK || status == SENSOR_HAL_ERR_PARTIAL) {
    /* Update Vorlauf (Endpoint 1) */
    if (reading->vorlauf_valid) {
      update_temperature_attribute(ENDPOINT_VORLAUF, reading->vorlauf_temp);
      sl_zigbee_app_debug_println("Vorlauf: %d.%02d C",
                                  (int)reading->vorlauf_temp,
                                  (int)(reading->vorlauf_temp * 100) % 100);
    }

    /* Update Ruecklauf (Endpoint 2) */
    if (reading->ruecklauf_valid) {
      update_temperature_attribute(ENDPOINT_RUECKLAUF, reading->ruecklauf_temp);
      sl_zigbee_app_debug_println("Ruecklauf: %d.%02d C",
                                  (int)reading->ruecklauf_temp,
                                  (int)(reading->ruecklauf_temp * 100) % 100);
    }

    /* Log delta-T */
    if (reading->vorlauf_valid && reading->ruecklauf_valid) {
      sl_zigbee_app_debug_println("Delta-T: %d.%02d C",
                                  (int)reading->delta_t,
                                  (int)(reading->delta_t * 100) % 100);
    }
  } else {
    sl_zigbee_app_debug_println("Measurement failed: %d", status);
  }

  /* Schedule next measurement */
  sl_zigbee_af_event_set_delay_ms(&measurement_event, MEASUREMENT_INTERVAL_MS);
}

// ---------------------------------------------------------------------------
// Update Zigbee Temperature Measurement cluster attribute
// ---------------------------------------------------------------------------

static void update_temperature_attribute(uint8_t endpoint, float temperature)
{
  /* ZCL Temperature Measurement: value in units of 0.01 C (int16s)
   * Example: 25.50 C -> 2550 */
  int16_t zcl_temp = (int16_t)(temperature * 100.0f);

  sl_zigbee_af_status_t status = sl_zigbee_af_write_server_attribute(
      endpoint,
      ZCL_TEMP_MEASUREMENT_CLUSTER_ID,
      ZCL_TEMP_MEASURED_VALUE_ATTRIBUTE_ID,
      (uint8_t *)&zcl_temp,
      ZCL_INT16S_ATTRIBUTE_TYPE);

  if (status != SL_ZIGBEE_ZCL_STATUS_SUCCESS) {
    sl_zigbee_app_debug_println("Attr write EP%d failed: 0x%02X", endpoint, status);
  }
}

// ---------------------------------------------------------------------------
// Network steering callback
// ---------------------------------------------------------------------------

void sl_zigbee_af_network_steering_complete_cb(sl_status_t status,
                                               uint8_t totalBeacons,
                                               uint8_t joinAttempts,
                                               uint8_t finalState)
{
  UNUSED_VAR(totalBeacons);
  UNUSED_VAR(joinAttempts);
  UNUSED_VAR(finalState);
  sl_zigbee_app_debug_println("%s network %s: 0x%02X", "Join", "complete", status);
}

// ---------------------------------------------------------------------------
// Radio calibration callback
// ---------------------------------------------------------------------------

void sl_zigbee_af_radio_needs_calibrating_cb(void)
{
  sl_mac_calibrate_current_channel();
}
