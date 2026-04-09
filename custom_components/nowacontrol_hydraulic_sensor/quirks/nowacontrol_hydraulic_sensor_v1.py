"""ZHA quirk for nowaControl Hydraulic Sensor V1."""

from __future__ import annotations

import zigpy.types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder
from zigpy.quirks.v2.homeassistant.sensor import SensorStateClass
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class NowaControlConfigCluster(CustomCluster):
    """Manufacturer cluster for nowaControl hydraulic sensor configuration."""

    cluster_id = 0xFC10
    ep_attribute = "nowacontrol_config"

    class AttributeDefs(BaseAttributeDefs):
        measurement_interval_ms = ZCLAttributeDef(id=0x0000, type=t.uint32_t, access="rwp")
        vorlauf_offset_cc = ZCLAttributeDef(id=0x0001, type=t.int16s, access="rwp")
        ruecklauf_offset_cc = ZCLAttributeDef(id=0x0002, type=t.int16s, access="rwp")
        sensor_count = ZCLAttributeDef(id=0x0003, type=t.uint8_t, access="rp")
        error_count = ZCLAttributeDef(id=0x0004, type=t.uint16_t, access="rp")
        last_status = ZCLAttributeDef(id=0x0005, type=t.uint8_t, access="rp")
        last_update_age_s = ZCLAttributeDef(id=0x0006, type=t.uint32_t, access="rp")
        antenna_mode = ZCLAttributeDef(id=0x0007, type=t.enum8, access="rp")
        rescan_request = ZCLAttributeDef(id=0x0008, type=t.uint32_t, access="rwp")
        factory_reset_request = ZCLAttributeDef(id=0x0009, type=t.uint32_t, access="rwp")


(
    QuirkBuilder("nowaControl", "Hydraulic Sensor V1")
    .replaces(NowaControlConfigCluster)
    .number(
        attribute_name=NowaControlConfigCluster.AttributeDefs.measurement_interval_ms.name,
        cluster_id=NowaControlConfigCluster.cluster_id,
        endpoint_id=1,
        translation_key="measurement_interval",
        min_value=5000,
        max_value=3600000,
        step=5000,
        unit="ms",
        entity_type=EntityType.CONFIG,
        fallback_name="Measurement interval",
    )
    .number(
        attribute_name=NowaControlConfigCluster.AttributeDefs.vorlauf_offset_cc.name,
        cluster_id=NowaControlConfigCluster.cluster_id,
        endpoint_id=1,
        translation_key="vorlauf_offset",
        min_value=-2000,
        max_value=2000,
        step=5,
        unit="0.01 degC",
        entity_type=EntityType.CONFIG,
        fallback_name="Vorlauf offset",
    )
    .number(
        attribute_name=NowaControlConfigCluster.AttributeDefs.ruecklauf_offset_cc.name,
        cluster_id=NowaControlConfigCluster.cluster_id,
        endpoint_id=1,
        translation_key="ruecklauf_offset",
        min_value=-2000,
        max_value=2000,
        step=5,
        unit="0.01 degC",
        entity_type=EntityType.CONFIG,
        fallback_name="Ruecklauf offset",
    )
    .sensor(
        attribute_name=NowaControlConfigCluster.AttributeDefs.sensor_count.name,
        cluster_id=NowaControlConfigCluster.cluster_id,
        endpoint_id=1,
        translation_key="sensor_count",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="1-Wire sensor count",
    )
    .sensor(
        attribute_name=NowaControlConfigCluster.AttributeDefs.error_count.name,
        cluster_id=NowaControlConfigCluster.cluster_id,
        endpoint_id=1,
        translation_key="error_count",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="1-Wire error count",
    )
    .sensor(
        attribute_name=NowaControlConfigCluster.AttributeDefs.last_status.name,
        cluster_id=NowaControlConfigCluster.cluster_id,
        endpoint_id=1,
        translation_key="last_status",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Last sensor status",
    )
    .sensor(
        attribute_name=NowaControlConfigCluster.AttributeDefs.last_update_age_s.name,
        cluster_id=NowaControlConfigCluster.cluster_id,
        endpoint_id=1,
        translation_key="last_update_age",
        unit="s",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Last update age",
    )
    .sensor(
        attribute_name=NowaControlConfigCluster.AttributeDefs.antenna_mode.name,
        cluster_id=NowaControlConfigCluster.cluster_id,
        endpoint_id=1,
        translation_key="antenna_mode",
        entity_type=EntityType.DIAGNOSTIC,
        fallback_name="Antenna mode",
    )
    .write_attr_button(
        attribute_name=NowaControlConfigCluster.AttributeDefs.rescan_request.name,
        attribute_value=1,
        cluster_id=NowaControlConfigCluster.cluster_id,
        endpoint_id=1,
        translation_key="rescan_sensors",
        entity_type=EntityType.CONFIG,
        fallback_name="Rescan sensors",
    )
    .write_attr_button(
        attribute_name=NowaControlConfigCluster.AttributeDefs.factory_reset_request.name,
        attribute_value=1,
        cluster_id=NowaControlConfigCluster.cluster_id,
        endpoint_id=1,
        translation_key="factory_reset",
        entity_type=EntityType.CONFIG,
        fallback_name="Factory reset",
    )
    .add_to_registry()
)
