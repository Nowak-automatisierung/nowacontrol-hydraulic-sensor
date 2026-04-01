/***************************************************************************//**
 * @file nowa_cli.c
 * @brief NowaControl custom CLI commands
 *
 * Registers a "nowa" CLI command group at runtime via
 * sl_cli_command_add_command_group().  All commands are visible in the
 * serial console as:
 *
 *   nowa config show
 *   nowa config set-interval <ms>
 *   nowa config set-pwr <0=battery|1=mains>
 *   nowa config reset
 *
 * @copyright 2026 Nowak Automatisierung
 ******************************************************************************/

#include "sl_cli.h"
#include "sl_cli_command.h"
#include "sl_cli_handles.h"
#include "nowa_config.h"
#include "app/framework/include/af.h"   /* sl_zigbee_app_debug_println */

// ---------------------------------------------------------------------------
// Command handlers
// ---------------------------------------------------------------------------

static void nowa_config_show_cmd(sl_cli_command_arg_t *args)
{
  (void)args;
  const nowa_config_t *cfg = nowa_config_get();
  sl_zigbee_app_debug_println(
    "NowaConfig:"
    "\r\n  version          : %u"
    "\r\n  power_source     : %u  (0=battery, 1=mains)"
    "\r\n  pending_apply    : %u"
    "\r\n  meas_interval_ms : %lu"
    "\r\n  poll_interval_ms : %lu",
    (unsigned)cfg->version,
    (unsigned)cfg->power_source,
    (unsigned)cfg->pending_apply,
    (unsigned long)cfg->measurement_interval_ms,
    (unsigned long)cfg->poll_interval_ms);
}

static void nowa_config_set_interval_cmd(sl_cli_command_arg_t *args)
{
  uint32_t ms = sl_cli_get_argument_uint32(args, 0);
  sl_status_t st = nowa_config_set_meas_interval(ms);
  sl_zigbee_app_debug_println("set-interval %lu ms → 0x%04X",
                              (unsigned long)ms, (unsigned)st);
}

static void nowa_config_set_pwr_cmd(sl_cli_command_arg_t *args)
{
  uint8_t src = sl_cli_get_argument_uint8(args, 0);
  if (src > 1u) {
    sl_zigbee_app_debug_println("Error: use 0 (battery) or 1 (mains)");
    return;
  }
  sl_status_t st = nowa_config_set_power_source((nowa_power_source_t)src);
  sl_zigbee_app_debug_println("set-pwr %u → 0x%04X (reboot to apply)",
                              (unsigned)src, (unsigned)st);
}

static void nowa_config_reset_cmd(sl_cli_command_arg_t *args)
{
  (void)args;
  nowa_config_reset_defaults();
  sl_zigbee_app_debug_println("NowaConfig: factory reset complete");
}

// ---------------------------------------------------------------------------
// Command table: "nowa config <subcommand>"
// ---------------------------------------------------------------------------

static const sl_cli_command_info_t nowa_config_show_info =
  SL_CLI_COMMAND(nowa_config_show_cmd,
                 "Show current persistent configuration",
                 "",
                 {SL_CLI_ARG_END});

static const sl_cli_command_info_t nowa_config_set_interval_info =
  SL_CLI_COMMAND(nowa_config_set_interval_cmd,
                 "Set measurement interval [ms] (5000 – 3600000)",
                 "<interval_ms>",
                 {SL_CLI_ARG_UINT32, SL_CLI_ARG_END});

static const sl_cli_command_info_t nowa_config_set_pwr_info =
  SL_CLI_COMMAND(nowa_config_set_pwr_cmd,
                 "Set power source type (0=battery, 1=mains) – reboot required",
                 "<source>",
                 {SL_CLI_ARG_UINT8, SL_CLI_ARG_END});

static const sl_cli_command_info_t nowa_config_reset_info =
  SL_CLI_COMMAND(nowa_config_reset_cmd,
                 "Reset configuration to factory defaults",
                 "",
                 {SL_CLI_ARG_END});

static const sl_cli_command_entry_t nowa_config_cmd_table[] = {
  { "show",         &nowa_config_show_info,         false },
  { "set-interval", &nowa_config_set_interval_info, false },
  { "set-pwr",      &nowa_config_set_pwr_info,      false },
  { "reset",        &nowa_config_reset_info,        false },
  { NULL, NULL, false }
};

static sl_cli_command_group_t nowa_config_group = {
  { NULL },
  false,
  nowa_config_cmd_table
};

static const sl_cli_command_info_t nowa_config_group_info =
  SL_CLI_COMMAND_GROUP(&nowa_config_group, "NowaControl persistent config");

// ---------------------------------------------------------------------------
// Top-level "nowa" command group
// ---------------------------------------------------------------------------

static const sl_cli_command_entry_t nowa_cmd_table[] = {
  { "config", &nowa_config_group_info, false },
  { NULL, NULL, false }
};

static sl_cli_command_group_t nowa_group = {
  { NULL },
  false,
  nowa_cmd_table
};

// ---------------------------------------------------------------------------
// Registration (called from sl_zigbee_af_main_init_cb)
// ---------------------------------------------------------------------------

void nowa_cli_init(void)
{
  bool ok = sl_cli_command_add_command_group(sl_cli_example_handle, &nowa_group);
  if (!ok) {
    sl_zigbee_app_debug_println("NowaCLI: failed to register command group");
  } else {
    sl_zigbee_app_debug_println("NowaCLI: 'nowa config' commands registered");
  }
}
