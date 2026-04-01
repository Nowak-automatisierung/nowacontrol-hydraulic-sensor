/***************************************************************************//**
 * @file nowa_config.h
 * @brief NowaControl persistent application configuration (NVM3-backed)
 *
 * Stores and restores runtime-tunable parameters across power cycles.
 * On first boot the defaults are written to NVM3. Use nowa_config_save()
 * after any in-RAM change to persist it.
 *
 * NVM3 key: NOWA_NVM3_KEY_CONFIG  (0x00001 in the default user region)
 *
 * @copyright 2026 Nowak Automatisierung
 ******************************************************************************/

#ifndef NOWA_CONFIG_H
#define NOWA_CONFIG_H

#include <stdint.h>
#include <stdbool.h>
#include "sl_status.h"

#ifdef __cplusplus
extern "C" {
#endif

// ---------------------------------------------------------------------------
// NVM3 key (default-instance user region, 0x00001 – 0x0FFFF available)
// ---------------------------------------------------------------------------
#define NOWA_NVM3_KEY_CONFIG        (0x00001u)

// Magic word and schema version: increment NOWA_CONFIG_VERSION to force
// a factory-reset of the config block after a breaking struct change.
#define NOWA_CONFIG_MAGIC           (0xC0F10001u)  /**< 'C'onfig 'V'1       */
#define NOWA_CONFIG_VERSION         (1u)

// ---------------------------------------------------------------------------
// Default parameter values
// ---------------------------------------------------------------------------
#define NOWA_DEFAULT_MEAS_INTERVAL_MS   (60000u)   /**< 60-second cycle      */
#define NOWA_DEFAULT_POLL_INTERVAL_MS   (0u)       /**< Disabled (router)    */

// ---------------------------------------------------------------------------
// Power-source type
// ---------------------------------------------------------------------------
typedef enum {
  NOWA_POWER_SOURCE_BATTERY = 0,   /**< Li-Ion / Li-Po battery              */
  NOWA_POWER_SOURCE_MAINS   = 1,   /**< External DC supply (mains-powered)  */
} nowa_power_source_t;

// ---------------------------------------------------------------------------
// Persistent configuration block (32 bytes, NVM3-aligned)
// ---------------------------------------------------------------------------
typedef struct {
  uint32_t magic;                  /**< NOWA_CONFIG_MAGIC when valid         */
  uint8_t  version;                /**< NOWA_CONFIG_VERSION                  */
  uint8_t  power_source;           /**< nowa_power_source_t                  */
  uint8_t  reserved[2];            /**< Padding – reserved for future use    */
  uint32_t measurement_interval_ms;/**< Temperature sampling period [ms]     */
  uint32_t poll_interval_ms;       /**< Zigbee end-device poll rate [ms]     */
                                   /**< 0 = router mode (no polling)         */
  uint8_t  reserved2[16];          /**< Future expansion                     */
} nowa_config_t;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * @brief Load config from NVM3 (or write defaults on first boot).
 * @return SL_STATUS_OK on success.
 */
sl_status_t nowa_config_init(void);

/**
 * @brief Return a read-only pointer to the in-RAM config snapshot.
 * @return Pointer to the current configuration (never NULL).
 */
const nowa_config_t *nowa_config_get(void);

/**
 * @brief Persist the in-RAM config snapshot to NVM3.
 * @return SL_STATUS_OK on success.
 */
sl_status_t nowa_config_save(void);

/**
 * @brief Reset to factory defaults and persist to NVM3.
 */
void nowa_config_reset_defaults(void);

#ifdef __cplusplus
}
#endif

#endif /* NOWA_CONFIG_H */
