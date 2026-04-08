/***************************************************************************//**
 * @file nowa_bat.c
 * @brief Battery voltage measurement using IADC on EFR32MG24 (PD04)
 *
 * @copyright 2026 Nowak Automatisierung
 ******************************************************************************/

#include "nowa_bat.h"
#include "em_cmu.h"
#include "em_iadc.h"
#include "em_gpio.h"
#include "app/framework/include/af.h"  /* sl_zigbee_app_debug_println */

// ---------------------------------------------------------------------------
// Hardware constants
// ---------------------------------------------------------------------------

/** Voltage divider ratio: two equal resistors → V_adc = V_bat / 2 */
#define BAT_DIVIDER_RATIO     2u

/** AVDD reference used for IADC, in mV (nominal 3300 mV for XIAO MG24) */
#define IADC_VREF_MV          3300u

/** 12-bit ADC full-scale code */
#define IADC_FULL_SCALE       4095u

/** Conversion timeout loop count (> 1 ms at 38.4 MHz) */
#define IADC_TIMEOUT_LOOPS    40000u

// ---------------------------------------------------------------------------
// IADC init state
// ---------------------------------------------------------------------------
static bool s_bat_initialized = false;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

sl_status_t nowa_bat_init(void)
{
  /* Enable IADC0 bus clock */
  CMU_ClockEnable(cmuClock_IADC0, true);

  /* Configure PD04 as analog input (disabled output buffer) */
  GPIO_PinModeSet(gpioPortD, 4, gpioModeDisabled, 0);

  /* IADC global init: use HFSRC clock (derived from HFXO/HFRCO), no warmup */
  IADC_Init_t initIADC = IADC_INIT_DEFAULT;

  /* Configuration 0: AVDD reference, single-ended, 12-bit */
  IADC_AllConfigs_t allConfigs = IADC_ALLCONFIGS_DEFAULT;
  allConfigs.configs[0].reference = iadcCfgReferenceVddx;
  allConfigs.configs[0].vRef      = IADC_VREF_MV;
  allConfigs.configs[0].osrHighSpeed = iadcCfgOsrHighSpeed2x;

  IADC_init(IADC0, &initIADC, &allConfigs);

  /* Single-queue init: immediate trigger, convert once */
  IADC_InitSingle_t initSingle = IADC_INITSINGLE_DEFAULT;

  /* Input: PD04 positive, GND negative (single-ended) */
  IADC_SingleInput_t singleInput = IADC_SINGLEINPUT_DEFAULT;
  singleInput.posInput = iadcPosInputPortDPin4;
  singleInput.negInput = iadcNegInputGnd;

  IADC_initSingle(IADC0, &initSingle, &singleInput);

  s_bat_initialized = true;
  sl_zigbee_app_debug_println("Battery ADC: IADC0 ready (PD04, AVDD ref)");
  return SL_STATUS_OK;
}

sl_status_t nowa_bat_measure(nowa_bat_reading_t *reading)
{
  if (!s_bat_initialized || reading == NULL) {
    return SL_STATUS_FAIL;
  }

  /* Start single conversion */
  IADC_command(IADC0, iadcCmdStartSingle);

  /* Poll for FIFO data (< 1 ms at any reasonable clock rate) */
  uint32_t timeout = IADC_TIMEOUT_LOOPS;
  while (IADC_getSingleFifoCnt(IADC0) == 0u) {
    if (--timeout == 0u) {
      sl_zigbee_app_debug_println("Battery ADC: conversion timeout");
      return SL_STATUS_FAIL;
    }
  }

  /* Read result (right-aligned 12-bit) */
  IADC_Result_t result = IADC_pullSingleFifoResult(IADC0);
  uint32_t adc_code = result.data & 0x0FFFu;

  /* Compute V_adc in mV: V_adc = code * VREF / FULL_SCALE */
  uint32_t v_adc_mv = (adc_code * IADC_VREF_MV) / IADC_FULL_SCALE;

  /* Recover battery voltage via divider: V_bat = V_adc * DIVIDER_RATIO */
  uint32_t v_bat_mv = v_adc_mv * BAT_DIVIDER_RATIO;

  /* Clamp to sensible range */
  if (v_bat_mv > 5000u) v_bat_mv = 5000u;

  /* ZCL battery_voltage: units of 100 mV */
  uint8_t zcl_v = (uint8_t)(v_bat_mv / 100u);

  /* ZCL battery_percentage_remaining: units of 0.5 %, 200 = 100 % */
  uint8_t zcl_pct;
  if (v_bat_mv <= NOWA_BAT_MV_EMPTY) {
    zcl_pct = 0u;
  } else if (v_bat_mv >= NOWA_BAT_MV_FULL) {
    zcl_pct = 200u;
  } else {
    zcl_pct = (uint8_t)(
      (v_bat_mv - NOWA_BAT_MV_EMPTY) * 200u
      / (NOWA_BAT_MV_FULL - NOWA_BAT_MV_EMPTY));
  }

  reading->voltage_mv    = (uint16_t)v_bat_mv;
  reading->zcl_voltage   = zcl_v;
  reading->zcl_percentage = zcl_pct;

  return SL_STATUS_OK;
}
