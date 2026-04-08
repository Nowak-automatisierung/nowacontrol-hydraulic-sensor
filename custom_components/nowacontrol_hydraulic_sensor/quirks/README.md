Copy [nowacontrol_hydraulic_sensor_v1.py](/C:/Users/mnowak/Work/10-products/nowacontrol-hydraulic-sensor/custom_components/nowacontrol_hydraulic_sensor/quirks/nowacontrol_hydraulic_sensor_v1.py) to Home Assistant's custom quirks path, for example `/config/custom_zha_quirks/`.

Enable it in `configuration.yaml`:

```yaml
zha:
  custom_quirks_path: /config/custom_zha_quirks
```

Then remove and re-pair the sensor so ZHA re-interviews the device and creates the configuration and diagnostic entities from the manufacturer cluster `0xFC10`.
