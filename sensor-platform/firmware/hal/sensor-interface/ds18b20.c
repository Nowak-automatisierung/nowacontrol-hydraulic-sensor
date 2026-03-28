/***************************************************************************//**
 * @file ds18b20.c
 * @brief DS18B20 digital temperature sensor driver implementation
 *
 * @copyright 2026 Nowak Automatisierung
 * @license MIT
 ******************************************************************************/

#include "ds18b20.h"
#include "sl_udelay.h"
#include <string.h>

// ---------------------------------------------------------------------------
// Internal: Scratchpad structure (9 bytes)
// ---------------------------------------------------------------------------
// Byte 0: Temperature LSB
// Byte 1: Temperature MSB
// Byte 2: TH register (user byte 1)
// Byte 3: TL register (user byte 2)
// Byte 4: Configuration register
// Byte 5: Reserved (0xFF)
// Byte 6: Reserved
// Byte 7: Reserved (0x10)
// Byte 8: CRC8
// ---------------------------------------------------------------------------

#define SCRATCHPAD_SIZE  9

/** @brief Power-on reset temperature value (85.0 C) */
#define DS18B20_POWER_ON_TEMP_RAW  0x0550

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

uint8_t ds18b20_init(const onewire_bus_t *bus,
                     ds18b20_sensor_t *sensors,
                     uint8_t max_sensors)
{
  onewire_rom_t rom_list[DS18B20_MAX_SENSORS];
  uint8_t found;
  uint8_t ds_count = 0;

  /* Initialize 1-Wire bus */
  onewire_init(bus);

  /* Search for all devices */
  found = onewire_search(bus, rom_list, max_sensors);

  /* Filter for DS18B20 devices (family code 0x28) */
  for (uint8_t i = 0; i < found && ds_count < max_sensors; i++) {
    if (rom_list[i].bytes[0] == DS18B20_FAMILY_CODE) {
      memcpy(&sensors[ds_count].rom, &rom_list[i], sizeof(onewire_rom_t));
      sensors[ds_count].temperature = DS18B20_INVALID_TEMP;
      sensors[ds_count].last_status = DS18B20_OK;
      sensors[ds_count].connected = true;
      ds_count++;
    }
  }

  /* Mark remaining slots as disconnected */
  for (uint8_t i = ds_count; i < max_sensors; i++) {
    memset(&sensors[i], 0, sizeof(ds18b20_sensor_t));
    sensors[i].temperature = DS18B20_INVALID_TEMP;
    sensors[i].last_status = DS18B20_ERR_NO_DEVICE;
    sensors[i].connected = false;
  }

  /* Set all discovered sensors to 12-bit resolution */
  for (uint8_t i = 0; i < ds_count; i++) {
    ds18b20_set_resolution(bus, &sensors[i], DS18B20_RESOLUTION_12BIT);
  }

  return ds_count;
}

ds18b20_status_t ds18b20_start_conversion(const onewire_bus_t *bus,
                                          ds18b20_sensor_t *sensor)
{
  if (!sensor->connected) {
    sensor->last_status = DS18B20_ERR_NO_DEVICE;
    return DS18B20_ERR_NO_DEVICE;
  }

  /* Select specific sensor by ROM ID */
  onewire_status_t ow_status = onewire_select(bus, &sensor->rom);
  if (ow_status != ONEWIRE_OK) {
    sensor->last_status = DS18B20_ERR_NO_DEVICE;
    sensor->connected = false;
    return DS18B20_ERR_NO_DEVICE;
  }

  /* Issue Convert T command */
  onewire_write_byte(bus, DS18B20_CMD_CONVERT_T);

  sensor->last_status = DS18B20_OK;
  return DS18B20_OK;
}

ds18b20_status_t ds18b20_start_conversion_all(const onewire_bus_t *bus)
{
  /* Reset + Skip ROM (address all devices) */
  onewire_status_t ow_status = onewire_reset(bus);
  if (ow_status != ONEWIRE_OK) {
    return DS18B20_ERR_NO_DEVICE;
  }

  onewire_write_byte(bus, ONEWIRE_CMD_SKIP_ROM);
  onewire_write_byte(bus, DS18B20_CMD_CONVERT_T);

  return DS18B20_OK;
}

ds18b20_status_t ds18b20_read_temperature(const onewire_bus_t *bus,
                                          ds18b20_sensor_t *sensor)
{
  uint8_t scratchpad[SCRATCHPAD_SIZE];

  if (!sensor->connected) {
    sensor->last_status = DS18B20_ERR_NO_DEVICE;
    return DS18B20_ERR_NO_DEVICE;
  }

  /* Select sensor and read scratchpad */
  onewire_status_t ow_status = onewire_select(bus, &sensor->rom);
  if (ow_status != ONEWIRE_OK) {
    sensor->last_status = DS18B20_ERR_NO_DEVICE;
    sensor->connected = false;
    return DS18B20_ERR_NO_DEVICE;
  }

  onewire_write_byte(bus, DS18B20_CMD_READ_SCRATCHPAD);

  /* Read all 9 bytes */
  for (uint8_t i = 0; i < SCRATCHPAD_SIZE; i++) {
    scratchpad[i] = onewire_read_byte(bus);
  }

  /* Validate CRC8 (byte 8 is CRC over bytes 0-7) */
  if (onewire_crc8(scratchpad, SCRATCHPAD_SIZE) != 0) {
    sensor->last_status = DS18B20_ERR_CRC;
    return DS18B20_ERR_CRC;
  }

  /* Convert raw temperature to float */
  int16_t raw = (int16_t)((scratchpad[1] << 8) | scratchpad[0]);

  /* Check for power-on reset value (85.0 C = 0x0550) */
  if (raw == DS18B20_POWER_ON_TEMP_RAW) {
    sensor->last_status = DS18B20_ERR_DISCONNECTED;
    return DS18B20_ERR_DISCONNECTED;
  }

  /* 12-bit resolution: 1 LSB = 0.0625 C */
  sensor->temperature = (float)raw * 0.0625f;
  sensor->last_status = DS18B20_OK;

  return DS18B20_OK;
}

ds18b20_status_t ds18b20_set_resolution(const onewire_bus_t *bus,
                                        ds18b20_sensor_t *sensor,
                                        ds18b20_resolution_t resolution)
{
  if (!sensor->connected) {
    return DS18B20_ERR_NO_DEVICE;
  }

  /* Select sensor */
  onewire_status_t ow_status = onewire_select(bus, &sensor->rom);
  if (ow_status != ONEWIRE_OK) {
    return DS18B20_ERR_NO_DEVICE;
  }

  /* Write scratchpad: TH=0x00, TL=0x00, Config=resolution */
  onewire_write_byte(bus, DS18B20_CMD_WRITE_SCRATCHPAD);
  onewire_write_byte(bus, 0x00);               /* TH */
  onewire_write_byte(bus, 0x00);               /* TL */
  onewire_write_byte(bus, (uint8_t)resolution); /* Config register */

  return DS18B20_OK;
}

bool ds18b20_is_conversion_done(const onewire_bus_t *bus)
{
  /* During conversion, sensor holds the bus low.
   * Conversion complete = bus reads high (1). */
  return (onewire_read_bit(bus) == 1);
}

uint16_t ds18b20_get_conversion_time_ms(ds18b20_resolution_t resolution)
{
  switch (resolution) {
    case DS18B20_RESOLUTION_9BIT:  return 94;
    case DS18B20_RESOLUTION_10BIT: return 188;
    case DS18B20_RESOLUTION_11BIT: return 375;
    case DS18B20_RESOLUTION_12BIT: return 750;
    default:                       return 750;
  }
}
