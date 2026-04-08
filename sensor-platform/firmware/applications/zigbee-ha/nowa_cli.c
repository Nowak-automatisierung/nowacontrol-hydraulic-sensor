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
#include "sensor_hal.h"
#include "app/framework/include/af.h"   /* sl_zigbee_app_debug_println */

// ---------------------------------------------------------------------------
// Command handlers
// ---------------------------------------------------------------------------

static void nowa_config_show_cmd(sl_cli_command_arg_t *args)
{
  (void)args;
  const nowa_config_t *cfg = nowa_config_get();
  onewire_rom_t rom0;
  onewire_rom_t rom1;
  bool rom0_valid = nowa_config_get_sensor_rom(0, &rom0);
  bool rom1_valid = nowa_config_get_sensor_rom(1, &rom1);
  sl_zigbee_app_debug_println(
    "NowaConfig:"
    "\r\n  version          : %u"
    "\r\n  power_source     : %u  (0=battery, 1=mains)"
    "\r\n  pending_apply    : %u"
    "\r\n  meas_interval_ms : %lu"
    "\r\n  poll_interval_ms : %lu"
    "\r\n  vorlauf_offset   : %d cc"
    "\r\n  ruecklauf_offset : %d cc",
    (unsigned)cfg->version,
    (unsigned)cfg->power_source,
    (unsigned)cfg->pending_apply,
    (unsigned long)cfg->measurement_interval_ms,
    (unsigned long)cfg->poll_interval_ms,
    (int)cfg->vorlauf_offset_cc,
    (int)cfg->ruecklauf_offset_cc);

  if (rom0_valid) {
    sl_zigbee_app_debug_println(
      "  vorlauf_rom      : %02X-%02X-%02X-%02X-%02X-%02X-%02X-%02X",
      rom0.bytes[0], rom0.bytes[1], rom0.bytes[2], rom0.bytes[3],
      rom0.bytes[4], rom0.bytes[5], rom0.bytes[6], rom0.bytes[7]);
  } else {
    sl_zigbee_app_debug_println("  vorlauf_rom      : <unset>");
  }

  if (rom1_valid) {
    sl_zigbee_app_debug_println(
      "  ruecklauf_rom    : %02X-%02X-%02X-%02X-%02X-%02X-%02X-%02X",
      rom1.bytes[0], rom1.bytes[1], rom1.bytes[2], rom1.bytes[3],
      rom1.bytes[4], rom1.bytes[5], rom1.bytes[6], rom1.bytes[7]);
  } else {
    sl_zigbee_app_debug_println("  ruecklauf_rom    : <unset>");
  }
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

static void nowa_config_set_offset_cmd(sl_cli_command_arg_t *args)
{
  uint8_t idx = sl_cli_get_argument_uint8(args, 0);
  int32_t offset_cc = (int32_t)sl_cli_get_argument_int32(args, 1);
  sl_status_t st = nowa_config_set_sensor_offset_cc(idx, (int16_t)offset_cc);
  sl_zigbee_app_debug_println("set-offset sensor=%u offset=%ldcc -> 0x%04X",
                              (unsigned)idx,
                              (long)offset_cc,
                              (unsigned)st);
}

static void nowa_config_reset_cmd(sl_cli_command_arg_t *args)
{
  (void)args;
  nowa_config_reset_defaults();
  sl_zigbee_app_debug_println("NowaConfig: factory reset complete");
}

static void nowa_config_clear_roms_cmd(sl_cli_command_arg_t *args)
{
  (void)args;
  nowa_config_clear_sensor_roms();
  sl_zigbee_app_debug_println("NowaConfig: cleared stored sensor ROM mapping");
}

static void nowa_factory_reset_cmd(sl_cli_command_arg_t *args)
{
  (void)args;

  nowa_config_reset_defaults();
  nowa_config_clear_sensor_roms();

  sl_status_t st = sl_zigbee_leave_network(SL_ZIGBEE_LEAVE_NWK_WITH_NO_OPTION);
  sl_zigbee_app_debug_println(
    "Factory reset: defaults restored, sensor ROMs cleared, leave network -> 0x%04X",
    (unsigned)st);
}

static void nowa_sensor_show_cmd(sl_cli_command_arg_t *args)
{
  (void)args;
  const sensor_reading_t *r = sensor_hal_get_reading();
  uint8_t count = sensor_hal_get_sensor_count();

  sl_zigbee_app_debug_println(
    "NowaSensor:"
    "\r\n  found            : %u"
    "\r\n  reads            : %u"
    "\r\n  errors           : %u"
    "\r\n  vorlauf_valid    : %u"
    "\r\n  ruecklauf_valid  : %u"
    "\r\n  vorlauf_temp     : %d.%02d"
    "\r\n  ruecklauf_temp   : %d.%02d"
    "\r\n  delta_t          : %d.%02d",
    (unsigned)count,
    (unsigned)r->read_count,
    (unsigned)r->error_count,
    r->vorlauf_valid ? 1u : 0u,
    r->ruecklauf_valid ? 1u : 0u,
    (int)r->vorlauf_temp, (int)(r->vorlauf_temp * 100.0f) % 100,
    (int)r->ruecklauf_temp, (int)(r->ruecklauf_temp * 100.0f) % 100,
    (int)r->delta_t, (int)(r->delta_t * 100.0f) % 100);

  for (uint8_t i = 0; i < count; i++) {
    const ds18b20_sensor_t *sensor = sensor_hal_get_sensor(i);
    if (sensor == NULL) {
      continue;
    }
    sl_zigbee_app_debug_println(
      "  sensor[%u]       : ROM=%02X-%02X-%02X-%02X-%02X-%02X-%02X-%02X status=%d connected=%d temp=%d.%02d",
      (unsigned)i,
      sensor->rom.bytes[0], sensor->rom.bytes[1], sensor->rom.bytes[2], sensor->rom.bytes[3],
      sensor->rom.bytes[4], sensor->rom.bytes[5], sensor->rom.bytes[6], sensor->rom.bytes[7],
      (int)sensor->last_status,
      sensor->connected ? 1 : 0,
      (int)sensor->temperature, (int)(sensor->temperature * 100.0f) % 100);
  }
}

static void nowa_sensor_measure_cmd(sl_cli_command_arg_t *args)
{
  (void)args;
  sensor_hal_status_t st = sensor_hal_measure();
  sl_zigbee_app_debug_println("NowaSensor: measure -> %d", (int)st);
  nowa_sensor_show_cmd(args);
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

static const sl_cli_command_info_t nowa_config_set_offset_info =
  SL_CLI_COMMAND(nowa_config_set_offset_cmd,
                 "Set sensor offset in 0.01 C (sensor 0=Vorlauf, 1=Ruecklauf)",
                 "<sensor_index> <offset_cc>",
                 {SL_CLI_ARG_UINT8, SL_CLI_ARG_INT32, SL_CLI_ARG_END});

static const sl_cli_command_info_t nowa_config_reset_info =
  SL_CLI_COMMAND(nowa_config_reset_cmd,
                 "Reset configuration to factory defaults",
                 "",
                 {SL_CLI_ARG_END});

static const sl_cli_command_info_t nowa_config_clear_roms_info =
  SL_CLI_COMMAND(nowa_config_clear_roms_cmd,
                 "Clear stored DS18B20 ROM mapping",
                 "",
                 {SL_CLI_ARG_END});

static const sl_cli_command_info_t nowa_factory_reset_info =
  SL_CLI_COMMAND(nowa_factory_reset_cmd,
                 "Factory reset: clear config, clear sensor ROM mapping, leave Zigbee network",
                 "",
                 {SL_CLI_ARG_END});

static const sl_cli_command_info_t nowa_sensor_show_info =
  SL_CLI_COMMAND(nowa_sensor_show_cmd,
                 "Show discovered DS18B20 sensors, ROMs, status and last values",
                 "",
                 {SL_CLI_ARG_END});

static const sl_cli_command_info_t nowa_sensor_measure_info =
  SL_CLI_COMMAND(nowa_sensor_measure_cmd,
                 "Trigger one blocking DS18B20 measurement and print diagnostics",
                 "",
                 {SL_CLI_ARG_END});

static const sl_cli_command_entry_t nowa_config_cmd_table[] = {
  { "show",         &nowa_config_show_info,         false },
  { "set-interval", &nowa_config_set_interval_info, false },
  { "set-pwr",      &nowa_config_set_pwr_info,      false },
  { "set-offset",   &nowa_config_set_offset_info,   false },
  { "clear-roms",   &nowa_config_clear_roms_info,   false },
  { "factory-reset",&nowa_factory_reset_info,       false },
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

static const sl_cli_command_entry_t nowa_sensor_cmd_table[] = {
  { "show",    &nowa_sensor_show_info,    false },
  { "measure", &nowa_sensor_measure_info, false },
  { NULL, NULL, false }
};

static sl_cli_command_group_t nowa_sensor_group = {
  { NULL },
  false,
  nowa_sensor_cmd_table
};

static const sl_cli_command_info_t nowa_sensor_group_info =
  SL_CLI_COMMAND_GROUP(&nowa_sensor_group, "NowaControl DS18B20 diagnostics");

// ---------------------------------------------------------------------------
// Top-level "nowa" command group
// ---------------------------------------------------------------------------

static const sl_cli_command_entry_t nowa_cmd_table[] = {
  { "config", &nowa_config_group_info, false },
  { "sensor", &nowa_sensor_group_info, false },
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
