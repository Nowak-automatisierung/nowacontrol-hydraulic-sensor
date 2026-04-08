/***************************************************************************//**
 * @brief Zigbee Reporting component configuration header.
 *******************************************************************************
 * Local copy so the reporting plugin can be enabled without regenerating the
 * full SLC project. Keep values conservative for this sensor device.
 ******************************************************************************/

#ifndef NOWACONTROL_REPORTING_CONFIG_H
#define NOWACONTROL_REPORTING_CONFIG_H

// <q SL_ZIGBEE_AF_PLUGIN_REPORTING_ENABLE_EXPANDED_TABLE>
#define SL_ZIGBEE_AF_PLUGIN_REPORTING_ENABLE_EXPANDED_TABLE   0

// <o SL_ZIGBEE_AF_PLUGIN_REPORTING_TABLE_SIZE> <1-127>
#define SL_ZIGBEE_AF_PLUGIN_REPORTING_TABLE_SIZE   5

// <o SL_ZIGBEE_AF_PLUGIN_REPORTING_EXPANDED_TABLE_SIZE> <1-1024>
#define SL_ZIGBEE_AF_PLUGIN_REPORTING_EXPANDED_TABLE_SIZE   20

// <q SL_ZIGBEE_AF_PLUGIN_REPORTING_ENABLE_GROUP_BOUND_REPORTS>
#define SL_ZIGBEE_AF_PLUGIN_REPORTING_ENABLE_GROUP_BOUND_REPORTS   1

#endif
