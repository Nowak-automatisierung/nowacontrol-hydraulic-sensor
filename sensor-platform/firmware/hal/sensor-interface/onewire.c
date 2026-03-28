/***************************************************************************//**
 * @file onewire.c
 * @brief 1-Wire bit-bang protocol driver for EFR32MG24
 *
 * Implements the 1-Wire protocol using GPIO bit-banging with
 * microsecond-precision timing. Interrupt masking ensures reliable
 * timing on the EFR32MG24 Cortex-M33 core.
 *
 * @copyright 2026 Nowak Automatisierung
 * @license MIT
 ******************************************************************************/

#include "onewire.h"
#include "em_cmu.h"
#include "sl_udelay.h"
#include "em_core.h"

// ---------------------------------------------------------------------------
// Internal helpers: GPIO drive modes
// ---------------------------------------------------------------------------

/** @brief Drive the 1-Wire line LOW (open-drain output). */
static inline void ow_drive_low(const onewire_bus_t *bus)
{
  GPIO_PinModeSet(bus->port, bus->pin, gpioModeWiredAnd, 0);
  GPIO_PinOutClear(bus->port, bus->pin);
}

/** @brief Release the 1-Wire line (input with pull-up via external resistor). */
static inline void ow_release(const onewire_bus_t *bus)
{
  GPIO_PinModeSet(bus->port, bus->pin, gpioModeInput, 0);
}

/** @brief Read the current state of the 1-Wire line. */
static inline uint8_t ow_read(const onewire_bus_t *bus)
{
  return (uint8_t)GPIO_PinInGet(bus->port, bus->pin);
}

// ---------------------------------------------------------------------------
// 1-Wire timing constants (microseconds)
// Derived from DS18B20 datasheet, Table 2
// ---------------------------------------------------------------------------

#define OW_TIMING_RESET_PULSE_US     480
#define OW_TIMING_PRESENCE_WAIT_US    70
#define OW_TIMING_PRESENCE_WINDOW_US 410
#define OW_TIMING_WRITE0_LOW_US       60
#define OW_TIMING_WRITE0_RELEASE_US    5
#define OW_TIMING_WRITE1_LOW_US        5
#define OW_TIMING_WRITE1_RELEASE_US   55
#define OW_TIMING_READ_SETUP_US        3
#define OW_TIMING_READ_SAMPLE_US      10
#define OW_TIMING_READ_RELEASE_US     50
#define OW_TIMING_SLOT_US             65

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

void onewire_init(const onewire_bus_t *bus)
{
  /* Enable GPIO clock */
  CMU_ClockEnable(cmuClock_GPIO, true);

  /* Configure pin as input (idle = high via external pull-up) */
  GPIO_PinModeSet(bus->port, bus->pin, gpioModeInput, 0);
}

onewire_status_t onewire_reset(const onewire_bus_t *bus)
{
  uint8_t presence;

  CORE_DECLARE_IRQ_STATE;
  CORE_ENTER_ATOMIC();

  /* Drive bus low for reset pulse */
  ow_drive_low(bus);
  sl_udelay_wait(OW_TIMING_RESET_PULSE_US);

  /* Release bus and wait for presence response */
  ow_release(bus);
  sl_udelay_wait(OW_TIMING_PRESENCE_WAIT_US);

  /* Sample presence pulse (device pulls low if present) */
  presence = ow_read(bus);

  CORE_EXIT_ATOMIC();

  /* Wait for remainder of reset time slot */
  sl_udelay_wait(OW_TIMING_PRESENCE_WINDOW_US);

  if (presence == 0) {
    return ONEWIRE_OK; /* Device detected */
  }
  return ONEWIRE_ERR_NO_PRESENCE;
}

void onewire_write_bit(const onewire_bus_t *bus, uint8_t bit)
{
  CORE_DECLARE_IRQ_STATE;
  CORE_ENTER_ATOMIC();

  if (bit & 0x01) {
    /* Write 1: short low pulse */
    ow_drive_low(bus);
    sl_udelay_wait(OW_TIMING_WRITE1_LOW_US);
    ow_release(bus);
    sl_udelay_wait(OW_TIMING_WRITE1_RELEASE_US);
  } else {
    /* Write 0: long low pulse */
    ow_drive_low(bus);
    sl_udelay_wait(OW_TIMING_WRITE0_LOW_US);
    ow_release(bus);
    sl_udelay_wait(OW_TIMING_WRITE0_RELEASE_US);
  }

  CORE_EXIT_ATOMIC();
}

uint8_t onewire_read_bit(const onewire_bus_t *bus)
{
  uint8_t bit;

  CORE_DECLARE_IRQ_STATE;
  CORE_ENTER_ATOMIC();

  /* Initiate read: short low pulse */
  ow_drive_low(bus);
  sl_udelay_wait(OW_TIMING_READ_SETUP_US);
  ow_release(bus);

  /* Wait then sample */
  sl_udelay_wait(OW_TIMING_READ_SAMPLE_US);
  bit = ow_read(bus);

  /* Wait for remainder of time slot */
  sl_udelay_wait(OW_TIMING_READ_RELEASE_US);

  CORE_EXIT_ATOMIC();

  return bit;
}

