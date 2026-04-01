/***************************************************************************//**
 * @file nowa_cli.h
 * @brief NowaControl custom CLI commands
 * @copyright 2026 Nowak Automatisierung
 ******************************************************************************/

#ifndef NOWA_CLI_H
#define NOWA_CLI_H

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Register the "nowa" CLI command group.
 *        Call once from sl_zigbee_af_main_init_cb().
 */
void nowa_cli_init(void);

#ifdef __cplusplus
}
#endif

#endif /* NOWA_CLI_H */
