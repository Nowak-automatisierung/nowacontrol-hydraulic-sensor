# __WORKSPACE_NAME__

## Mission
Dieses Repository ist ein produktionsorientierter Workspace für Software, Dokumentation, Web, Cloud und optional Geräte/Firmware.

## Operating rules
- Arbeite inkrementell und nachvollziehbar.
- Bevor du größere Änderungen machst, skizziere kurz den Plan.
- Bevorzuge kleine, reviewbare Änderungen statt großer unstrukturierter Umbauten.
- Halte Architekturentscheidungen in `docs/adr/` fest.
- Aktualisiere betroffene Dokumentation, wenn Verhalten oder Schnittstellen geändert werden.
- Halte Secrets aus Git heraus.
- Nutze projektweite MCP-Server nur über `.mcp.json`.
- Nutze agent-spezifische MCP-Server bevorzugt inline in Subagents, wenn sie nur für Spezialaufgaben nötig sind.

## Repository map
- `docs/` Architektur, ADRs, Produktdokumente, Runbooks, Release-Doku
- `apps/` Web, API, Admin
- `firmware/` Bootloader, Devices, Shared Firmware, Public Signing Material
- `hardware/` Elektronik, Mechanik, Fertigung
- `cloud/` Provisioning, Telemetry, Device API, Update Service
- `infra/` dev/stage/prod Infrastruktur
- `tests/` unit, integration, e2e, hil
- `tools/` lokales Setup, Release, Provisioning, Hooks
- `.claude/` projektweite Claude-Operations-Struktur

## Definition of done
- Relevante Tests sind grün oder bewusst dokumentiert
- Dokumentation ist aktualisiert
- Sicherheitsrelevante Änderungen sind markiert
- Release-Auswirkungen sind benannt