void onewire_write_byte(const onewire_bus_t *bus, uint8_t data)
{
  for (uint8_t i = 0; i < 8; i++) {
    onewire_write_bit(bus, data & 0x01);
    data >>= 1;
  }
}

uint8_t onewire_read_byte(const onewire_bus_t *bus)
{
  uint8_t data = 0;
  for (uint8_t i = 0; i < 8; i++) {
    data >>= 1;
    if (onewire_read_bit(bus)) {
      data |= 0x80;
    }
  }
  return data;
}

// ---------------------------------------------------------------------------
// CRC8 (Dallas/Maxim polynomial: x^8 + x^5 + x^4 + 1 = 0x31)
// ---------------------------------------------------------------------------

uint8_t onewire_crc8(const uint8_t *data, uint8_t len)
{
  uint8_t crc = 0x00;
  for (uint8_t i = 0; i < len; i++) {
    uint8_t byte = data[i];
    for (uint8_t bit = 0; bit < 8; bit++) {
      uint8_t mix = (crc ^ byte) & 0x01;
      crc >>= 1;
      if (mix) {
        crc ^= 0x8C; /* Reflected polynomial */
      }
      byte >>= 1;
    }
  }
  return crc;
}

// ---------------------------------------------------------------------------
// ROM Search Algorithm (Maxim AN187)
// ---------------------------------------------------------------------------

/** @brief Internal state for ROM search */
static struct {
  uint8_t last_discrepancy;
  uint8_t last_device_flag;
  onewire_rom_t rom;
} search_state;

uint8_t onewire_search(const onewire_bus_t *bus,
                       onewire_rom_t *rom_list,
                       uint8_t max_devices)
{
  uint8_t device_count = 0;

  /* Reset search state */
  search_state.last_discrepancy = 0;
  search_state.last_device_flag = 0;
  for (uint8_t i = 0; i < 8; i++) {
    search_state.rom.bytes[i] = 0;
  }

  while (device_count < max_devices) {
    uint8_t id_bit_number = 1;
    uint8_t last_zero = 0;
    uint8_t rom_byte_number = 0;
    uint8_t rom_byte_mask = 1;
    uint8_t search_direction;
    uint8_t id_bit, cmp_id_bit;

    /* Issue reset */
    if (onewire_reset(bus) != ONEWIRE_OK) {
      /* No devices on bus */
      break;
    }

    /* Issue search ROM command */
    onewire_write_byte(bus, ONEWIRE_CMD_SEARCH_ROM);

    do {
      /* Read bit and complement */
      id_bit = onewire_read_bit(bus);
      cmp_id_bit = onewire_read_bit(bus);

      if (id_bit == 1 && cmp_id_bit == 1) {
        /* No devices participating - abort */
        break;
      }

      if (id_bit != cmp_id_bit) {
        /* All devices have same bit - no discrepancy */
        search_direction = id_bit;
      } else {
        /* Discrepancy: both 0 and 1 exist */
        if (id_bit_number == search_state.last_discrepancy) {
          search_direction = 1;
        } else if (id_bit_number > search_state.last_discrepancy) {
          search_direction = 0;
        } else {
          search_direction = (search_state.rom.bytes[rom_byte_number]
                              & rom_byte_mask) ? 1 : 0;
        }
        if (search_direction == 0) {
          last_zero = id_bit_number;
        }
      }

      /* Set or clear bit in ROM */
      if (search_direction == 1) {
        search_state.rom.bytes[rom_byte_number] |= rom_byte_mask;
      } else {
        search_state.rom.bytes[rom_byte_number] &= ~rom_byte_mask;
      }

      /* Write search direction bit */
      onewire_write_bit(bus, search_direction);

      /* Advance to next bit */
      id_bit_number++;
      rom_byte_mask <<= 1;
      if (rom_byte_mask == 0) {
        rom_byte_number++;
        rom_byte_mask = 1;
      }

    } while (rom_byte_number < 8);

    if (id_bit_number > 64) {
      /* Verify CRC */
      if (onewire_crc8(search_state.rom.bytes, 8) == 0) {
        /* Valid ROM found - copy to output */
        for (uint8_t i = 0; i < 8; i++) {
          rom_list[device_count].bytes[i] = search_state.rom.bytes[i];
        }
        device_count++;
      }
    }

    /* Update search state */
    search_state.last_discrepancy = last_zero;
    if (search_state.last_discrepancy == 0) {
      /* All devices found */
      break;
    }
  }

  return device_count;
}

onewire_status_t onewire_select(const onewire_bus_t *bus,
                                const onewire_rom_t *rom)
{
  onewire_status_t status = onewire_reset(bus);
  if (status != ONEWIRE_OK) {
    return status;
  }

  onewire_write_byte(bus, ONEWIRE_CMD_MATCH_ROM);
  for (uint8_t i = 0; i < 8; i++) {
    onewire_write_byte(bus, rom->bytes[i]);
  }

  return ONEWIRE_OK;
}
