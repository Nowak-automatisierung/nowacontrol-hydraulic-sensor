# Integration Test Suite Baseline

Baseline fuer die Integration-Test-Struktur des nowaControl Hydraulic Sensor Projekts.

## Zweck

Dieses Verzeichnis enthaelt spaeter Integrationstests fuer das Zusammenspiel mehrerer Firmware-, Protokoll- und Plattform-Komponenten.

## Geplanter Fokus

- Sensor-HAL und gemeinsame Firmware-Bausteine
- Zigbee-bezogene Integrationspfade
- Konfigurations- und Initialisierungsablaeufe
- Update- und Bootloader-nahe Integrationspfade, soweit ohne echte Zielhardware testbar
- Hostseitige Testfaelle mit mehreren beteiligten Modulen

## Aktueller Status

Aktuell ist nur die strukturelle Baseline vorhanden. Konkrete Integrationstests werden in spaeteren Arbeitspaketen ergaenzt, sobald die beteiligten Komponenten im Repository vorliegen.

## Hinweise

Integrationstests koennen Mocking, Test-Doubles und kontrollierte Host-Umgebungen verwenden, sollen aber klar von Unit-Tests und HIL-Tests getrennt bleiben.