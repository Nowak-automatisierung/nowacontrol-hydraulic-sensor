/***************************************************************************//**
 * @file sensor_hal.c
 * @brief Sensor HAL implementation for hydraulic temperature sensing
 *
 * @copyright 2026 Nowak Automatisierung
 * @license MIT
 ******************************************************************************/

#include "sensor_hal.h"
#include "sl_sleeptimer.h"
#include <string.h>

// ---------------------------------------------------------------------------
// Private state
// ---------------------------------------------------------------------------

/** @brief 1-Wire bus configuration */
static onewire_bus_t s_bus = {
  .port = SENSOR_HAL_OW_PORT,
  .pin  = SENSOR_HAL_OW_PIN,
};

/** @brief DS18B20 sensor handles */
static ds18b20_sensor_t s_sensors[SENSOR_COUNT];

/** @brief Number of discovered sensors */
static uint8_t s_sensor_count = 0;

/** @brief Current sensor reading */
static sensor_reading_t s_reading = {
  .vorlauf_temp   = DS18B20_INVALID_TEMP,
  .ruecklauf_temp = DS18B20_INVALID_TEMP,
  .delta_t        = DS18B20_INVALID_TEMP,
  .vorlauf_valid  = false,
  .ruecklauf_valid = false,
  .timestamp_ms   = 0,
  .read_count     = 0,
  .error_count    = 0,
};

/** @brief Initialization flag */
static bool s_initialized = false;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

sensor_hal_status_t sensor_hal_init(void)
{
  /* Discover DS18B20 sensors on the 1-Wire bus */
  s_sensor_count = ds18b20_init(&s_bus, s_sensors, SENSOR_COUNT);

  if (s_sensor_count == 0) {
    s_initialized = false;
    return SENSOR_HAL_ERR_NO_SENSORS;
  }

  /* Reset reading state */
  memset(&s_reading, 0, sizeof(sensor_reading_t));
  s_reading.vorlauf_temp = DS18B20_INVALID_TEMP;
  s_reading.ruecklauf_temp = DS18B20_INVALID_TEMP;
  s_reading.delta_t = DS18B20_INVALID_TEMP;

  s_initialized = true;
  return SENSOR_HAL_OK;
}

sensor_hal_status_t sensor_hal_rescan(void)
{
  /* Re-run discovery on the live bus. Keep counters, but refresh the sensor list. */
  uint16_t read_count = s_reading.read_count;
  uint16_t error_count = s_reading.error_count;
  uint32_t timestamp_ms = s_reading.timestamp_ms;

  sensor_hal_status_t status = sensor_hal_init();

  s_reading.read_count = read_count;
  s_reading.error_count = error_count;
  s_reading.timestamp_ms = timestamp_ms;

  return status;
}

sensor_hal_status_t sensor_hal_start_conversion(void)
{
  if (!s_initialized) {
    return SENSOR_HAL_ERR_INIT;
  }

  /* Start conversion on all sensors simultaneously */
  ds18b20_status_t status = ds18b20_start_conversion_all(&s_bus);
  if (status != DS18B20_OK) {
    return SENSOR_HAL_ERR_ALL_FAILED;
  }

  return SENSOR_HAL_OK;
}

bool sensor_hal_is_ready(void)
{
  return ds18b20_is_conversion_done(&s_bus);
}

