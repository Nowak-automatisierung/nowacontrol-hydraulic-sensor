/***************************************************************************//**
 * @file nowa_config.c
 * @brief NowaControl persistent application configuration (NVM3-backed)
 *
 * @copyright 2026 Nowak Automatisierung
 ******************************************************************************/

#include "nowa_config.h"
#include "nvm3_default.h"
#include "app/framework/include/af.h"   /* sl_zigbee_app_debug_println */
#include <string.h>

// ---------------------------------------------------------------------------
// Internal state
// ---------------------------------------------------------------------------

static nowa_config_t s_config;

// ---------------------------------------------------------------------------
// Private helpers
// ---------------------------------------------------------------------------

static void set_defaults(void)
{
  memset(&s_config, 0, sizeof(s_config));
  s_config.magic                   = NOWA_CONFIG_MAGIC;
  s_config.version                 = NOWA_CONFIG_VERSION;
  s_config.power_source            = (uint8_t)NOWA_POWER_SOURCE_BATTERY;
  s_config.pending_apply           = 0u;
  s_config.measurement_interval_ms = NOWA_DEFAULT_MEAS_INTERVAL_MS;
  s_config.poll_interval_ms        = NOWA_DEFAULT_POLL_INTERVAL_MS;
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

sl_status_t nowa_config_init(void)
{
  sl_status_t status = nvm3_readData(nvm3_defaultHandle,
                                     NOWA_NVM3_KEY_CONFIG,
                                     &s_config,
                                     sizeof(s_config));

  bool valid = (status == SL_STATUS_OK)
               && (s_config.magic   == NOWA_CONFIG_MAGIC)
               && (s_config.version == NOWA_CONFIG_VERSION);

  if (!valid) {
    sl_zigbee_app_debug_println(
      "NowaConfig: first boot or schema change – writing defaults");
    set_defaults();
    status = nowa_config_save();
  } else {
    if (s_config.pending_apply) {
      sl_zigbee_app_debug_println(
        "NowaConfig: pending_apply cleared (settings applied at boot)");
      s_config.pending_apply = 0u;
      (void)nowa_config_save();
    }
    sl_zigbee_app_debug_println(
      "NowaConfig: loaded (interval=%lu ms, pwr=%d)",
      (unsigned long)s_config.measurement_interval_ms,
      (int)s_config.power_source);
  }

  return status;
}

const nowa_config_t *nowa_config_get(void)
{
  return &s_config;
}

sl_status_t nowa_config_set_meas_interval(uint32_t interval_ms)
{
  /* Clamp to valid range */
  if (interval_ms < NOWA_MEAS_INTERVAL_MIN_MS) {
    interval_ms = NOWA_MEAS_INTERVAL_MIN_MS;
  } else if (interval_ms > NOWA_MEAS_INTERVAL_MAX_MS) {
    interval_ms = NOWA_MEAS_INTERVAL_MAX_MS;
  }

  s_config.measurement_interval_ms = interval_ms;
  sl_zigbee_app_debug_println(
    "NowaConfig: meas_interval set to %lu ms", (unsigned long)interval_ms);
  return nowa_config_save();
}

sl_status_t nowa_config_set_power_source(nowa_power_source_t src)
{
  s_config.power_source  = (uint8_t)src;
  s_config.pending_apply = 1u;   /* Requires reboot to take full effect */
  sl_zigbee_app_debug_println(
    "NowaConfig: power_source set to %d (reboot required)", (int)src);
  return nowa_config_save();
}

sl_status_t nowa_config_save(void)
{
  sl_status_t status = nvm3_writeData(nvm3_defaultHandle,
                                      NOWA_NVM3_KEY_CONFIG,
                                      &s_config,
                                      sizeof(s_config));
  if (status != SL_STATUS_OK) {
    sl_zigbee_app_debug_println(
      "NowaConfig: NVM3 write failed (0x%04X)", status);
  }
  return status;
}

void nowa_config_reset_defaults(void)
{
  set_defaults();
  nowa_config_save();
  sl_zigbee_app_debug_println("NowaConfig: factory reset");
}
