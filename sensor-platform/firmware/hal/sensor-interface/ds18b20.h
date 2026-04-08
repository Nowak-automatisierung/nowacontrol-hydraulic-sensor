/***************************************************************************//**
 * @file ds18b20.h
 * @brief DS18B20 digital temperature sensor driver
 *
 * Driver for Maxim/Analog Devices DS18B20 1-Wire temperature sensor.
 * Supports multiple sensors on a single bus, 12-bit resolution (0.0625 C),
 * and CRC8 validation of all scratchpad reads.
 *
 * @copyright 2026 Nowak Automatisierung
 * @license MIT
 ******************************************************************************/

#ifndef DS18B20_H
#define DS18B20_H

#include <stdint.h>
#include <stdbool.h>
#include "onewire.h"

#ifdef __cplusplus
extern "C" {
#endif

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

#define DS18B20_FAMILY_CODE          0x28
#define DS18B20_MAX_SENSORS          2    /**< Max sensors on one bus */
#define DS18B20_INVALID_TEMP         (-999.0f)

// ---------------------------------------------------------------------------
// DS18B20 commands
// ---------------------------------------------------------------------------

#define DS18B20_CMD_CONVERT_T        0x44  /**< Start temperature conversion */
#define DS18B20_CMD_READ_SCRATCHPAD  0xBE  /**< Read 9-byte scratchpad      */
#define DS18B20_CMD_WRITE_SCRATCHPAD 0x4E  /**< Write TH, TL, config        */
#define DS18B20_CMD_COPY_SCRATCHPAD  0x48  /**< Copy scratchpad to EEPROM   */
#define DS18B20_CMD_RECALL_E2        0xB8  /**< Recall EEPROM to scratchpad */
#define DS18B20_CMD_READ_POWER       0xB4  /**< Read power supply mode      */

// ---------------------------------------------------------------------------
// Resolution configuration
// ---------------------------------------------------------------------------

typedef enum {
  DS18B20_RESOLUTION_9BIT  = 0x1F,  /**<  93.75 ms conversion, 0.5 C     */
  DS18B20_RESOLUTION_10BIT = 0x3F,  /**< 187.50 ms conversion, 0.25 C    */
  DS18B20_RESOLUTION_11BIT = 0x5F,  /**< 375.00 ms conversion, 0.125 C   */
  DS18B20_RESOLUTION_12BIT = 0x7F,  /**< 750.00 ms conversion, 0.0625 C  */
} ds18b20_resolution_t;

// ---------------------------------------------------------------------------
// Status codes
// ---------------------------------------------------------------------------

typedef enum {
  DS18B20_OK = 0,               /**< Operation successful            */
  DS18B20_ERR_NO_DEVICE,        /**< No device found on bus          */
  DS18B20_ERR_CRC,              /**< CRC8 validation failed          */
  DS18B20_ERR_NOT_DS18B20,      /**< Device is not a DS18B20         */
  DS18B20_ERR_CONVERSION,       /**< Temperature conversion failed   */
  DS18B20_ERR_DISCONNECTED,     /**< Sensor disconnected (85.0 C)    */
  DS18B20_ERR_BUS_PATTERN,      /**< Invalid all-0/all-1 bus pattern */
} ds18b20_status_t;

// ---------------------------------------------------------------------------
// Sensor handle
// ---------------------------------------------------------------------------

/** @brief DS18B20 sensor instance */
typedef struct {
  onewire_rom_t  rom;           /**< 64-bit ROM ID                   */
  float          temperature;   /**< Last read temperature in C      */
  ds18b20_status_t last_status; /**< Status of last operation        */
  bool           connected;     /**< true if sensor was discovered   */
} ds18b20_sensor_t;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * @brief Initialize DS18B20 driver and discover sensors on the bus.
 *
 * Scans the 1-Wire bus for DS18B20 devices and populates the
 * sensor array. Sets all sensors to 12-bit resolution.
 *
 * @param bus           Pointer to 1-Wire bus configuration.
 * @param sensors       Array to store discovered sensor handles.
 * @param max_sensors   Maximum number of sensors to discover.
 * @return Number of DS18B20 sensors found.
 */
uint8_t ds18b20_init(const onewire_bus_t *bus,
                     ds18b20_sensor_t *sensors,
                     uint8_t max_sensors);

/**
 * @brief Start temperature conversion on a specific sensor.
 *
 * Initiates a temperature measurement. The conversion takes up to
 * 750 ms at 12-bit resolution. Use ds18b20_read_temperature() after
 * the conversion completes.
 *
 * @param bus     Pointer to 1-Wire bus configuration.
 * @param sensor  Pointer to the target sensor handle.
 * @return DS18B20_OK on success.
 */
ds18b20_status_t ds18b20_start_conversion(const onewire_bus_t *bus,
                                          ds18b20_sensor_t *sensor);

/**
 * @brief Start conversion on ALL sensors simultaneously (Skip ROM).
 *
 * More efficient than converting sensors one at a time.
 *
 * @param bus  Pointer to 1-Wire bus configuration.
 * @return DS18B20_OK on success.
 */
ds18b20_status_t ds18b20_start_conversion_all(const onewire_bus_t *bus);

/**
 * @brief Read temperature from a specific sensor's scratchpad.
 *
 * Reads the 9-byte scratchpad and validates CRC8. On success,
 * updates sensor->temperature with the result in degrees Celsius.
 *
 * @param bus     Pointer to 1-Wire bus configuration.
 * @param sensor  Pointer to the target sensor handle.
 * @return DS18B20_OK on success, error code otherwise.
 */
ds18b20_status_t ds18b20_read_temperature(const onewire_bus_t *bus,
                                          ds18b20_sensor_t *sensor);

/**
 * @brief Set the measurement resolution of a sensor.
 *
 * @param bus         Pointer to 1-Wire bus configuration.
 * @param sensor      Pointer to the target sensor handle.
 * @param resolution  Desired resolution (9-12 bit).
 * @return DS18B20_OK on success.
 */
ds18b20_status_t ds18b20_set_resolution(const onewire_bus_t *bus,
                                        ds18b20_sensor_t *sensor,
                                        ds18b20_resolution_t resolution);

/**
 * @brief Check if a temperature conversion is complete.
 *
 * In parasite power mode, reads the bus to check conversion status.
 *
 * @param bus  Pointer to 1-Wire bus configuration.
 * @return true if conversion is complete, false if still in progress.
 */
bool ds18b20_is_conversion_done(const onewire_bus_t *bus);

/**
 * @brief Get the conversion time in milliseconds for a resolution.
 *
 * @param resolution  The configured resolution.
 * @return Conversion time in milliseconds.
 */
uint16_t ds18b20_get_conversion_time_ms(ds18b20_resolution_t resolution);

#ifdef __cplusplus
}
#endif

#endif /* DS18B20_H */
