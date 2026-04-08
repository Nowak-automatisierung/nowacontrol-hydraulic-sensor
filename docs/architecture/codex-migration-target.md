# Codex Migration Target

## Ziel
Dieses Dokument definiert die migrationssichere Zielarchitektur fuer das nowaControl Hydraulic Sensor Monorepo.

## Leitprinzipien
- Der funktionierende Zigbee-/DS18B20-Pfad unter `sensor-platform/firmware/applications/zigbee-ha` bleibt der technische Referenzpfad.
- Neue Home-Assistant-/HACS-Strukturen werden additiv aufgebaut und erst spaeter zur produktiven Distribution erklaert.
- Claude-spezifische Artefakte werden nicht weitergefuehrt; das Repository wird konsequent auf Codex ausgerichtet.
- Firmware, Quirks, HACS-Integration und OTA-Assets bekommen klar getrennte Verantwortlichkeiten.

## Aktueller stabiler Produktpfad
- Firmware-App: `sensor-platform/firmware/applications/zigbee-ha`
- Flash-Pfad: `scripts/flash-sensor.ps1`
- Bootloader-Artefakt: `sensor-platform/firmware/bootloader/nowacontrol_bootloader_nwc_hyd_001.hex`
- App-Artefakt: `sensor-platform/firmware/applications/zigbee-ha/cmake_gcc/build/base/nowacontrol-zigbee-ha.hex`
- ZHA-Quirk-Quellen: `homeassistant/zha_quirks/`

## Ehemalige Problemzonen / Altlasten
- Claude-spezifische Workspace-Dateien und Scaffold-Skripte wurden aus dem produktiven Git-Pfad entfernt.
- Lokal erzeugte Claude-Worktrees bleiben ignoriert und sind keine Source of Truth.
- Die HACS-faehige `custom_components/<domain>`-Struktur ist jetzt vorhanden.
- Release-, OTA- und Paket-Workflows sind angelegt und muessen nur noch produktiv genutzt werden.

## Zielarchitektur
```text
sensor-platform/                    Produktquelle fuer Firmware, Hardware, Tests, OTA-Assets
homeassistant/
  zha_quirks/                       Quirk-Quellen fuer lokale/dev Installation
custom_components/
  nowacontrol_hydraulic_sensor/     HACS-/Home-Assistant-Zielpaket am Repo-Root
hacs.json                           HACS-Metadaten am Repo-Root
scripts/                            Flash-, Build- und Service-Skripte
.github/workflows/                  Build-, Release-, HACS- und OTA-Pipelines
docs/
  architecture/                     Zielarchitektur und Migrationsentscheidungen
  runbooks/                         Deployment-, Recovery- und HACS-Betriebsanweisungen
```

## HACS- und HA-Zielbild
- HACS erwartet fuer den direkte Repository-Installationspfad `hacs.json` und `custom_components/<domain>` am Repo-Root; `homeassistant/` bleibt fuer Quirks und Hilfsdokumentation bestehen.
- Die ZHA-Quirks werden paketiert dokumentiert und koennen in `/config/custom_zha_quirks/` abgelegt werden.
- Die spaetere Integration soll Bedienung fuer:
  - Messintervall
  - Vorlauf-/Ruecklauf-Offset
  - Delta-T
  - Sensor-Diagnose
  - Rescan
  - Factory Reset
  bereitstellen.

## OTA-/GitHub-Zielbild
- GitHub Releases werden die produktiven OTA-Artefakte publizieren.
- Release-Pipelines muessen mindestens erzeugen:
  - signiertes Firmware-Artefakt
  - OTA-Metadaten/Manifest
  - Release Notes
  - HACS-Paketversion
- `device-cloud/services/update-service/` bleibt der spaetere Cloud-Lieferpfad, darf aber fuer V1 nicht mit HACS verwechselt werden.

## Migrationsstrategie
1. Bestehende Firmware stabil halten.
2. HACS-/HA-Struktur additiv aufbauen.
3. README/Doku auf Codex-Zielbild aktualisieren.
4. Release-/OTA-Workflows ergaenzen.
5. Claude-Artefakte aus dem produktiven Pfad entfernen.
6. GitHub-/HACS-Rollout standardisieren.

## No-Go-Regeln
- Keine Aenderung am funktionierenden Flashpfad ohne Ersatz.
- Keine Vermischung von HACS-Paketdateien mit den Firmware-Buildverzeichnissen.
- Keine Rueckkehr zu gemischten Claude-/Codex-Strukturen.

