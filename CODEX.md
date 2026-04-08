# nowaControl Hydraulic Sensor - Codex Workspace Guide

## Mission
Dieses Repository ist die produktive Source of Truth fuer den nowaControl Hydraulic Sensor inklusive Firmware, Home-Assistant-Integration, OTA-Vorbereitung und Betriebsdokumentation.

## Codex-Leitregeln
- Bestehende, funktionierende Sensorpfade nicht unbeabsichtigt brechen.
- Firmware-Aenderungen immer gegen den funktionierenden Pfad `sensor-platform/firmware/applications/zigbee-ha` beurteilen.
- Home-Assistant-/HACS-Strukturen additiv und versionierbar entwickeln.
- Keine neuen Claude-spezifischen Strukturen mehr einführen.
- Release-, OTA- und HACS-Artefakte als getrennte Lieferpfade behandeln.

## Produktrelevante Bereiche
- `sensor-platform/` Firmware, Hardware, OTA, Tests
- `custom_components/nowacontrol_hydraulic_sensor/` HACS-/Home-Assistant-Zielpaket
- `homeassistant/zha_quirks/` Quirk-Quellen und lokale Installationshilfe
- `docs/` Architektur, Runbooks, Release- und Integrationsdokumente
- `scripts/` Flash- und Service-Skripte

## Bereinigte Altlasten
- Die früheren Claude-Workspace-Dateien und Claude-Scaffold-Skripte wurden aus dem produktiven Repository entfernt.
- Lokal ignorierte Restverzeichnisse wie `.claude/worktrees/` bleiben außerhalb des produktiven Git-Pfads.

## Definition of done
- Funktionierende Sensorpfade bleiben intakt.
- Betroffene Doku ist aktualisiert.
- HACS-/HA-/OTA-Auswirkungen sind benannt.
- Neue Struktur fuehrt nicht zu parallelen, widerspruechlichen Pfaden.
