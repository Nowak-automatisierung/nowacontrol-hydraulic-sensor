# GitHub Release Pipeline

## Ziel
Dieses Runbook beschreibt den professionellen Release-Pfad fuer:
- Home-Assistant-/HACS-Paket
- Firmware-Artefakte
- OTA-Metadaten

## Workflow-Uebersicht

### 1. Validate Home Assistant Package
- Datei: `.github/workflows/validate-homeassistant.yml`
- Zweck:
  - prueft `hacs.json`
  - prueft `custom_components/nowacontrol_hydraulic_sensor/manifest.json`
  - kompiliert Python-Dateien in `custom_components/` und `homeassistant/zha_quirks/`

### 2. Release Home Assistant Package
- Datei: `.github/workflows/release-homeassistant.yml`
- Trigger:
  - Tag `ha-v*`
  - `workflow_dispatch`
- Ergebnis:
  - ZIP mit `custom_components`, `hacs.json` und ZHA-Quirk-Hilfsdateien
  - GitHub Release fuer den Home-Assistant-Auslieferungspfad

### 3. Release Firmware and OTA Assets
- Datei: `.github/workflows/release-firmware-ota.yml`
- Trigger:
  - Tag `fw-v*`
  - `workflow_dispatch`
- Runner:
  - `self-hosted`, `windows`, `silabs`
- Ergebnis:
  - Bootloader- und Firmware-Artefakte
  - OTA-Manifest mit SHA-256 und Dateigroessen
  - GitHub Release fuer Firmware/OTA

## Wichtige Trennung
- HACS-/Home-Assistant-Release und Firmware-Release sind absichtlich getrennt.
- Home Assistant installiert keine Firmware.
- OTA-Metadaten sind kein Ersatz fuer HACS und HACS ist kein Ersatz fuer OTA.

## Offene Produktionspunkte
- Brand-Assets fuer HACS (`brand/icon.png`)
- Signierter Firmware-Build auf dem Self-hosted-Silabs-Runner
- GitHub Release Notes aus `sensor-platform/ota/release-notes/`
- Kopplung an `device-cloud/services/update-service/`
- Channel-spezifische OTA-Distribution (`stable`, `beta`, `rollback`)
