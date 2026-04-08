# Home Assistant und HACS Rollout Runbook

## Ziel
Saubere Installation der nowaControl Home-Assistant-Seite als HACS Custom Repository, ohne den Firmware-Quellpfad zu vermischen.

## Wichtige Vorbedingung
HACS Custom Repositories erwarten ein oeffentliches GitHub-Repository mit passender Paketstruktur. Dieses Repository erfuellt diesen Pfad jetzt ueber `hacs.json` am Root und das Paket unter `custom_components/`.

## Empfohlene Betriebsform
- Monorepo bleibt Source of Truth.
- Das HACS-Zielpaket liegt am Repo-Root unter `custom_components/nowacontrol_hydraulic_sensor/` plus `hacs.json`.
- GitHub Release/Package-Workflow exportiert die fuer HA relevanten Dateien.
- Firmware-OTA bleibt ein separater Release-Kanal.

## Installationspfad in Home Assistant
1. HACS Custom Repository eintragen.
2. Integration aus HACS installieren.
3. Integration ueber `Einstellungen -> Geraete & Dienste -> Integration hinzufuegen -> nowaControl Hydraulic Sensor` einrichten.
4. `configuration.yaml` fuer ZHA-Quirks ergaenzen:

```yaml
zha:
  custom_quirks_path: /config/custom_zha_quirks
```

5. Home Assistant neu starten.
6. Die Integration installiert den Quirk automatisch oder zeigt einen Repair-Hinweis zum Installieren an.
7. Home Assistant erneut neu starten.
8. Sensor neu anlernen.

## Sichtbare Ziel-Entitaeten
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

## Rollout fuer mehrere Liegenschaften
- Jeder Standort bekommt identische Paketversionen.
- Standortspezifische Offsets und Intervalle werden in HA gesetzt, nicht in forks.
- Releases werden versioniert, getestet und ueber GitHub dokumentiert.