sensor_hal_status_t sensor_hal_read_all(void)
{
  if (!s_initialized) {
    return SENSOR_HAL_ERR_INIT;
  }

  /* Start every read cycle from a known-invalid state so HA never keeps
   * stale temperatures when a sensor disappears or the bus glitches. */
  s_reading.vorlauf_temp = DS18B20_INVALID_TEMP;
  s_reading.ruecklauf_temp = DS18B20_INVALID_TEMP;
  s_reading.delta_t = DS18B20_INVALID_TEMP;
  s_reading.vorlauf_valid = false;
  s_reading.ruecklauf_valid = false;

  uint8_t success_count = 0;

  /* Read Vorlauf (sensor index 0) */
  if (s_sensor_count > SENSOR_IDX_VORLAUF && s_sensors[SENSOR_IDX_VORLAUF].connected) {
    ds18b20_status_t status = ds18b20_read_temperature(&s_bus,
                                                       &s_sensors[SENSOR_IDX_VORLAUF]);
    if (status == DS18B20_OK) {
      s_reading.vorlauf_temp = s_sensors[SENSOR_IDX_VORLAUF].temperature;
      s_reading.vorlauf_valid = true;
      success_count++;
    } else {
      s_reading.vorlauf_valid = false;
      s_reading.error_count++;
    }
  }

  /* Read Ruecklauf (sensor index 1) */
  if (s_sensor_count > SENSOR_IDX_RUECKLAUF && s_sensors[SENSOR_IDX_RUECKLAUF].connected) {
    ds18b20_status_t status = ds18b20_read_temperature(&s_bus,
                                                       &s_sensors[SENSOR_IDX_RUECKLAUF]);
    if (status == DS18B20_OK) {
      s_reading.ruecklauf_temp = s_sensors[SENSOR_IDX_RUECKLAUF].temperature;
      s_reading.ruecklauf_valid = true;
      success_count++;
    } else {
      s_reading.ruecklauf_valid = false;
      s_reading.error_count++;
    }
  }

  /* Compute delta-T if both readings are valid */
  if (s_reading.vorlauf_valid && s_reading.ruecklauf_valid) {
    s_reading.delta_t = s_reading.vorlauf_temp - s_reading.ruecklauf_temp;
  } else {
    s_reading.delta_t = DS18B20_INVALID_TEMP;
  }

  /* Update timestamp */
  uint32_t tick_count = sl_sleeptimer_get_tick_count();
  s_reading.timestamp_ms = sl_sleeptimer_tick_to_ms(tick_count);

  /* Update read counter */
  if (success_count > 0) {
    s_reading.read_count++;
  }

  /* Return appropriate status */
  if (success_count == 0) {
    return SENSOR_HAL_ERR_ALL_FAILED;
  } else if (success_count < s_sensor_count) {
    return SENSOR_HAL_ERR_PARTIAL;
  }
  return SENSOR_HAL_OK;
}

sensor_hal_status_t sensor_hal_measure(void)
{
  sensor_hal_status_t status;

  /* Start conversion */
  status = sensor_hal_start_conversion();
  if (status != SENSOR_HAL_OK) {
    return status;
  }

  /* Wait for conversion (750ms at 12-bit resolution) */
  uint16_t wait_ms = ds18b20_get_conversion_time_ms(DS18B20_RESOLUTION_12BIT);
  sl_sleeptimer_delay_millisecond(wait_ms + 10); /* +10ms safety margin */

  /* Read results */
  return sensor_hal_read_all();
}

const sensor_reading_t* sensor_hal_get_reading(void)
{
  return &s_reading;
}

float sensor_hal_get_vorlauf(void)
{
  return s_reading.vorlauf_valid ? s_reading.vorlauf_temp : DS18B20_INVALID_TEMP;
}

float sensor_hal_get_ruecklauf(void)
{
  return s_reading.ruecklauf_valid ? s_reading.ruecklauf_temp : DS18B20_INVALID_TEMP;
}

float sensor_hal_get_delta_t(void)
{
  return (s_reading.vorlauf_valid && s_reading.ruecklauf_valid)
         ? s_reading.delta_t
         : DS18B20_INVALID_TEMP;
}

uint8_t sensor_hal_get_sensor_count(void)
{
  return s_sensor_count;
}

const ds18b20_sensor_t* sensor_hal_get_sensor(uint8_t index)
{
  if (index >= s_sensor_count) {
    return NULL;
  }
  return &s_sensors[index];
}

sensor_hal_status_t sensor_hal_assign_sensor(uint8_t index,
                                             const onewire_rom_t *rom)
{
  if (index >= SENSOR_COUNT) {
    return SENSOR_HAL_ERR_INIT;
  }

  /* Search for matching ROM in discovered sensors */
  for (uint8_t i = 0; i < s_sensor_count; i++) {
    bool match = true;
    for (uint8_t j = 0; j < 8; j++) {
      if (s_sensors[i].rom.bytes[j] != rom->bytes[j]) {
        match = false;
        break;
      }
    }
    if (match) {
      /* Swap sensors if needed */
      if (i != index) {
        ds18b20_sensor_t tmp = s_sensors[index];
        s_sensors[index] = s_sensors[i];
        s_sensors[i] = tmp;
      }
      return SENSOR_HAL_OK;
    }
  }

  return SENSOR_HAL_ERR_NO_SENSORS;
}
