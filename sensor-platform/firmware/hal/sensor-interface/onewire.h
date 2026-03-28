/***************************************************************************//**
 * @file onewire.h
 * @brief 1-Wire bit-bang protocol driver for EFR32MG24
 *
 * Provides low-level 1-Wire communication via GPIO bit-banging.
 * Timing-critical sections use interrupt masking for accuracy.
 *
 * @note Requires 4.7k pull-up resistor on the 1-Wire data line.
 * @note All timing based on DS18B20 datasheet specifications.
 *
 * @copyright 2026 Nowak Automatisierung
 * @license MIT
 ******************************************************************************/

#ifndef ONEWIRE_H
#define ONEWIRE_H

#include <stdint.h>
#include <stdbool.h>
#include "em_gpio.h"

#ifdef __cplusplus
extern "C" {
#endif

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/** @brief 1-Wire bus configuration */
typedef struct {
  GPIO_Port_TypeDef port;   /**< GPIO port for 1-Wire data line */
  uint8_t           pin;    /**< GPIO pin for 1-Wire data line  */
} onewire_bus_t;

// ---------------------------------------------------------------------------
// Status codes
// ---------------------------------------------------------------------------

typedef enum {
  ONEWIRE_OK = 0,           /**< Operation successful               */
  ONEWIRE_ERR_NO_PRESENCE,  /**< No device responded to reset pulse  */
  ONEWIRE_ERR_SHORT,        /**< Bus shorted to GND                  */
  ONEWIRE_ERR_TIMEOUT,      /**< Operation timed out                 */
} onewire_status_t;

// ---------------------------------------------------------------------------
// ROM commands (common to all 1-Wire devices)
// ---------------------------------------------------------------------------

#define ONEWIRE_CMD_SEARCH_ROM   0xF0
#define ONEWIRE_CMD_READ_ROM     0x33
#define ONEWIRE_CMD_MATCH_ROM    0x55
#define ONEWIRE_CMD_SKIP_ROM     0xCC
#define ONEWIRE_CMD_ALARM_SEARCH 0xEC

/** @brief 1-Wire ROM ID (8 bytes: family + 48-bit serial + CRC8) */
typedef struct {
  uint8_t bytes[8];
} onewire_rom_t;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * @brief Initialize the 1-Wire bus GPIO.
 * @param bus  Pointer to bus configuration (port/pin).
 */
void onewire_init(const onewire_bus_t *bus);

/**
 * @brief Send a reset pulse and detect device presence.
 * @param bus  Pointer to bus configuration.
 * @return ONEWIRE_OK if at least one device responded.
 */
onewire_status_t onewire_reset(const onewire_bus_t *bus);

/**
 * @brief Write a single byte to the 1-Wire bus (LSB first).
 * @param bus   Pointer to bus configuration.
 * @param data  Byte to transmit.
 */
void onewire_write_byte(const onewire_bus_t *bus, uint8_t data);

/**
 * @brief Read a single byte from the 1-Wire bus (LSB first).
 * @param bus  Pointer to bus configuration.
 * @return The byte read from the bus.
 */
uint8_t onewire_read_byte(const onewire_bus_t *bus);

/**
 * @brief Write a single bit to the 1-Wire bus.
 * @param bus  Pointer to bus configuration.
 * @param bit  Bit value (0 or 1).
 */
void onewire_write_bit(const onewire_bus_t *bus, uint8_t bit);

/**
 * @brief Read a single bit from the 1-Wire bus.
 * @param bus  Pointer to bus configuration.
 * @return Bit value (0 or 1).
 */
uint8_t onewire_read_bit(const onewire_bus_t *bus);

/**
 * @brief Search for all devices on the 1-Wire bus.
 *
 * Uses the standard ROM search algorithm. Call repeatedly until
 * it returns 0 to enumerate all devices.
 *
 * @param bus          Pointer to bus configuration.
 * @param rom_list     Array to store discovered ROM IDs.
 * @param max_devices  Maximum number of devices to discover.
 * @return Number of devices found (0 if search complete or error).
 */
uint8_t onewire_search(const onewire_bus_t *bus,
                       onewire_rom_t *rom_list,
                       uint8_t max_devices);

/**
 * @brief Select a specific device by ROM ID (Match ROM).
 * @param bus  Pointer to bus configuration.
 * @param rom  Pointer to the ROM ID of the target device.
 * @return ONEWIRE_OK on success.
 */
onewire_status_t onewire_select(const onewire_bus_t *bus,
                                const onewire_rom_t *rom);

/**
 * @brief Compute Dallas/Maxim CRC8 over a data buffer.
 * @param data  Pointer to data buffer.
 * @param len   Number of bytes.
 * @return CRC8 value (0x00 if data+CRC is valid).
 */
uint8_t onewire_crc8(const uint8_t *data, uint8_t len);

#ifdef __cplusplus
}
#endif

#endif /* ONEWIRE_H */
