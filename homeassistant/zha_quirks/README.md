Copy [nowacontrol_hydraulic_sensor_v1.py](/C:/Users/mnowak/Work/10-products/nowacontrol-hydraulic-sensor/homeassistant/zha_quirks/nowacontrol_hydraulic_sensor_v1.py) to Home Assistant's custom quirks path, for example `/config/custom_zha_quirks/`.

Enable it in `configuration.yaml`:

```yaml
zha:
  custom_quirks_path: /config/custom_zha_quirks
```

Then remove and re-pair the sensor so ZHA re-interviews the new endpoint/cluster layout and the quirk can create HA entities for:

- measurement interval
- Vorlauf offset
- Ruecklauf offset
- 1-Wire sensor count
- 1-Wire error count
- last sensor status
- last update age
- antenna mode
- rescan button
- factory reset button
