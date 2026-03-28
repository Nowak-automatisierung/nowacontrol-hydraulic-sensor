/***************************************************************************//**
 * @file sensor_hal.h
 * @brief Sensor Hardware Abstraction Layer for hydraulic temperature sensing
 *
 * High-level abstraction for the NowaControl hydraulic temperature-differential
 * sensor. Manages Vorlauf (supply) and Ruecklauf (return) DS18B20 sensors,
 * computes delta-T, and provides thermal energy measurement support.
 *
 * Usage:
 *   sensor_hal_init();
 *   sensor_hal_read_all();
 *   float dt = sensor_hal_get_delta_t();
 *
 * @copyright 2026 Nowak Automatisierung
 * @license MIT
 ******************************************************************************/

#ifndef SENSOR_HAL_H
#define SENSOR_HAL_H

#include <stdint.h>
#include <stdbool.h>
#include "ds18b20.h"

#ifdef __cplusplus
extern "C" {
#endif

// ---------------------------------------------------------------------------
// Configuration: GPIO pin for 1-Wire bus
// ---------------------------------------------------------------------------
// XIAO MG24 pin mapping:
//   D0 = PA4, D1 = PA5, D2 = PB1, D3 = PB2, D4 = PB3, D5 = PB4
//   D6 = PC7, D7 = PC9, D8 = PD2, D9 = PD3, D10 = PD4
//
// Default: D2 (PB1) for 1-Wire data line
// ---------------------------------------------------------------------------

#ifndef SENSOR_HAL_OW_PORT
#define SENSOR_HAL_OW_PORT   gpioPortB
#endif

#ifndef SENSOR_HAL_OW_PIN
#define SENSOR_HAL_OW_PIN    1
#endif

// ---------------------------------------------------------------------------
// Sensor indices
// ---------------------------------------------------------------------------

#define SENSOR_IDX_VORLAUF   0   /**< Supply temperature sensor index   */
#define SENSOR_IDX_RUECKLAUF 1   /**< Return temperature sensor index   */
#define SENSOR_COUNT         2   /**< Total number of sensors           */

// ---------------------------------------------------------------------------
// Status codes
// ---------------------------------------------------------------------------

typedef enum {
  SENSOR_HAL_OK = 0,             /**< All sensors read successfully      */
  SENSOR_HAL_ERR_INIT,           /**< Initialization failed              */
  SENSOR_HAL_ERR_NO_SENSORS,     /**< No sensors found on bus            */
  SENSOR_HAL_ERR_PARTIAL,        /**< Some sensors failed to read        */
  SENSOR_HAL_ERR_ALL_FAILED,     /**< All sensor reads failed            */
  SENSOR_HAL_ERR_NOT_READY,      /**< Conversion not yet complete        */
} sensor_hal_status_t;

// ---------------------------------------------------------------------------
// Sensor data structure
// ---------------------------------------------------------------------------

/** @brief Complete sensor reading result */
typedef struct {
  float    vorlauf_temp;        /**< Supply temperature in C             */
  float    ruecklauf_temp;      /**< Return temperature in C             */
  float    delta_t;             /**< Temperature differential (V - R)    */
  bool     vorlauf_valid;       /**< true if Vorlauf reading is valid    */
  bool     ruecklauf_valid;     /**< true if Ruecklauf reading is valid  */
  uint32_t timestamp_ms;        /**< Timestamp of last reading           */
  uint16_t read_count;          /**< Total successful read cycles        */
  uint16_t error_count;         /**< Total CRC/read errors               */
} sensor_reading_t;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * @brief Initialize the sensor HAL.
 *
 * Initializes the 1-Wire bus, discovers DS18B20 sensors, and
 * configures them for 12-bit resolution. The first sensor found
 * is assigned as Vorlauf, the second as Ruecklauf.
 *
 * @return SENSOR_HAL_OK on success, error code otherwise.
 */
sensor_hal_status_t sensor_hal_init(void);

/**
 * @brief Start temperature conversion on all sensors.
 *
 * Triggers simultaneous conversion on both sensors using Skip ROM.
 * Call sensor_hal_is_ready() or wait 750ms before reading.
 *
 * @return SENSOR_HAL_OK on success.
 */
sensor_hal_status_t sensor_hal_start_conversion(void);

/**
 * @brief Check if temperature conversion is complete.
 * @return true if sensors are ready to be read.
 */
bool sensor_hal_is_ready(void);

/**
 * @brief Read temperatures from all sensors.
 *
 * Reads scratchpad from both sensors, validates CRC, computes
 * delta-T. Must be called after conversion is complete.
 *
 * @return SENSOR_HAL_OK if both sensors read successfully.
 */
sensor_hal_status_t sensor_hal_read_all(void);

/**
 * @brief Perform a complete measurement cycle (convert + wait + read).
 *
 * Blocking call: starts conversion, waits for completion, reads
 * temperatures. Takes ~750ms at 12-bit resolution.
 *
 * @return SENSOR_HAL_OK if both sensors read successfully.
 */
sensor_hal_status_t sensor_hal_measure(void);

/**
 * @brief Get the latest sensor reading.
 * @return Pointer to the current reading (static, do not free).
 */
const sensor_reading_t* sensor_hal_get_reading(void);

/**
 * @brief Get the Vorlauf (supply) temperature.
 * @return Temperature in C, or DS18B20_INVALID_TEMP on error.
 */
float sensor_hal_get_vorlauf(void);

/**
 * @brief Get the Ruecklauf (return) temperature.
 * @return Temperature in C, or DS18B20_INVALID_TEMP on error.
 */
float sensor_hal_get_ruecklauf(void);

/**
 * @brief Get the temperature differential (Vorlauf - Ruecklauf).
 * @return Delta-T in C, or DS18B20_INVALID_TEMP if invalid.
 */
float sensor_hal_get_delta_t(void);

/**
 * @brief Get the number of discovered sensors.
 * @return Number of DS18B20 sensors on the bus (0, 1, or 2).
 */
uint8_t sensor_hal_get_sensor_count(void);

/**
 * @brief Assign a specific ROM ID to Vorlauf or Ruecklauf.
 *
 * By default, sensors are assigned in discovery order.
 * Use this to explicitly map a known ROM ID to a role.
 *
 * @param index  SENSOR_IDX_VORLAUF or SENSOR_IDX_RUECKLAUF.
 * @param rom    Pointer to the ROM ID to assign.
 * @return SENSOR_HAL_OK on success.
 */
sensor_hal_status_t sensor_hal_assign_sensor(uint8_t index,
                                             const onewire_rom_t *rom);

#ifdef __cplusplus
}
#endif

#endif /* SENSOR_HAL_H */
