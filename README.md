# nowaControl Hydraulic Sensor

Monorepo fuer die Entwicklung des nowaControl Hydraulic Sensor Produkts auf Basis des Seeed Studio XIAO MG24 (EFR32MG24).

## Zweck

Dieses Repository buendelt Produktdokumentation, Firmware-Vorbereitung, Cloud-/OTA-Vorbereitung, Infrastruktur und begleitende Projektartefakte fuer die V1-Entwicklung.

Der aktuelle Fokus liegt auf:

- Hardware- und Firmware-Baseline fuer XIAO MG24
- Zigbee / Home Assistant ZHA als V1-Protokollpfad
- OTA-Vorbereitung mit signierten Images und Rollback-Pfad
- Validierungs-, Compliance- und Release-Vorbereitung

## Aktueller Status

Der Repository-Grundaufbau und die erste Dokumentationsbasis sind vorhanden.

Bereits angelegt bzw. dokumentiert:

- Architektur-, Hardware-, Protokoll-, Compliance- und Validation-Dokumente
- Milestones M0 bis M4 in GitHub
- Erste Engineering-Issues fuer Firmware, Tests, OTA und Compliance
- GitHub-Repository als zentrale Source of Truth

Noch offen:

- Firmware-Basis unter `sensor-platform/firmware/devices`
- Bootloader-Konfiguration und OTA-Slot-Fallback
- Unit-, Integration- und HIL-Teststruktur
- Update-Service-Lieferpfad
- Signing-Workflow und erstes signiertes OTA-Image
- Messdaten fuer Power, RF und Compliance-relevante Grenzwerte

## V1-Fokus

V1 ist auf folgende Kernlinie ausgerichtet:

- Hardware: Seeed Studio XIAO MG24
- Funkpfad: Zigbee
- Integration: Home Assistant ueber ZHA
- OTA: vorbereitet, aber noch nicht release-ready
- BLE / Thread / Matter: Zukunftspfad, nicht Bestandteil von V1 ohne neue Bewertung

## Codex-Migration

Die bevorzugte Projekt-Einstiegsdatei fuer die laufende Migration ist `CODEX.md`.

Neu angelegt fuer den professionellen Finalpfad:
- `custom_components/nowacontrol_hydraulic_sensor/` als HACS-/Home-Assistant-Zielpaket
- `hacs.json` am Repo-Root fuer HACS-Kompatibilitaet
- `docs/architecture/codex-migration-target.md` als Migrations-Source-of-Truth
- `docs/runbooks/github-public-hacs-cutover.md` als Schritt-fuer-Schritt-Pfad fuer GitHub/HACS-Rollout

`CLAUDE.md` und `.claude/` gelten als Legacy-Bestand und werden erst nach dokumentierter Uebernahme bereinigt.

## Repository-Struktur

```text
CODEX.md               Codex-Einstieg und Arbeitsregeln
custom_components/      HACS-/Home-Assistant-Zielpaket
.claude/               Legacy Claude-Projektkontext, Agenten, Skills
.github/workflows/     GitHub-Automatisierung
admin-portal/          Verwaltungs- und Produktoberflaechen
device-cloud/          Cloud-Services, u. a. Update-Service
docs/                  Architektur, Hardware, Protokolle, Release-Dokumente
infra/                 Infrastruktur und Betriebsartefakte
marketing-site/        Marketing-/Web-Praesenz
sensor-platform/       Geraete-, Firmware-, Hardware- und Testbasis
tools/scaffold/        Projekt- und Worktree-Scaffolding

