/***************************************************************************//**
 * @file nowa_config.h
 * @brief NowaControl persistent application configuration (NVM3-backed)
 *
 * Stores and restores runtime-tunable parameters across power cycles.
 * On first boot the defaults are written to NVM3.  After modifying a
 * field, call nowa_config_save() to persist it immediately, or set the
 * pending_apply flag and call nowa_config_save() — the change will be
 * visible to the application after the next nowa_config_init() call
 * (i.e., after a reboot).
 *
 * NVM3 key: NOWA_NVM3_KEY_CONFIG  (0x00001 in the default user region)
 *
 * Schema migration:
 *   Increment NOWA_CONFIG_VERSION to force factory-reset of the block
 *   when the struct layout changes in an incompatible way.
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

// Magic + version: changing NOWA_CONFIG_VERSION forces a factory reset
// on the next boot so that old incompatible structs are overwritten.
#define NOWA_CONFIG_MAGIC           (0xC0F10002u)  /**< Schema version 2      */
#define NOWA_CONFIG_VERSION         (2u)

// ---------------------------------------------------------------------------
// Limits for runtime-tunable parameters
// ---------------------------------------------------------------------------
#define NOWA_MEAS_INTERVAL_MIN_MS   (5000u)         /**< 5 s minimum           */
#define NOWA_MEAS_INTERVAL_MAX_MS   (3600000u)      /**< 1 h maximum           */

// ---------------------------------------------------------------------------
// Default parameter values
// ---------------------------------------------------------------------------
#define NOWA_DEFAULT_MEAS_INTERVAL_MS   (60000u)    /**< 60-second cycle       */
#define NOWA_DEFAULT_POLL_INTERVAL_MS   (0u)        /**< Disabled (router)     */

// ---------------------------------------------------------------------------
// Power-source type
// ---------------------------------------------------------------------------
typedef enum {
  NOWA_POWER_SOURCE_BATTERY = 0,   /**< Li-Ion / Li-Po battery               */
  NOWA_POWER_SOURCE_MAINS   = 1,   /**< External DC supply (mains-powered)   */
} nowa_power_source_t;

// ---------------------------------------------------------------------------
// Persistent configuration block (48 bytes, version 2)
// ---------------------------------------------------------------------------
typedef struct {
  /* --- Header (8 bytes) --------------------------------------------------- */
  uint32_t magic;                   /**< NOWA_CONFIG_MAGIC when valid          */
  uint8_t  version;                 /**< NOWA_CONFIG_VERSION                   */
  uint8_t  power_source;            /**< nowa_power_source_t                   */
  uint8_t  pending_apply;           /**< Non-zero: reboot needed for changes   */
  uint8_t  reserved;                /**< Padding                               */

  /* --- Runtime parameters (8 bytes) --------------------------------------- */
  uint32_t measurement_interval_ms; /**< Temperature sampling period [ms]      */
  uint32_t poll_interval_ms;        /**< Zigbee end-device poll rate [ms]      */
                                    /**< 0 = router mode (no polling)          */

  /* --- Future expansion (32 bytes) --------------------------------------- */
  uint8_t  reserved2[32];           /**< Reserved, zero on creation            */
} nowa_config_t;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * @brief Load config from NVM3 (or write defaults on first boot / schema change).
 * @return SL_STATUS_OK on success.
 */
sl_status_t nowa_config_init(void);

/**
 * @brief Return a read-only pointer to the in-RAM config snapshot.
 * @return Pointer to the current configuration (never NULL).
 */
const nowa_config_t *nowa_config_get(void);

/**
 * @brief Set the measurement interval and persist to NVM3 immediately.
 *
 * The new value takes effect for the next measurement cycle without a reboot.
 * Clamps to [NOWA_MEAS_INTERVAL_MIN_MS, NOWA_MEAS_INTERVAL_MAX_MS].
 *
 * @param  interval_ms  Desired interval in milliseconds.
 * @return SL_STATUS_OK on success.
 */
sl_status_t nowa_config_set_meas_interval(uint32_t interval_ms);

/**
 * @brief Set the power source type and persist to NVM3.
 *
 * Sets pending_apply = 1 because the power source affects deep-sleep
 * mode selection, which is determined once at boot.
 *
 * @param  src  NOWA_POWER_SOURCE_BATTERY or NOWA_POWER_SOURCE_MAINS.
 * @return SL_STATUS_OK on success.
 */
sl_status_t nowa_config_set_power_source(nowa_power_source_t src);

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
