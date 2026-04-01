/***************************************************************************//**
 * @file nowa_bat.h
 * @brief NowaControl battery voltage measurement via IADC (XIAO MG24 Sense)
 *
 * The battery voltage divider on the XIAO MG24 Sense board connects the
 * battery positive terminal through two equal 1 MΩ resistors to GND, with
 * the mid-point routed to PD04 (D10).  The ADC therefore sees V_bat / 2.
 *
 *   PD04 voltage range  : 1.5 V (0 %) … 2.1 V (100 %)  (3.0 – 4.2 V bat)
 *   IADC reference      : AVDD ≈ 3.3 V
 *   IADC resolution     : 12-bit
 *
 * Result encoding for ZCL Power Configuration Cluster:
 *   battery_voltage              – units of 100 mV  (0x21 = 33 → 3.3 V)
 *   battery_percentage_remaining – units of 0.5 %   (200 = 100 %)
 *
 * @copyright 2026 Nowak Automatisierung
 ******************************************************************************/

#ifndef NOWA_BAT_H
#define NOWA_BAT_H

#include <stdint.h>
#include "sl_status.h"

#ifdef __cplusplus
extern "C" {
#endif

// ---------------------------------------------------------------------------
// Battery chemistry limits (Li-Ion / Li-Po)
// ---------------------------------------------------------------------------
#define NOWA_BAT_MV_FULL    4200u   /**< Full charge voltage [mV]           */
#define NOWA_BAT_MV_EMPTY   3000u   /**< Minimum operational voltage [mV]   */

// ---------------------------------------------------------------------------
// Battery reading structure
// ---------------------------------------------------------------------------
typedef struct {
  uint16_t voltage_mv;           /**< Battery voltage in mV                 */
  uint8_t  zcl_voltage;          /**< ZCL value: units of 100 mV            */
  uint8_t  zcl_percentage;       /**< ZCL value: units of 0.5 %, 200 = 100% */
} nowa_bat_reading_t;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * @brief Initialise the IADC for battery voltage measurement.
 *        Must be called once after sl_gpio_init().
 * @return SL_STATUS_OK on success.
 */
sl_status_t nowa_bat_init(void);

/**
 * @brief Perform a single ADC conversion and compute battery metrics.
 *
 * Blocks for < 1 ms (IADC one-shot conversion).
 *
 * @param[out] reading  Populated with voltage_mv, zcl_voltage, zcl_percentage.
 * @return SL_STATUS_OK on success, SL_STATUS_FAIL on ADC timeout.
 */
sl_status_t nowa_bat_measure(nowa_bat_reading_t *reading);

#ifdef __cplusplus
}
#endif

#endif /* NOWA_BAT_H */
