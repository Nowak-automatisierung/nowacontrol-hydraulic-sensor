# Unit Test Suite Baseline

Baseline fuer die Unit-Test-Struktur des nowaControl Hydraulic Sensor Projekts.

## Zweck

Dieses Verzeichnis enthaelt spaeter Unit-Tests fuer klar abgegrenzte Firmware- und Plattform-Komponenten.

## Geplanter Fokus

- Sensor-HAL Hilfsfunktionen
- Konfigurationslogik
- Parser und Transformationslogik
- Bootloader-nahe Hilfslogik, soweit hostseitig testbar
- Gemeinsame Utility-Funktionen

## Aktueller Status

Aktuell ist nur die strukturelle Baseline vorhanden. Konkrete Unit-Tests werden in spaeteren Arbeitspaketen ergaenzt, sobald die zu testenden Komponenten im Repository vorliegen.

## Hinweise

Unit-Tests sollen hostseitig ausfuehrbar sein und keine echte MG24-Hardware voraussetzen.