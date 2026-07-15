# nowaControl Hydraulic Sensor - Home Assistant Package

Dieses Paket ist die Home-Assistant-/HACS-Schicht fuer den nowaControl Hydraulic Sensor.

## Rolle
- stellt die HACS-/Home-Assistant-Metadaten bereit
- liefert den nowaControl-ZHA-Quirk als mitgeliefertes Paketartefakt aus
- bietet einen echten Home-Assistant-Setupdialog ueber `Geraet hinzufuegen`
- stellt Optionen, Hinweise und einen rein diagnostischen Statusservice bereit
- dokumentiert die Trennung zwischen HACS-Integration und Zigbee-Firmware

## Wichtige Architekturregel
ZHA-Quirks leben in Home Assistant nicht innerhalb von `custom_components`, sondern im durch ZHA konfigurierten Quirk-Pfad, typischerweise `/config/custom_zha_quirks/`.

Der Quirk wird weiterhin als Paketartefakt ausgeliefert. Direkte Dateischreibzugriffe
der Integration sind als P0-Containment standardmaessig und unabhaengig von alten
Konfigurationswerten deaktiviert. Installieren, Ueberschreiben und Entfernen werden
deterministisch verweigert; eine spaetere Reaktivierung erfordert einen separaten
Security- und Commissioning-Vertrag.

## Aktivierung in Home Assistant
1. Paket ueber HACS installieren.
2. Die Integration anschliessend ueber `Einstellungen -> Geraete & Dienste -> Integration hinzufuegen -> nowaControl Hydraulic Sensor` einrichten.
3. In `configuration.yaml` bleibt weiterhin der ZHA-Basiseintrag noetig:

```yaml
zha:
  custom_quirks_path: /config/custom_zha_quirks
```

4. Home Assistant neu starten.
5. Den Quirk ausserhalb dieser Integration nach einem separat freigegebenen Verfahren bereitstellen.
6. Sensor in ZHA neu anlernen.

## UI-first Verhalten
- Config Flow fuer den ersten Setupdialog
- Options Flow fuer Pfad und Benachrichtigungen; Auto-Install bleibt effektiv deaktiviert
- nicht schreibender Hinweis fuer fehlenden Quirk oder falschen ZHA-Quirk-Pfad
- nur ein read-only Statusservice; keine Install-, Overwrite- oder Remove-Services

## Verfuegbarer Service

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
