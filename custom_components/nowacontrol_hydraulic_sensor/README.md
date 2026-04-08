# nowaControl Hydraulic Sensor - Home Assistant Package

Dieses Paket ist die Home-Assistant-/HACS-Schicht fuer den nowaControl Hydraulic Sensor.

## Rolle
- stellt die HACS-/Home-Assistant-Metadaten bereit
- liefert den nowaControl-ZHA-Quirk als mitgeliefertes Paketartefakt aus
- registriert Home-Assistant-Services fuer Quirk-Installation und Statuspruefung
- dokumentiert die Trennung zwischen HACS-Integration und Zigbee-Firmware

## Wichtige Architekturregel
ZHA-Quirks leben in Home Assistant nicht innerhalb von `custom_components`, sondern im durch ZHA konfigurierten Quirk-Pfad, typischerweise `/config/custom_zha_quirks/`.

Dieses Paket loest das sauber, indem es:
- den Quirk mit ausliefert
- einen Installationsservice bereitstellt
- die notwendigen naechsten Schritte per Home-Assistant-Benachrichtigung anzeigt

## Aktivierung in Home Assistant
Wenn das GitHub-Repository privat ist, nutze fuer die aktuelle Installation den lokalen Pfad ueber `/config/custom_components/`. HACS kann private GitHub-Repositories laut offizieller HACS-Dokumentation nicht als Custom Repository verwenden.

1. Paket ueber HACS installieren.
2. In `configuration.yaml` hinzufuegen:

```yaml
nowacontrol_hydraulic_sensor:

zha:
  custom_quirks_path: /config/custom_zha_quirks
```

3. Home Assistant neu starten.
4. Service `nowacontrol_hydraulic_sensor.install_zha_quirk` ausfuehren.
5. Home Assistant erneut neu starten.
6. Sensor in ZHA neu anlernen.

## Verfuegbare Services
- `nowacontrol_hydraulic_sensor.install_zha_quirk`
- `nowacontrol_hydraulic_sensor.remove_zha_quirk`
- `nowacontrol_hydraulic_sensor.show_quirk_status`

## Erwartete ZHA-Entitaeten nach erfolgreichem Neu-Anlernen
- Vorlauf Temperatur
- Ruecklauf Temperatur
- Delta-T
- Measurement interval
- Vorlauf offset
- Ruecklauf offset
- 1-Wire sensor count
- 1-Wire error count
- last sensor status
- last update age
- antenna mode
- rescan button
- factory reset button
