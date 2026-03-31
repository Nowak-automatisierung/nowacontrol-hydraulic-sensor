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
static sl_zigbee_af_event_t steering_event;
static sl_zigbee_af_event_t led_event;
static bool sensor_initialized = false;
static uint8_t steering_retry_count = 0;

// ---------------------------------------------------------------------------
// Forward declarations
// ---------------------------------------------------------------------------

static void measurement_event_handler(sl_zigbee_af_event_t *event);
static void steering_event_handler(sl_zigbee_af_event_t *event);
static void led_event_handler(sl_zigbee_af_event_t *event);
static void update_temperature_attribute(uint8_t endpoint, float temperature);

// ---------------------------------------------------------------------------
// Application init (called once at startup)
// ---------------------------------------------------------------------------

void sl_zigbee_af_main_init_cb(void)
{
  sl_zigbee_af_event_init(&measurement_event, measurement_event_handler);
  sl_zigbee_af_event_init(&steering_event, steering_event_handler);
  sl_zigbee_af_event_init(&led_event, led_event_handler);

  /* Blink LED to confirm firmware is running */
  sl_led_turn_on(&sl_led_led0);
  sl_zigbee_af_event_set_delay_ms(&led_event, 500);

  /* Auto-join: start network steering after 5 seconds if not on a network */
  sl_zigbee_af_event_set_delay_ms(&steering_event, 5000);

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
// LED blink handler - visual confirmation that firmware is running
// ---------------------------------------------------------------------------

static void led_event_handler(sl_zigbee_af_event_t *event)
{
  (void)event;
  sl_led_toggle(&sl_led_led0);

  /* Blink fast (500ms) while not on network, slow (2s) when joined */
  sl_status_t net_status = sl_zigbee_af_network_state();
  if (net_status == SL_ZIGBEE_JOINED_NETWORK) {
    sl_zigbee_af_event_set_delay_ms(&led_event, 2000);
  } else {
    sl_zigbee_af_event_set_delay_ms(&led_event, 500);
  }
}

// ---------------------------------------------------------------------------
// Auto-join: start network steering if not on a network
// ---------------------------------------------------------------------------

static void steering_event_handler(sl_zigbee_af_event_t *event)
{
  (void)event;

  /* Only start steering if we are NOT already on a network */
  sl_status_t net_status = sl_zigbee_af_network_state();
  if (net_status != SL_ZIGBEE_JOINED_NETWORK) {
    sl_zigbee_app_debug_println("Not on network - starting steering (attempt %d)...",
                                steering_retry_count + 1);
    sl_status_t steer_status = sl_zigbee_af_network_steering_start();
    sl_zigbee_app_debug_println("Steering start returned: 0x%04X", steer_status);
    steering_retry_count++;
  } else {
    sl_zigbee_app_debug_println("Already on network - skipping steering");
    sl_led_turn_on(&sl_led_led0); /* Solid LED = joined */
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
  sl_zigbee_app_debug_println("Join complete: 0x%04X (beacons=%d, attempts=%d)",
                              status, totalBeacons, joinAttempts);

  if (status != SL_STATUS_OK && steering_retry_count < 5) {
    /* Retry steering after 10 seconds */
    sl_zigbee_app_debug_println("Steering failed - retry in 10s...");
    sl_zigbee_af_event_set_delay_ms(&steering_event, 10000);
  }
}

// ---------------------------------------------------------------------------
// Radio calibration callback
// ---------------------------------------------------------------------------

void sl_zigbee_af_radio_needs_calibrating_cb(void)
{
  sl_mac_calibrate_current_channel();
}
