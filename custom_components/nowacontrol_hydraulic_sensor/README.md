# nowaControl Hydraulic Sensor - Home Assistant Package

Dieses Paket ist die Home-Assistant-/HACS-Schicht fuer den nowaControl Hydraulic Sensor.

## Rolle
- stellt die HACS-/Home-Assistant-Metadaten bereit
- liefert den nowaControl-ZHA-Quirk als mitgeliefertes Paketartefakt aus
- bietet einen echten Home-Assistant-Setupdialog ueber `Geraet hinzufuegen`
- stellt Optionen, Reparaturhinweise und Services fuer Quirk-Installation und Statuspruefung bereit
- dokumentiert die Trennung zwischen HACS-Integration und Zigbee-Firmware

## Wichtige Architekturregel
ZHA-Quirks leben in Home Assistant nicht innerhalb von `custom_components`, sondern im durch ZHA konfigurierten Quirk-Pfad, typischerweise `/config/custom_zha_quirks/`.

Dieses Paket loest das sauber, indem es:
- den Quirk mit ausliefert
- einen Installationsservice bereitstellt
- die notwendigen naechsten Schritte per Home-Assistant-Benachrichtigung anzeigt

## Aktivierung in Home Assistant
1. Paket ueber HACS installieren.
2. Die Integration anschliessend ueber `Einstellungen -> Geraete & Dienste -> Integration hinzufuegen -> nowaControl Hydraulic Sensor` einrichten.
3. In `configuration.yaml` bleibt weiterhin der ZHA-Basiseintrag noetig:

```yaml
zha:
  custom_quirks_path: /config/custom_zha_quirks
```

4. Home Assistant neu starten.
5. Im UI pruefen, ob die Integration den Quirk automatisch installiert hat.
6. Falls ein Repair-Hinweis erscheint, diesen im UI bestaetigen.
7. Sensor in ZHA neu anlernen.

## UI-first Verhalten
- Config Flow fuer den ersten Setupdialog
- Options Flow fuer Pfad, Auto-Install und Benachrichtigungen
- Repairs fuer fehlenden Quirk oder falschen ZHA-Quirk-Pfad
- Services bleiben als Fallback fuer Wartung und Support erhalten

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
